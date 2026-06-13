"""SAML SSO endpoints: SP metadata, login redirect, ACS, and admin configuration."""

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models import SsoConfig, User
from app.schemas.sso import SsoConfigIn, SsoConfigOut, SsoStatusOut
from app.services import audit, events, sso

router = APIRouter(tags=["sso"])

# Fields that are write-only / never echoed back verbatim.
_SECRET_FIELDS = {"sp_private_key"}


def _to_out(cfg: SsoConfig) -> SsoConfigOut:
    out = SsoConfigOut.model_validate(cfg, from_attributes=True)
    out.sp_metadata_url = f"{cfg.base_url.rstrip('/')}/api/v1/sso/metadata" if cfg.base_url else ""
    out.acs_url = sso.acs_url(cfg) if cfg.base_url else ""
    out.sp_entity_id_effective = sso.sp_entity_id(cfg) if cfg.base_url or cfg.sp_entity_id else ""
    out.sp_signing_configured = bool(cfg.sp_private_key.strip() and cfg.sp_x509_cert.strip())
    return out


# --------------------------------------------------------------------------- #
# Public: login-page status, redirect to IdP, metadata, ACS
# --------------------------------------------------------------------------- #
@router.get("/sso/status", response_model=SsoStatusOut)
def status(db: Session = Depends(get_db)):
    cfg = sso.get_config(db)
    return SsoStatusOut(
        enabled=cfg.enabled and bool(cfg.idp_sso_url),
        button_label=cfg.button_label,
        login_url="/api/v1/auth/sso/login",
    )


@router.get("/auth/sso/login")
def login_redirect(db: Session = Depends(get_db)):
    cfg = sso.get_config(db)
    if not cfg.enabled:
        raise HTTPException(status_code=404, detail="SAML SSO is not enabled")
    try:
        url = sso.build_authn_request_redirect(cfg)
    except sso.SamlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url, status_code=302)


@router.get("/sso/metadata")
def metadata(db: Session = Depends(get_db)):
    cfg = sso.get_config(db)
    try:
        xml = sso.sp_metadata_xml(cfg)
    except sso.SamlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=xml, media_type="application/samlmetadata+xml")


@router.post("/auth/sso/acs")
def assertion_consumer(
    db: Session = Depends(get_db),
    SAMLResponse: str = Form(...),  # noqa: N803 - SAML binding field name
    RelayState: str | None = Form(default=None),  # noqa: N803
):
    cfg = sso.get_config(db)
    try:
        user = sso.process_response(db, cfg, SAMLResponse)
    except sso.SamlError as exc:
        events.emit(db, "warning", "auth", f"SAML SSO login rejected: {exc}")
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = sso.issue_token(user)
    db.commit()
    base = cfg.base_url.rstrip("/")
    target = RelayState if (RelayState and RelayState.startswith("/")) else "/sso/callback"
    return RedirectResponse(f"{base}{target}?token={token}", status_code=302)


# --------------------------------------------------------------------------- #
# Admin: configuration
# --------------------------------------------------------------------------- #
@router.get("/sso/config", response_model=SsoConfigOut)
def get_config(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    return _to_out(sso.get_config(db))


@router.put("/sso/config", response_model=SsoConfigOut)
def update_config(
    payload: SsoConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    cfg = sso.get_config(db)
    before = audit.snapshot(cfg)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field in _SECRET_FIELDS and not value:
            continue  # blank => keep existing secret
        setattr(cfg, field, value)
    db.flush()
    after = {k: v for k, v in audit.snapshot(cfg).items() if k not in _SECRET_FIELDS}
    audit.record(db, user.username, "update", "sso_config", cfg.id,
                 {k: v for k, v in before.items() if k not in _SECRET_FIELDS}, after,
                 summary="Updated SAML SSO configuration")
    events.emit(db, "info", "auth", f"SAML SSO configuration updated by {user.username}")
    db.commit()
    return _to_out(cfg)

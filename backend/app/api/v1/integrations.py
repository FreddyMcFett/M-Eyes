from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models import Integration, User
from app.schemas.integration import (
    IntegrationIn,
    IntegrationOut,
    IntegrationSyncResult,
    IntegrationTestResult,
    IntegrationUpdate,
)
from app.services import integration_admin
from app.services.integrations import connector_catalog
from app.services.integrations.base import ConnectorError

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _to_out(integration: Integration) -> IntegrationOut:
    out = IntegrationOut.model_validate(integration, from_attributes=True)
    out.secret_set = bool(integration.secret)
    return out


@router.get("/catalog")
def catalog(user: User = Depends(get_current_user)):
    """Connector descriptors for the UI to render add/edit forms."""
    return connector_catalog()


@router.get("", response_model=list[IntegrationOut])
def list_integrations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_to_out(i) for i in integration_admin.list_integrations(db)]


@router.get("/{integration_id}", response_model=IntegrationOut)
def get_integration(integration_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    integration = integration_admin.get(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return _to_out(integration)


@router.post("", response_model=IntegrationOut, status_code=201)
def create_integration(payload: IntegrationIn, db: Session = Depends(get_db),
                       user: User = Depends(require_role("admin"))):
    if db.scalar(select(Integration).where(Integration.name == payload.name)):
        raise HTTPException(status_code=409, detail=f"An integration named {payload.name!r} exists")
    try:
        integration = integration_admin.create(db, user.username, payload.model_dump())
    except ConnectorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return _to_out(integration)


@router.patch("/{integration_id}", response_model=IntegrationOut)
def update_integration(integration_id: int, payload: IntegrationUpdate, db: Session = Depends(get_db),
                       user: User = Depends(require_role("admin"))):
    integration = integration_admin.get(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration_admin.update(db, user.username, integration, payload.model_dump(exclude_unset=True))
    db.commit()
    return _to_out(integration)


@router.delete("/{integration_id}", status_code=204)
def delete_integration(integration_id: int, db: Session = Depends(get_db),
                       user: User = Depends(require_role("admin"))):
    integration = integration_admin.get(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration_admin.delete(db, user.username, integration)
    db.commit()


@router.post("/{integration_id}/test", response_model=IntegrationTestResult)
def test_integration(integration_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_role("operator"))):
    integration = integration_admin.get(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    result = integration_admin.test(db, integration)
    db.commit()
    return IntegrationTestResult(**result)


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResult)
def sync_integration(integration_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_role("operator"))):
    integration = integration_admin.get(db, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    result = integration_admin.run_sync(db, integration)
    db.commit()
    return IntegrationSyncResult(ok=result.get("ok", False),
                                 detail=result.get("detail", ""),
                                 message=result.get("message", ""))

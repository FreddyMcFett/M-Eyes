from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Deployment, User
from app.schemas.system import DeploymentOut
from app.services import app_settings
from app.services.deploy import bind as bind_deploy
from app.services.deploy import kea as kea_deploy

router = APIRouter(prefix="/deploy", tags=["deploy"])


def _debug_enabled(db: Session) -> bool:
    return app_settings.get_bool(db, "debug_mode")


@router.post("/bind")
def deploy_bind(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = bind_deploy.deploy(db, user.username, debug=_debug_enabled(db))
    db.commit()
    return result


@router.get("/bind/preview")
def preview_bind(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return bind_deploy.preview(db)


@router.post("/kea")
def deploy_kea(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = kea_deploy.deploy(db, user.username, debug=_debug_enabled(db))
    db.commit()
    return result


@router.get("/kea/preview")
def preview_kea(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return kea_deploy.preview(db)


@router.get("/status")
def engine_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    def last(target: str) -> Deployment | None:
        return db.scalar(
            select(Deployment).where(Deployment.target == target).order_by(Deployment.id.desc()).limit(1)
        )

    last_bind, last_kea = last("bind"), last("kea")
    return {
        "bind": {
            "last_status": last_bind.status if last_bind else None,
            "last_message": last_bind.message if last_bind else None,
            "deployed_version": last_bind.config_version if last_bind else None,
        },
        "kea": {
            "last_status": last_kea.status if last_kea else None,
            "last_message": last_kea.message if last_kea else None,
            "deployed_version": last_kea.config_version if last_kea else None,
        },
    }


@router.get("/history", response_model=list[DeploymentOut])
def history(limit: int = Query(default=50, le=500), db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    return db.scalars(select(Deployment).order_by(Deployment.id.desc()).limit(limit)).all()


@router.get("/ping/{target}")
def ping(target: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if target == "bind":
        return bind_deploy.ping()
    if target == "kea":
        return kea_deploy.ping()
    return {"reachable": False, "detail": f"Unknown target {target!r}"}

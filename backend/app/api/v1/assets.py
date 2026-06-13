from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models import User
from app.models.asset import ASSET_CRITICALITY, ASSET_STATUSES, ASSET_TYPES
from app.schemas.asset import AssetIn, AssetOut, AssetSyncResult, AssetUpdate
from app.services import assets

router = APIRouter(prefix="/assets", tags=["assets"])


def _validate_enums(asset_type: str | None, status: str | None, criticality: str | None) -> None:
    if asset_type is not None and asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid asset_type; allowed: {list(ASSET_TYPES)}")
    if status is not None and status not in ASSET_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status; allowed: {list(ASSET_STATUSES)}")
    if criticality is not None and criticality not in ASSET_CRITICALITY:
        raise HTTPException(status_code=422,
                            detail=f"Invalid criticality; allowed: {list(ASSET_CRITICALITY)}")


@router.get("", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return assets.list_assets(db)


@router.get("/meta")
def asset_meta(user: User = Depends(get_current_user)):
    return {"types": list(ASSET_TYPES), "statuses": list(ASSET_STATUSES),
            "criticality": list(ASSET_CRITICALITY)}


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = assets.get(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetIn, db: Session = Depends(get_db),
                 user: User = Depends(require_role("operator"))):
    _validate_enums(payload.asset_type, payload.status, payload.criticality)
    data = payload.model_dump(exclude={"tag_ids", "interfaces"})
    interfaces = [i.model_dump() for i in payload.interfaces]
    asset = assets.create(db, user.username, data, interfaces, payload.tag_ids)
    db.commit()
    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db),
                 user: User = Depends(require_role("operator"))):
    asset = assets.get(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    _validate_enums(payload.asset_type, payload.status, payload.criticality)
    changes = payload.model_dump(exclude_unset=True, exclude={"tag_ids", "interfaces"})
    interfaces = [i.model_dump() for i in payload.interfaces] if payload.interfaces is not None else None
    assets.update(db, user.username, asset, changes, interfaces, payload.tag_ids)
    db.commit()
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_role("operator"))):
    asset = assets.get(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    assets.delete(db, user.username, asset)
    db.commit()


@router.post("/sync", response_model=AssetSyncResult)
def sync_assets(db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    result = assets.sync_from_ipam(db, user.username)
    db.commit()
    return AssetSyncResult(**result)

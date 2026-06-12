from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import IPAddress, Network, User
from app.schemas.ipam import IPAddressIn, IPAddressOut, IPAddressUpdate
from app.services import ipam

router = APIRouter(tags=["ipam"])


@router.get("/networks/{network_id}/addresses", response_model=list[IPAddressOut])
def list_addresses(network_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if db.get(Network, network_id) is None:
        raise HTTPException(status_code=404, detail="Network not found")
    return db.scalars(
        select(IPAddress).where(IPAddress.network_id == network_id).order_by(IPAddress.ip)
    ).all()


@router.post("/networks/{network_id}/addresses", response_model=IPAddressOut, status_code=201)
def create_address(network_id: int, payload: IPAddressIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    network = db.get(Network, network_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Network not found")
    record = ipam.create_ip(db, user.username, network, payload.model_dump())
    db.commit()
    return record


@router.patch("/addresses/{address_id}", response_model=IPAddressOut)
def update_address(address_id: int, payload: IPAddressUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    record = db.get(IPAddress, address_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Address not found")
    record = ipam.update_ip(db, user.username, record, payload.model_dump(exclude_unset=True))
    db.commit()
    return record


@router.delete("/addresses/{address_id}", status_code=204)
def delete_address(address_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    record = db.get(IPAddress, address_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Address not found")
    ipam.delete_ip(db, user.username, record)
    db.commit()

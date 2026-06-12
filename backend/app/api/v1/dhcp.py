from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import DhcpOption, DhcpRange, DhcpReservation, DhcpSubnet, User
from app.schemas.dhcp import (
    DhcpOptionIn,
    DhcpOptionOut,
    DhcpRangeIn,
    DhcpRangeOut,
    DhcpReservationIn,
    DhcpReservationOut,
    DhcpSubnetIn,
    DhcpSubnetOut,
    DhcpSubnetUpdate,
)
from app.services import dhcp as dhcp_service
from app.services import leases as lease_service

router = APIRouter(prefix="/dhcp", tags=["dhcp"])


@router.get("/leases")
def list_leases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Live lease table, read from Kea via the Control Agent."""
    return lease_service.list_leases(db)


def _out(subnet: DhcpSubnet) -> DhcpSubnetOut:
    out = DhcpSubnetOut.model_validate(subnet)
    out.cidr = subnet.network.cidr
    return out


def _subnet_or_404(db: Session, subnet_id: int) -> DhcpSubnet:
    subnet = db.get(DhcpSubnet, subnet_id)
    if subnet is None:
        raise HTTPException(status_code=404, detail="DHCP subnet not found")
    return subnet


@router.get("/subnets", response_model=list[DhcpSubnetOut])
def list_subnets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_out(s) for s in db.scalars(select(DhcpSubnet)).all()]


@router.post("/subnets", response_model=DhcpSubnetOut, status_code=201)
def create_subnet(payload: DhcpSubnetIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    subnet = dhcp_service.create_subnet(db, user.username, payload.model_dump())
    db.commit()
    return _out(subnet)


@router.get("/subnets/{subnet_id}", response_model=DhcpSubnetOut)
def get_subnet(subnet_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    return _out(_subnet_or_404(db, subnet_id))


@router.patch("/subnets/{subnet_id}", response_model=DhcpSubnetOut)
def update_subnet(subnet_id: int, payload: DhcpSubnetUpdate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    subnet = _subnet_or_404(db, subnet_id)
    subnet = dhcp_service.update_subnet(db, user.username, subnet,
                                        payload.model_dump(exclude_unset=True))
    db.commit()
    return _out(subnet)


@router.delete("/subnets/{subnet_id}", status_code=204)
def delete_subnet(subnet_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    dhcp_service.delete_subnet(db, user.username, _subnet_or_404(db, subnet_id))
    db.commit()


@router.post("/subnets/{subnet_id}/ranges", response_model=DhcpRangeOut, status_code=201)
def create_range(subnet_id: int, payload: DhcpRangeIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    subnet = _subnet_or_404(db, subnet_id)
    rng = dhcp_service.create_range(db, user.username, subnet, payload.model_dump())
    db.commit()
    return rng


@router.delete("/ranges/{range_id}", status_code=204)
def delete_range(range_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    rng = db.get(DhcpRange, range_id)
    if rng is None:
        raise HTTPException(status_code=404, detail="Range not found")
    dhcp_service.delete_range(db, user.username, rng)
    db.commit()


@router.post("/subnets/{subnet_id}/reservations", response_model=DhcpReservationOut, status_code=201)
def create_reservation(subnet_id: int, payload: DhcpReservationIn, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    subnet = _subnet_or_404(db, subnet_id)
    reservation = dhcp_service.create_reservation(db, user.username, subnet, payload.model_dump())
    db.commit()
    return reservation


@router.delete("/reservations/{reservation_id}", status_code=204)
def delete_reservation(reservation_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    reservation = db.get(DhcpReservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    dhcp_service.delete_reservation(db, user.username, reservation)
    db.commit()


@router.get("/options", response_model=list[DhcpOptionOut])
def list_global_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(DhcpOption).where(DhcpOption.subnet_id.is_(None))).all()


@router.post("/options", response_model=DhcpOptionOut, status_code=201)
def set_global_option(payload: DhcpOptionIn, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    option = dhcp_service.set_option(db, user.username, payload.model_dump())
    db.commit()
    return option


@router.post("/subnets/{subnet_id}/options", response_model=DhcpOptionOut, status_code=201)
def set_subnet_option(subnet_id: int, payload: DhcpOptionIn, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    subnet = _subnet_or_404(db, subnet_id)
    option = dhcp_service.set_option(db, user.username, payload.model_dump(), subnet=subnet)
    db.commit()
    return option


@router.delete("/options/{option_id}", status_code=204)
def delete_option(option_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    option = db.get(DhcpOption, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail="Option not found")
    dhcp_service.delete_option(db, user.username, option)
    db.commit()

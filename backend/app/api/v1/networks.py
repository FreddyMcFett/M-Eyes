from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Network, User
from app.schemas.ipam import NetworkIn, NetworkOut, NetworkUpdate, UtilizationOut
from app.services import discovery, ipam

router = APIRouter(prefix="/networks", tags=["ipam"])


def _with_utilization(db: Session, network: Network) -> NetworkOut:
    out = NetworkOut.model_validate(network)
    out.utilization = UtilizationOut(**ipam.utilization(db, network))
    return out


def _get_or_404(db: Session, network_id: int) -> Network:
    network = db.get(Network, network_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Network not found")
    return network


@router.get("", response_model=list[NetworkOut])
def list_networks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    networks = db.scalars(select(Network).order_by(Network.cidr)).all()
    return [_with_utilization(db, n) for n in networks]


@router.post("", response_model=NetworkOut, status_code=201)
def create_network(payload: NetworkIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    network = ipam.create_network(db, user.username, payload.model_dump())
    db.commit()
    return _with_utilization(db, network)


@router.get("/{network_id}", response_model=NetworkOut)
def get_network(network_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    return _with_utilization(db, _get_or_404(db, network_id))


@router.patch("/{network_id}", response_model=NetworkOut)
def update_network(network_id: int, payload: NetworkUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    network = _get_or_404(db, network_id)
    data = payload.model_dump(exclude_unset=True)
    network = ipam.update_network(db, user.username, network, data)
    db.commit()
    return _with_utilization(db, network)


@router.delete("/{network_id}", status_code=204)
def delete_network(network_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    ipam.delete_network(db, user.username, _get_or_404(db, network_id))
    db.commit()


@router.get("/{network_id}/next-ip")
def next_ip(network_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    network = _get_or_404(db, network_id)
    return {"ip": ipam.next_available_ip(db, network)}


@router.post("/{network_id}/discover")
def discover(network_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    """Ping sweep: record responding addresses as 'discovered', refresh last_seen,
    and flag conflicts."""
    network = _get_or_404(db, network_id)
    result = discovery.discover(db, user.username, network)
    db.commit()
    return result

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import (
    ChangeLog,
    Deployment,
    DhcpSubnet,
    Feed,
    Host,
    IPAddress,
    Network,
    Record,
    User,
    Zone,
)
from app.services import audit, ipam

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    def count(model) -> int:
        return db.scalar(select(func.count(model.id))) or 0

    networks = db.scalars(select(Network).where(Network.is_container.is_(False))).all()
    top_networks = []
    for network in networks:
        util = ipam.utilization(db, network)
        top_networks.append({"id": network.id, "cidr": network.cidr, "name": network.name, **util})
    top_networks.sort(key=lambda n: n["percent"], reverse=True)

    recent_changes = db.scalars(select(ChangeLog).order_by(ChangeLog.id.desc()).limit(8)).all()

    def last_deploy(target: str):
        row = db.scalar(select(Deployment).where(Deployment.target == target)
                        .order_by(Deployment.id.desc()).limit(1))
        return {"status": row.status, "ts": row.ts.isoformat(),
                "config_version": row.config_version} if row else None

    return {
        "config_version": audit.current_version(db),
        "counts": {
            "networks": count(Network),
            "ip_addresses": count(IPAddress),
            "zones": count(Zone),
            "records": count(Record),
            "dhcp_subnets": count(DhcpSubnet),
            "hosts": count(Host),
            "feeds": count(Feed),
        },
        "top_networks": top_networks[:5],
        "recent_changes": [
            {"id": c.id, "ts": c.ts.isoformat(), "actor": c.actor, "action": c.action,
             "object_type": c.object_type, "summary": c.summary}
            for c in recent_changes
        ],
        "engines": {"bind": last_deploy("bind"), "kea": last_deploy("kea")},
    }

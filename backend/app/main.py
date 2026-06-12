import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1 import (
    addresses,
    auth,
    blocklist,
    changelog,
    dashboard,
    deploy,
    dhcp,
    extattrs,
    feeds_admin,
    hosts,
    logs,
    networks,
    records,
    rpz,
    runbook,
    search,
    system,
    tags,
    views,
    zones,
)
from app.database import SessionLocal, engine
from app.feeds.router import router as feeds_router
from app.models import Base, User
from app.security import hash_password
from app.services.broker import broker
from app.version import __version__

logger = logging.getLogger("meyes")


def seed_admin() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)) is None:
            db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            db.commit()
            logger.info("Seeded default admin user (admin/admin) - change the password!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_admin()
    broker.set_loop(asyncio.get_running_loop())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="M-Eyes",
        description="Open-source DDI platform (DNS, DHCP, IPAM) with Fortinet ecosystem integration",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_routers = (
        auth.router, dashboard.router, networks.router, addresses.router, tags.router,
        zones.router, views.router, records.router, dhcp.router, hosts.router,
        feeds_admin.router, blocklist.router, changelog.router, deploy.router,
        runbook.router, logs.router, system.router, rpz.router, extattrs.router,
        search.router,
    )
    for router in api_routers:
        app.include_router(router, prefix="/api/v1")
    app.include_router(feeds_router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()

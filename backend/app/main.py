import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1 import (
    addresses,
    apikeys,
    auth,
    blocklist,
    certs,
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
from app.services import certs as certs_service
from app.services import threat_feeds as threat_feed_service
from app.services.broker import broker
from app.version import __version__

logger = logging.getLogger("meyes")

THREAT_FEED_CHECK_SECONDS = 1800  # how often due feeds are looked for


def _sync_due_threat_feeds() -> None:
    with SessionLocal() as db:
        for feed in threat_feed_service.feeds_due(db):
            threat_feed_service.sync_feed(db, feed)
            db.commit()


async def threat_feed_refresher() -> None:
    """Background loop: re-sync enabled threat feeds past their refresh interval."""
    while True:
        try:
            await asyncio.to_thread(_sync_due_threat_feeds)
        except Exception:  # noqa: BLE001 - the refresher must survive any feed error
            logger.exception("Threat feed auto-refresh failed")
        await asyncio.sleep(THREAT_FEED_CHECK_SECONDS)


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
    with SessionLocal() as db:
        certs_service.ensure_bootstrap(db)
    broker.set_loop(asyncio.get_running_loop())
    refresher = asyncio.create_task(threat_feed_refresher())
    yield
    refresher.cancel()


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
        search.router, certs.router, apikeys.router,
    )
    for router in api_routers:
        app.include_router(router, prefix="/api/v1")
    app.include_router(feeds_router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()

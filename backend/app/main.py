import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1 import (
    addresses,
    apikeys,
    assets,
    auth,
    automation,
    blocklist,
    certs,
    changelog,
    dashboard,
    deploy,
    dhcp,
    extattrs,
    feeds_admin,
    hosts,
    integrations,
    logs,
    networks,
    records,
    rpz,
    runbook,
    search,
    sso,
    system,
    tags,
    users,
    views,
    zones,
)
from app.config import DEFAULT_JWT_SECRET, get_settings
from app.database import SessionLocal, engine
from app.feeds.router import router as feeds_router
from app.models import Base, User
from app.security import hash_password
from app.services import automation as automation_service
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


def _run_due_automation() -> None:
    with SessionLocal() as db:
        automation_service.run_due(db)


async def automation_scheduler() -> None:
    """Background loop: run autonomous automation rules as they fall due."""
    while True:
        await asyncio.sleep(automation_service.SCHEDULER_TICK_SECONDS)
        try:
            await asyncio.to_thread(_run_due_automation)
        except Exception:  # noqa: BLE001 - the scheduler must survive any rule error
            logger.exception("Automation scheduler tick failed")


def seed_admin() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)) is None:
            db.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
            db.commit()
            logger.info("Seeded default admin user (admin/admin) - change the password!")


def _warn_insecure_defaults() -> None:
    if get_settings().jwt_secret == DEFAULT_JWT_SECRET:
        logger.warning(
            "MEYES_JWT_SECRET is the built-in development default; set a strong, unique "
            "secret in production - tokens are otherwise forgeable by anyone."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    _warn_insecure_defaults()
    seed_admin()
    with SessionLocal() as db:
        certs_service.ensure_bootstrap(db)
    broker.set_loop(asyncio.get_running_loop())
    refresher = asyncio.create_task(threat_feed_refresher())
    scheduler = asyncio.create_task(automation_scheduler())
    yield
    refresher.cancel()
    scheduler.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title="M-Eyes",
        description="Open-source DDI platform (DNS, DHCP, IPAM) with Fortinet ecosystem integration",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_routers = (
        auth.router, dashboard.router, networks.router, addresses.router, tags.router,
        zones.router, views.router, records.router, dhcp.router, hosts.router,
        feeds_admin.router, blocklist.router, changelog.router, deploy.router,
        runbook.router, logs.router, system.router, rpz.router, extattrs.router,
        search.router, certs.router, apikeys.router, users.router, sso.router,
        assets.router, integrations.router, automation.router,
    )
    for router in api_routers:
        app.include_router(router, prefix="/api/v1")
    app.include_router(feeds_router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": __version__}

    return app


app = create_app()

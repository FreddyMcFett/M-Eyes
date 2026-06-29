import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Event, User
from app.schemas.system import EventOut
from app.security import decode_access_token
from app.services.broker import broker

router = APIRouter(tags=["logs"])


def _filtered_events(db: Session, severity, category, search, limit):
    query = select(Event).order_by(Event.id.desc())
    if severity:
        query = query.where(Event.severity == severity)
    if category:
        query = query.where(Event.category == category)
    if search:
        query = query.where(Event.message.ilike(f"%{search}%"))
    return db.scalars(query.limit(limit)).all()


@router.get("/events", response_model=list[EventOut])
def list_events(
    severity: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Event).order_by(Event.id.desc())
    if severity:
        query = query.where(Event.severity == severity)
    if category:
        query = query.where(Event.category == category)
    if search:
        query = query.where(Event.message.ilike(f"%{search}%"))
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/events/export", response_class=PlainTextResponse)
def export_events(
    severity: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=5000, le=50000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the (optionally filtered) event log as a plain-text ``.log`` file.

    Lines are emitted oldest-first in a syslog-like shape so the file reads
    naturally and can be tailed/grep'd with standard tooling.
    """
    rows = list(_filtered_events(db, severity, category, search, limit))
    rows.reverse()  # chronological order in the file

    def fmt(event: Event) -> str:
        ts = event.ts if event.ts.tzinfo else event.ts.replace(tzinfo=UTC)
        stamp = ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{stamp}  {event.severity.upper():<7}  [{event.category}]  {event.message}"

    filters = [f"{k}={v}" for k, v in
               (("severity", severity), ("category", category), ("search", search)) if v]
    now = datetime.now(UTC)
    header = (
        "# M-Eyes event log export\n"
        f"# generated: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"# filters:   {', '.join(filters) or 'none'}\n"
        f"# events:    {len(rows)}\n"
        "#\n"
    )
    body = "\n".join(fmt(e) for e in rows)
    content = header + body + ("\n" if body else "")
    filename = f"m-eyes-events-{now.strftime('%Y%m%d-%H%M%S')}.log"
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/events/stream")
async def stream_events(token: str = ""):
    """SSE live event stream. EventSource cannot set headers, so auth uses ?token=<jwt>."""
    if decode_access_token(token) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid or missing token")

    queue = broker.subscribe()

    async def generator():
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {message}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

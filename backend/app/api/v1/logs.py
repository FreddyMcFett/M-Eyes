import asyncio

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Event, User
from app.schemas.system import EventOut
from app.security import decode_access_token
from app.services.broker import broker

router = APIRouter(tags=["logs"])


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

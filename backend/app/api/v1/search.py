from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import User
from app.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(q: str = Query(min_length=1), db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Search term must be at least 2 characters")
    return {"query": q, "results": search_service.search(db, q)}

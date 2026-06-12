from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.generators.runbook import render_runbook
from app.models import User

router = APIRouter(prefix="/runbook", tags=["versioning"])


@router.get("")
def runbook(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return render_runbook(db)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.graph import run_query
from app.schemas import Answer, QueryRequest, Source
from app.services import build_services
from app.storage.db import get_db

router = APIRouter()


@router.post("/query", response_model=Answer)
def query(request: QueryRequest, db: Session = Depends(get_db)) -> Answer:
    services = build_services(db)
    state = run_query(
        services,
        question=request.question,
        category=request.category,
        family_member=request.family_member,
    )
    return Answer(
        answer=state.get("answer", ""),
        sources=[Source(**s) for s in state.get("sources", [])],
        confidence=state.get("confidence", 0),
        warnings=state.get("warnings", []),
    )

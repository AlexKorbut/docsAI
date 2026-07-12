"""Upcoming obligations: payments with a due date within the next N days."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas import Reminder
from app.storage.db import get_db
from app.storage.models import Document, Payment

router = APIRouter()


@router.get("/reminders", response_model=list[Reminder])
def list_reminders(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[Reminder]:
    today = date.today()
    horizon = today + timedelta(days=days)
    rows = (
        db.query(Payment)
        .join(Document)
        .filter(Payment.due_date.isnot(None))
        .filter(Payment.due_date >= today, Payment.due_date <= horizon)
        .order_by(Payment.due_date)
        .limit(100)
        .all()
    )
    return [
        Reminder(
            document_id=p.document_id,
            document_title=p.document.title,
            category=p.document.category,
            amount=float(p.amount),
            currency=p.currency,
            due_date=p.due_date,
            description=p.description,
            days_left=(p.due_date - today).days,
        )
        for p in rows
    ]

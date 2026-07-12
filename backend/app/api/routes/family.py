"""Family member registry — documents are attached to members by name."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas import FamilyMemberIn, FamilyMemberOut
from app.storage.db import get_db
from app.storage.models import FamilyMember

router = APIRouter()


def _out(m: FamilyMember) -> FamilyMemberOut:
    return FamilyMemberOut(
        id=m.id, name=m.name, relation=m.relation, birth_date=m.birth_date, notes=m.notes
    )


@router.get("/family", response_model=list[FamilyMemberOut])
def list_members(db: Session = Depends(get_db)) -> list[FamilyMemberOut]:
    return [_out(m) for m in db.query(FamilyMember).order_by(FamilyMember.name).all()]


@router.post("/family", response_model=FamilyMemberOut, status_code=201)
def add_member(member: FamilyMemberIn, db: Session = Depends(get_db)) -> FamilyMemberOut:
    exists = db.query(FamilyMember).filter(FamilyMember.name == member.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Member with this name already exists")
    row = FamilyMember(**member.model_dump())
    db.add(row)
    db.flush()
    return _out(row)


@router.delete("/family/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)) -> None:
    row = db.get(FamilyMember, member_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(row)

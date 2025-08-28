from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import SessionLocal

router = APIRouter(prefix="/characters", tags=["characters"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.CharacterCard)
def create_character(card: schemas.CharacterCardCreate, db: Session = Depends(get_db)):
    db_card = models.CharacterCard(**card.dict())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


@router.get("/", response_model=list[schemas.CharacterCard])
def read_characters(db: Session = Depends(get_db)):
    return db.query(models.CharacterCard).all()


@router.get("/{card_id}", response_model=schemas.CharacterCard)
def read_character(card_id: int, db: Session = Depends(get_db)):
    card = db.get(models.CharacterCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Character not found")
    return card


@router.put("/{card_id}", response_model=schemas.CharacterCard)
def update_character(
    card_id: int, card_update: schemas.CharacterCardCreate, db: Session = Depends(get_db)
):
    card = db.get(models.CharacterCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Character not found")
    for key, value in card_update.dict().items():
        setattr(card, key, value)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=204)
def delete_character(card_id: int, db: Session = Depends(get_db)):
    card = db.get(models.CharacterCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(card)
    db.commit()

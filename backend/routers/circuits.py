from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/circuits")

@router.get("/", response_model=list[schemas.Circuit])
def list_circuits(db: Session = Depends(get_db)):
    return db.query(models.Circuit).all()

@router.post("/", response_model=schemas.Circuit, status_code=201)
def create_circuit(payload: schemas.CircuitCreate, db: Session = Depends(get_db)):
    circuit = models.Circuit(**payload.dict())
    db.add(circuit)
    db.commit()
    db.refresh(circuit)
    return circuit

@router.get("/{circuit_id}", response_model=schemas.Circuit)
def get_circuit(circuit_id: int, db: Session = Depends(get_db)):
    circuit = db.query(models.Circuit).get(circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
    return circuit

@router.put("/{circuit_id}", response_model=schemas.Circuit)
def update_circuit(circuit_id: int, payload: schemas.CircuitCreate, db: Session = Depends(get_db)):
    circuit = db.query(models.Circuit).get(circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
    for k, v in payload.dict().items():
        setattr(circuit, k, v)
    db.commit()
    db.refresh(circuit)
    return circuit

@router.delete("/{circuit_id}", status_code=204)
def delete_circuit(circuit_id: int, db: Session = Depends(get_db)):
    circuit = db.query(models.Circuit).get(circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")
    db.delete(circuit)
    db.commit()
    return None

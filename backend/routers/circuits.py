from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from ..circuit_engine import CircuitExecutor, CircuitValidator, CircuitParser
from ..config import load_config

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


# --- Execution Endpoints ---

class ExecuteCircuitRequest(BaseModel):
    inputs: Dict[str, Any] = {}
    character_id: Optional[int] = None
    session_id: Optional[str] = None


class ExecuteCircuitResponse(BaseModel):
    success: bool
    output: str = ""
    variables: Dict[str, Any] = {}
    execution_ms: float = 0.0
    logs: List[Dict[str, Any]] = []
    error: Optional[str] = None


@router.post("/{circuit_id}/execute", response_model=ExecuteCircuitResponse)
def execute_circuit(
    circuit_id: int,
    request: ExecuteCircuitRequest,
    db: Session = Depends(get_db)
):
    """Execute a circuit with given inputs and return results."""
    # Get circuit from database
    circuit = db.query(models.Circuit).get(circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    try:
        # Create executor
        executor = CircuitExecutor(db=db)

        # Execute circuit
        result = executor.execute_circuit(
            circuit,
            request.inputs,
            request.character_id
        )

        return ExecuteCircuitResponse(**result)

    except Exception as e:
        return ExecuteCircuitResponse(
            success=False,
            error=str(e),
            execution_ms=0.0,
            output="",
            variables={},
            logs=[]
        )


@router.post("/{circuit_id}/validate")
def validate_circuit(circuit_id: int, db: Session = Depends(get_db)):
    """Validate a circuit's structure and return validation results."""
    circuit = db.query(models.Circuit).get(circuit_id)
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    try:
        # Parse and validate
        circuit_data = CircuitParser.parse_circuit(circuit.data)
        errors = CircuitValidator.validate_circuit(circuit_data)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "node_count": len(circuit_data.nodes),
            "edge_count": len(circuit_data.edges)
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "node_count": 0,
            "edge_count": 0
        }


@router.post("/validate-raw")
def validate_circuit_raw(request: Dict[str, Any]):
    """Validate raw circuit data structure."""
    try:
        circuit_data = CircuitParser.parse_circuit(request)
        errors = CircuitValidator.validate_circuit(circuit_data)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "node_count": len(circuit_data.nodes),
            "edge_count": len(circuit_data.edges)
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "node_count": 0,
            "edge_count": 0
        }

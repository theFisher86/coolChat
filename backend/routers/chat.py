from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..database import get_db
from ..circuit_integrations import CircuitIntegrationAdapter

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    circuit_id: Optional[int] = None
    circuit_outputs: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str

@router.post("", response_model=ChatResponse)
async def create_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    # Basic integration: if circuit outputs have system_prompt, use it
    system_prompt = None
    if payload.circuit_outputs and 'system_prompt' in payload.circuit_outputs:
        system_prompt = payload.circuit_outputs['system_prompt']
    elif payload.circuit_id:
        # If only circuit_id, perhaps load and execute later, but for now simple
        pass
    
    adapter = CircuitIntegrationAdapter(db)
    if system_prompt:
        # Call LLM with system prompt
        from ..models import Character  # For example, if needed
        reply = adapter.call_llm('openai', 'gpt-4o-mini', payload.message, system_msg=system_prompt)
    else:
        # Default: call without system prompt
        reply = adapter.call_llm('openai', 'gpt-4o-mini', payload.message)
    
    return ChatResponse(reply=reply)

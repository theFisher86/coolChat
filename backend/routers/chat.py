from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def create_chat(payload: ChatRequest) -> ChatResponse:
    """Return a simple echo of the provided message."""

    return ChatResponse(reply=f"Echo: {payload.message}")

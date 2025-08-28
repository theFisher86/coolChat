"""Primary FastAPI application for the CoolChat backend.

This module currently exposes a couple of utility endpoints as well as a very
small in-memory implementation of "character cards".  The goal is to mimic a
subset of SillyTavern's functionality so the front-end can store and retrieve
character definitions.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI(title="CoolChat")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models and in-memory storage
# ---------------------------------------------------------------------------


class Character(BaseModel):
    """Representation of a character card.

    For now we only keep a few basic fields.  The ``id`` is assigned by the
    server when the character is created.
    """

    id: int
    name: str
    description: str = ""
    avatar_url: str | None = None


class CharacterCreate(BaseModel):
    """Payload used when creating a new character."""

    name: str
    description: str = ""
    avatar_url: str | None = None


# simple in-memory store
_characters: Dict[int, Character] = {}
_next_id: int = 1


@app.get("/")
async def root():
    """Basic sanity check endpoint for the API root."""
    return {"message": "CoolChat backend running"}

@app.get("/health")
async def health_check():
    """Simple endpoint to confirm the service is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Character endpoints
# ---------------------------------------------------------------------------


@app.get("/characters", response_model=List[Character])
async def list_characters() -> List[Character]:
    """Return all stored character cards."""

    return list(_characters.values())


@app.post("/characters", response_model=Character, status_code=201)
async def create_character(payload: CharacterCreate) -> Character:
    """Create a new character and return the resulting record."""

    global _next_id
    char = Character(id=_next_id, **payload.model_dump())
    _characters[_next_id] = char
    _next_id += 1
    return char


@app.get("/characters/{char_id}", response_model=Character)
async def get_character(char_id: int) -> Character:
    """Fetch a single character by its identifier."""

    char = _characters.get(char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@app.delete("/characters/{char_id}", status_code=204)
async def delete_character(char_id: int) -> None:
    """Remove a character from the store."""

    if char_id not in _characters:
        raise HTTPException(status_code=404, detail="Character not found")
    del _characters[char_id]
    return None


# ---------------------------------------------------------------------------
# Lorebook endpoints
# ---------------------------------------------------------------------------


class LoreEntry(BaseModel):
    """Simple world info entry used for context injection."""

    id: int
    keyword: str
    content: str


class LoreEntryCreate(BaseModel):
    keyword: str
    content: str


_lore: Dict[int, LoreEntry] = {}
_next_lore_id: int = 1


@app.get("/lore", response_model=List[LoreEntry])
async def list_lore() -> List[LoreEntry]:
    """Return all lore entries."""

    return list(_lore.values())


@app.post("/lore", response_model=LoreEntry, status_code=201)
async def create_lore(payload: LoreEntryCreate) -> LoreEntry:
    """Create a new lore entry."""

    global _next_lore_id
    entry = LoreEntry(id=_next_lore_id, **payload.model_dump())
    _lore[_next_lore_id] = entry
    _next_lore_id += 1
    return entry


@app.get("/lore/{entry_id}", response_model=LoreEntry)
async def get_lore(entry_id: int) -> LoreEntry:
    """Retrieve a single lore entry."""

    entry = _lore.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    return entry


@app.delete("/lore/{entry_id}", status_code=204)
async def delete_lore(entry_id: int) -> None:
    """Delete a lore entry."""

    if entry_id not in _lore:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    del _lore[entry_id]
    return None


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------


class MemoryEntry(BaseModel):
    """Persisted memory snippet with an auto-generated summary."""

    id: int
    content: str
    summary: str


class MemoryCreate(BaseModel):
    """Incoming payload for a new memory entry."""

    content: str


_memory: Dict[int, MemoryEntry] = {}
_next_memory_id: int = 1


def _summarize(text: str, width: int = 60) -> str:
    """Create a short summary for the supplied text."""

    import textwrap

    return textwrap.shorten(text, width=width, placeholder="...")


@app.get("/memory", response_model=List[MemoryEntry])
async def list_memory() -> List[MemoryEntry]:
    """Return all stored memory entries."""

    return list(_memory.values())


@app.post("/memory", response_model=MemoryEntry, status_code=201)
async def create_memory(payload: MemoryCreate) -> MemoryEntry:
    """Store a new memory entry with an auto-generated summary."""

    global _next_memory_id
    entry = MemoryEntry(
        id=_next_memory_id,
        content=payload.content,
        summary=_summarize(payload.content),
    )
    _memory[_next_memory_id] = entry
    _next_memory_id += 1
    return entry


@app.get("/memory/{entry_id}", response_model=MemoryEntry)
async def get_memory(entry_id: int) -> MemoryEntry:
    """Retrieve a memory entry by identifier."""

    entry = _memory.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return entry


@app.delete("/memory/{entry_id}", status_code=204)
async def delete_memory(entry_id: int) -> None:
    """Remove a memory entry from the store."""

    if entry_id not in _memory:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    del _memory[entry_id]
    return None


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat message payload."""

    message: str


class ChatResponse(BaseModel):
    """Simple echo response returned to the caller."""

    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Echo the provided message back to the client.

    This placeholder endpoint lets the front-end exercise a basic chat
    workflow while more sophisticated LLM integrations are developed.
    """

    return ChatResponse(reply=f"Echo: {payload.message}")


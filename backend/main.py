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
import asyncio
import httpx
from .config import AppConfig, load_config, save_config, mask_secret, Provider
import os

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


async def _llm_reply(message: str, cfg: AppConfig) -> str:
    # In test environments, avoid external calls unless explicitly allowed.
    def _external_enabled() -> bool:
        if os.getenv("COOLCHAT_ALLOW_EXTERNAL") == "1":
            return True
        # If pytest is running, default to disabled
        return os.getenv("PYTEST_CURRENT_TEST") is None

    # Provider: echo (default)
    if cfg.provider == Provider.ECHO:
        return f"Echo: {message}"

    # If external calls are disabled, fallback to echo behavior
    if not _external_enabled():
        return f"Echo: {message}"

    # Provider: openai (or compatible)
    if cfg.provider == Provider.OPENAI:
        if not cfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'openai'")

        url = cfg.api_base.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": cfg.model,
            "messages": [
                {"role": "user", "content": message},
            ],
            "temperature": cfg.temperature,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                # Pass through error details where possible
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            data = resp.json()
            # Standard OpenAI response shape
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    # Provider: openrouter (OpenAI-compatible)
    if cfg.provider == Provider.OPENROUTER:
        if not cfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'openrouter'")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        # Optional: pass through referer/title if set as env (not required)
        referer = os.getenv("COOLCHAT_HTTP_REFERER")
        title = os.getenv("COOLCHAT_X_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title

        body = {
            "model": cfg.model,
            "messages": [
                {"role": "user", "content": message},
            ],
            "temperature": cfg.temperature,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    # Provider: gemini
    if cfg.provider == Provider.GEMINI:
        if not cfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'gemini'")

        # Use OpenAI-compatible endpoint with Authorization header
        base = (cfg.api_base or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        path = "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        }
        body = {
            "model": cfg.model or "gemini-1.5-flash",
            "messages": [
                {"role": "user", "content": message},
            ],
            "temperature": cfg.temperature,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(base_url=base, timeout=timeout) as client:
            resp = await client.post(path, headers=headers, json=body)
            if resp.status_code >= 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    # Unknown provider
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {cfg.provider}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Return a chat reply using configured provider (echo by default)."""

    cfg = load_config()
    try:
        reply = await _llm_reply(payload.message, cfg)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(reply=reply)


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------


class ConfigResponse(BaseModel):
    provider: str
    api_key_masked: str | None = None
    api_base: str
    model: str
    temperature: float


class ConfigUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    api_base: str | None = None
    model: str | None = None
    temperature: float | None = None


@app.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    cfg = load_config()
    return ConfigResponse(
        provider=cfg.provider,
        api_key_masked=mask_secret(cfg.api_key),
        api_base=cfg.api_base,
        model=cfg.model,
        temperature=cfg.temperature,
    )


@app.put("/config", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdate) -> ConfigResponse:
    cfg = load_config()
    if payload.provider is not None:
        cfg.provider = payload.provider
    if payload.api_key is not None:
        cfg.api_key = payload.api_key
    if payload.api_base is not None:
        cfg.api_base = payload.api_base
    if payload.model is not None:
        cfg.model = payload.model
    if payload.temperature is not None:
        cfg.temperature = payload.temperature

    # Apply sensible defaults if fields left blank for certain providers
    if cfg.provider == Provider.OPENAI:
        if not cfg.api_base:
            cfg.api_base = "https://api.openai.com/v1"
        if not cfg.model:
            cfg.model = "gpt-4o-mini"
    elif cfg.provider == Provider.OPENROUTER:
        if not cfg.api_base:
            cfg.api_base = "https://openrouter.ai/api/v1"
        if not cfg.model:
            cfg.model = "openrouter/auto"
    elif cfg.provider == Provider.GEMINI:
        # Gemini OpenAI-compatible base and default model
        if not cfg.api_base:
            cfg.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        if not cfg.model:
            cfg.model = "gemini-1.5-flash"

    try:
        save_config(cfg)
    except Exception as e:  # propagate as HTTP error to surface 500s
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")
    return ConfigResponse(
        provider=cfg.provider,
        api_key_masked=mask_secret(cfg.api_key),
        api_base=cfg.api_base,
        model=cfg.model,
        temperature=cfg.temperature,
    )


# ---------------------------------------------------------------------------
# Models endpoint (provider-aware)
# ---------------------------------------------------------------------------


class ModelsResponse(BaseModel):
    models: List[str]


@app.get("/models", response_model=ModelsResponse)
async def list_models(provider: str | None = None) -> ModelsResponse:
    cfg = load_config()
    p = provider or cfg.provider

    async def _err(detail):
        raise HTTPException(status_code=400, detail=detail)

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

    if p == Provider.ECHO:
        return ModelsResponse(models=[])

    if p == Provider.OPENAI:
        if not cfg.api_key:
            await _err("Missing API key for openai")
        base = (cfg.api_base or "https://api.openai.com/v1").rstrip("/")
        url = base + "/models"
        headers = {"Authorization": f"Bearer {cfg.api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=502, detail=detail)
        data = resp.json()
        ids = []
        for item in data.get("data", []):
            mid = item.get("id") or item.get("name")
            if mid:
                ids.append(mid)
        return ModelsResponse(models=ids)

    if p == Provider.OPENROUTER:
        url = "https://openrouter.ai/api/v1/models"
        headers = {}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=502, detail=detail)
        data = resp.json()
        ids = []
        for item in data.get("data", []):
            mid = item.get("id") or item.get("name")
            if mid:
                ids.append(mid)
        return ModelsResponse(models=ids)

    if p == Provider.GEMINI:
        if not cfg.api_key:
            await _err("Missing API key for gemini")
        base = (cfg.api_base or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        url = base + "/models"
        headers = {"Authorization": f"Bearer {cfg.api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=502, detail=detail)
        data = resp.json()
        ids = []
        for item in data.get("data", []):
            mid = item.get("id") or item.get("name")
            if mid:
                ids.append(mid)
        return ModelsResponse(models=ids)

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {p}")


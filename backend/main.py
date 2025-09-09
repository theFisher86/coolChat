"""Primary FastAPI application for the CoolChat backend.

This module currently exposes a couple of utility endpoints as well as a very
small in-memory implementation of "character cards".  The goal is to mimic a
subset of SillyTavern's functionality so the front-end can store and retrieve
character definitions.
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Union
import asyncio
import httpx
import json
import time
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from .config import AppConfig, ProviderConfig, load_config, save_config, mask_secret, Provider, ImagesConfig, ImageProvider
from .models import Lorebook, LoreEntry, Character as CharacterModel
from .storage import load_json, save_json, public_dir
from .database import SessionLocal, get_db
from sqlalchemy.orm import Session
from .routers import lore
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

# Development bypass endpoint for testing
@app.get("/test", summary="Development testing endpoint", include_in_schema=False)
async def test_endpoint():
    """Bypass endpoint for testing when auth issues occur in development.

    This endpoint is for testing purposes only and bypasses any potential
    authentication middleware issues during local development.
    """
    return {
        "status": "ok",
        "message": "CoolChat backend accessible",
        "endpoint": "/test",
        "bypass_for_testing": True,
        "timestamp": time.time(),
        "health_check": "/health",
        "api_docs": "/docs"
    }

# Serve static files (e.g., imported character images) from repo ./public
try:
    import os as _os
    _public_dir = _os.path.join(_os.path.dirname(__file__), "..", "public")
    _public_dir = _os.path.abspath(_public_dir)
    _os.makedirs(_public_dir, exist_ok=True)
    app.mount("/public", StaticFiles(directory=_public_dir), name="public")
except Exception:
    pass

# Serve extensions folder (manifests and client code)
try:
    _ext_dir = _os.path.join(_os.path.dirname(__file__), "..", "extensions")
    _ext_dir = _os.path.abspath(_ext_dir)
    _os.makedirs(_ext_dir, exist_ok=True)
    app.mount("/plugins/static", StaticFiles(directory=_ext_dir), name="plugins_static")
except Exception:
    pass

# Include routers
app.include_router(lore.router, tags=["lore"])
app.include_router(characters.router, tags=["characters"])

# Serve debug.json file for frontend access
@app.get("/debug.json")
async def get_debug_config():
    """Serve debug.json file for frontend access."""
    from .debug import get_debug_logger
    logger = get_debug_logger()
    try:
        from pathlib import Path
        debug_file = Path(__file__).parent.parent / "debug.json"
        if debug_file.exists():
            import json
            data = json.loads(debug_file.read_text())
            return data
        else:
            return logger.config
    except Exception as e:
        # Return current loaded config if file access fails
        return logger.config


@app.post("/phone/debug")
async def phone_debug(payload: Dict[str, object]):
    try:
        from .debug import get_debug_logger
        logger = get_debug_logger()
        logger.debug_api_calls(f"Phone debug: {payload}")
    except Exception:
        pass
    return {"status": "ok"}


@app.on_event("startup")
async def _startup_load_state():
    try:
        # Create SQLite tables if they don't exist
        from .database import create_tables
        create_tables()
        logger = get_debug_logger()
        logger.debug_db("[CoolChat] SQLite tables created/verified")

        # Load existing JSON state
        _load_state()

        # Migrate existing data to SQLite
        _migrate_to_sqlite()

    except Exception as e:
        try:
            logger = get_debug_logger()
            logger.debug_db("[CoolChat] startup load_state error:" + str(e))
        except Exception:
            pass


# Extensions API: list available extensions and manage enabled map
@app.get("/plugins")
async def list_plugins():
    # Read manifests from extensions folder
    out = {"plugins": [], "enabled": {}}
    cfg = load_config()
    try:
        base = _ext_dir
        for name in sorted(os.listdir(base)):
            mpath = os.path.join(base, name, "manifest.json")
            if os.path.isfile(mpath):
                try:
                    with open(mpath, 'r', encoding='utf-8') as f:
                        import json as _json
                        data = _json.load(f)
                        data['id'] = data.get('id') or name
                        out['plugins'].append(data)
                except Exception:
                    continue
    except Exception:
        pass
    # Enabled map from config
    try:
        out['enabled'] = cfg.extensions if isinstance(cfg.extensions, dict) else {}
    except Exception:
        out['enabled'] = {}
    return out


@app.post('/plugins/enabled')
async def set_enabled_extensions(payload: Dict[str, bool]):
    try:
        cfg = load_config()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail='Invalid payload')
        cfg.extensions = payload
        save_config(cfg)
        return {'status': 'ok'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    # Extended fields inspired by SillyTavern
    first_message: str | None = None
    alternate_greetings: List[str] = []
    scenario: str | None = None
    system_prompt: str | None = None
    personality: str | None = None
    mes_example: str | None = None
    creator_notes: str | None = None
    tags: List[str] = []
    post_history_instructions: str | None = None
    extensions: Dict[str, object] | None = None
    lorebook_ids: List[int] = []
    image_prompt_prefix: str | None = None
    image_prompt_suffix: str | None = None

    class Config:
        orm_mode = True


class CharacterCreate(BaseModel):
    """Payload used when creating a new character."""

    name: str
    description: str = ""
    avatar_url: str | None = None
    first_message: Optional[str] = None
    alternate_greetings: Optional[List[str]] = None
    scenario: Optional[str] = None
    system_prompt: Optional[str] = None
    personality: Optional[str] = None
    mes_example: Optional[str] = None
    creator_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    post_history_instructions: Optional[str] = None
    extensions: Optional[Dict[str, object]] = None
    lorebook_ids: Optional[List[int]] = None
    image_prompt_prefix: Optional[str] = None
    image_prompt_suffix: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    first_message: Optional[str] = None
    alternate_greetings: Optional[List[str]] = None
    scenario: Optional[str] = None
    system_prompt: Optional[str] = None
    personality: Optional[str] = None
    mes_example: Optional[str] = None
    creator_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    post_history_instructions: Optional[str] = None
    extensions: Optional[Dict[str, object]] = None
    lorebook_ids: Optional[List[int]] = None
    image_prompt_prefix: Optional[str] = None
    image_prompt_suffix: Optional[str] = None


class LorebookCreate(BaseModel):
    name: str
    description: str | None = None
    entries: Optional[List[dict]] = None


class LoreEntryCreate(BaseModel):
    keyword: str
    content: str
    keywords: Optional[List[str]] = None
    secondary_keywords: Optional[List[str]] = None
    logic: str | None = None
    trigger: float | None = None
    order: float | None = None



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
async def list_characters(db: Session = Depends(get_db)) -> List[Character]:
    """Return all stored character cards."""

    return db.query(CharacterModel).all()


@app.post("/characters", response_model=Character, status_code=201)
async def create_character(payload: CharacterCreate, db: Session = Depends(get_db)) -> Character:
    """Create a new character and return the resulting record."""

    data = payload.model_dump()
    lorebook_ids = data.pop("lorebook_ids", []) or []
    if data.get("alternate_greetings") is None:
        data["alternate_greetings"] = []
    if data.get("tags") is None:
        data["tags"] = []
    char = CharacterModel(**data)
    if lorebook_ids:
        char.lorebooks = db.query(Lorebook).filter(Lorebook.id.in_(lorebook_ids)).all()
    db.add(char)
    db.commit()
    db.refresh(char)
    return char


@app.get("/characters/{char_id}", response_model=Character)
async def get_character(char_id: int, db: Session = Depends(get_db)) -> Character:
    """Fetch a single character by its identifier."""

    char = db.get(CharacterModel, char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return char


@app.delete("/characters/{char_id}", status_code=204)
async def delete_character(char_id: int, db: Session = Depends(get_db)) -> None:
    """Remove a character from the store."""

    char = db.get(CharacterModel, char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(char)
    db.commit()
    return None


@app.put("/characters/{char_id}", response_model=Character)
async def update_character(char_id: int, payload: CharacterUpdate, db: Session = Depends(get_db)) -> Character:
    char = db.get(CharacterModel, char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    data = payload.model_dump(exclude_unset=True)
    lorebook_ids = data.pop("lorebook_ids", None)
    for key, value in data.items():
        setattr(char, key, value)
    if lorebook_ids is not None:
        char.lorebooks = db.query(Lorebook).filter(Lorebook.id.in_(lorebook_ids)).all()
    db.commit()
    db.refresh(char)
    return char


# ---------------------------------------------------------------------------
# Lorebook endpoints
# ---------------------------------------------------------------------------


# In-memory lore and lorebooks removed - now using database-backed system


# Legacy in-memory lore endpoints removed - using database system now


# Removed all conflicting legacy lorebook endpoints - now using database router


# Legacy lorebook endpoints removed - now using database system
# Legacy lorebook entry update endpoint removed - now using database router


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


def _load_state() -> None:
    global _lore, _next_lore_id, _lorebooks, _next_lorebook_id, _memory, _next_memory_id, _chat_histories

    # Characters are stored in the database; no need to load from JSON

    data = load_json("lore.json", {"next_id": 1, "items": []})
    _next_lore_id = int(data.get("next_id", 1))
    _lore = {}
    for e in data.get("items", []):
        # Handle migration from old format (keyword) to new format (keywords, title)
        try:
            if "keyword" in e and "keywords" not in e:
                # Old format: convert keyword to keywords list and use as title
                e["keywords"] = [e["keyword"]]
                e["title"] = e["keyword"]
            _lore[e["id"]] = LoreEntry(**e)
        except Exception as inner_e:
            # Skip invalid entries during load
            print(f"[CoolChat] Skipping invalid lore entry {e.get('id', 'unknown')}: {inner_e}")
            continue

    data = load_json("lorebooks.json", {"next_id": 1, "items": []})
    _next_lorebook_id = int(data.get("next_id", 1))
    _lorebooks = {}
    for lb in data.get("items", []):
        # Handle migration from old format (entry_ids) to new database format
        try:
            # Remove entry_ids as they don't belong in Lorebook model anymore
            lb_clean = {k: v for k, v in lb.items() if k != 'entry_ids'}
            _lorebooks[lb["id"]] = Lorebook(**lb_clean)
        except Exception as inner_e:
            print(f"[CoolChat] Skipping invalid lorebook {lb.get('id', 'unknown')}: {inner_e}")
            continue

    data = load_json("memory.json", {"next_id": 1, "items": []})
    _next_memory_id = int(data.get("next_id", 1))
    _memory = {m["id"]: MemoryEntry(**m) for m in data.get("items", [])}

    globals_dict = load_json("histories.json", {})
    _chat_histories.clear(); _chat_histories.update(globals_dict)


def _safe_name(name: str) -> str:
    import re
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "").strip())
    return s or "item"


def _export_lorebook_st_json(lb: "Lorebook") -> Dict[str, object]:
    entries = []
    for eid in lb.entry_ids:
        e = _lore.get(eid)
        if not e:
            continue
        entries.append({"keys": [e.keyword], "content": e.content})
    return {"name": lb.name, "description": lb.description, "entries": entries}


def _save_lorebook_snapshot(lb: "Lorebook") -> None:
    import json as _json
    ldir = public_dir() / "lorebooks"
    try:
        ldir.mkdir(parents=True, exist_ok=True)
        fname = f"{lb.id}_{_safe_name(lb.name)}.json"
        (ldir / fname).write_text(_json.dumps(_export_lorebook_st_json(lb), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _save_lore() -> None:
    save_json("lore.json", {"next_id": _next_lore_id, "items": [e.model_dump() for e in _lore.values()]})


def _save_lorebooks() -> None:
    save_json("lorebooks.json", {"next_id": _next_lorebook_id, "items": [lb.model_dump() for lb in _lorebooks.values()]})


def _save_memory() -> None:
    save_json("memory.json", {"next_id": _next_memory_id, "items": [m.model_dump() for m in _memory.values()]})


def _save_histories() -> None:
    save_json("histories.json", _chat_histories)


def _get_character(char_id: int) -> CharacterModel | None:
    """Helper to fetch a character from the database by ID."""
    db = SessionLocal()
    try:
        return db.get(CharacterModel, char_id)
    finally:
        db.close()


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
    _save_memory()
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
    _save_memory()
    return None


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat message payload."""

    message: str
    session_id: str | None = None
    reset: bool | None = None


class ChatResponse(BaseModel):
    """Simple echo response returned to the caller."""

    reply: str


def _active_provider_cfg(cfg: AppConfig) -> tuple[str, ProviderConfig]:
    p = cfg.active_provider
    pc = cfg.providers.get(p)
    if pc is None:
        # Fallback to echo config if missing
        p = Provider.ECHO
        pc = cfg.providers.get(p, ProviderConfig())
    return p, pc


async def _llm_reply(
    message: str,
    cfg: AppConfig,
    recent_text: str | None = None,
    system_override: str | None = None,
    disable_system: bool = False,
) -> str:
    # In test environments, avoid external calls unless explicitly allowed.
    def _external_enabled() -> bool:
        if os.getenv("COOLCHAT_ALLOW_EXTERNAL") == "1":
            return True
        # If pytest is running, default to disabled
        return os.getenv("PYTEST_CURRENT_TEST") is None

    # Provider: echo (default)
    provider, pcfg = _active_provider_cfg(cfg)

    if provider == Provider.ECHO:
        return f"Echo: {message}"

    # If external calls are disabled, fallback to echo behavior
    if not _external_enabled():
        return f"Echo: {message}"

    # Provider: openai (or compatible)
    # Build optional system message from active character and user persona, respecting token limit
    char = _get_character(cfg.active_character_id) if getattr(cfg, "active_character_id", None) else None
    system_msg = None if disable_system else (
        system_override if system_override is not None else _build_system_from_character(
            char,
            getattr(cfg, 'user_persona', None),
            (getattr(cfg.providers.get(provider, ProviderConfig()), 'max_context_tokens', None) or getattr(cfg, 'max_context_tokens', 2048)),
            recent_text or "",
        )
    )

    # Replace tokens in messages
    def _replace(text: str) -> str:
        char_name = char.name if char else None
        user_name = getattr(cfg, 'user_persona', None).name if getattr(cfg, 'user_persona', None) else "User"
        if not text:
            return text
        t = text.replace("{{char}}", char_name or "Character")
        t = t.replace("{{user}}", user_name)
        # Custom variables from prompts.json
        try:
            from .storage import load_json as _lj
            pdata = _lj("prompts.json", {})
            vars = pdata.get("variables", {}) if isinstance(pdata, dict) else {}
            if isinstance(vars, dict):
                for k, v in vars.items():
                    if isinstance(k, str) and isinstance(v, str):
                        t = t.replace("{{"+k+"}}", v)
        except Exception:
            pass
        return t
    if system_msg:
        system_msg = _replace(system_msg)
    message = _replace(message)

    if provider == Provider.OPENAI:
        if not pcfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'openai'")

        base = (pcfg.api_base or "https://api.openai.com/v1").rstrip("/")
        url = base + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {pcfg.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": message})
        body = {"model": pcfg.model, "messages": messages, "temperature": pcfg.temperature}
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_prompts', False):
            from .debug import get_debug_logger
            logger = get_debug_logger()
            logger.debug_llm_requests(f"OpenAI request: {url}, body: {body}")
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                # Pass through error details where possible
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_responses', False):
                try:
                    from .debug import get_debug_logger
                    logger = get_debug_logger()
                    logger.debug_llm_responses(f"OpenAI response: {resp.json()}")
                except Exception:
                    logger.debug_llm_responses(f"OpenAI response text: {resp.text}")
            data = resp.json()
            # Standard OpenAI response shape
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    # Provider: openrouter (OpenAI-compatible)
    if provider == Provider.OPENROUTER:
        if not pcfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'openrouter'")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {pcfg.api_key}",
            "Content-Type": "application/json",
        }
        # Optional: pass through referer/title if set as env (not required)
        referer = os.getenv("COOLCHAT_HTTP_REFERER")
        title = os.getenv("COOLCHAT_X_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": message})
        body = {"model": pcfg.model, "messages": messages, "temperature": pcfg.temperature}
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_prompts', False):
            print("[CoolChat] OpenRouter request:", {"url": url, "body": body})
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_responses', False):
                try:
                    print("[CoolChat] OpenRouter response:", resp.json())
                except Exception:
                    print("[CoolChat] OpenRouter response text:", resp.text)
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    # Provider: gemini
    if provider == Provider.GEMINI:
        if not pcfg.api_key:
            raise HTTPException(status_code=400, detail="Missing API key for provider 'gemini'")

        # Use OpenAI-compatible endpoint with Authorization header
        base = (pcfg.api_base or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        path = "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {pcfg.api_key}",
        }
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": message})
        body = {"model": pcfg.model or "gemini-1.5-flash", "messages": messages, "temperature": pcfg.temperature}
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_prompts', False):
            print("[CoolChat] Gemini request:", {"base": base, "path": path, "body": body})
        async with httpx.AsyncClient(base_url=base, timeout=timeout) as client:
            resp = await client.post(path, headers=headers, json=body)
            if resp.status_code >= 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise HTTPException(status_code=502, detail={"provider_error": detail})
            if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_responses', False):
                try:
                    print("[CoolChat] Gemini response:", resp.json())
                except Exception:
                    print("[CoolChat] Gemini response text:", resp.text)
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception:
                raise HTTPException(status_code=502, detail={"provider_error": "Unexpected response schema"})

    if provider == Provider.POLLINATIONS:
        # text.pollinations.ai provides OpenAI-compatible chat completions under /openai
        base = (pcfg.api_base or "https://text.pollinations.ai").rstrip("/")
        url = base + "/openai/chat/completions"
        headers = {"Content-Type": "application/json"}
        if pcfg.api_key:
            headers["Authorization"] = f"Bearer {pcfg.api_key}"
        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        messages.append({"role": "user", "content": message})
        body = {"model": pcfg.model or "openai-large", "messages": messages, "temperature": pcfg.temperature}
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

    # Unknown provider
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Return a chat reply using configured provider (echo by default)."""

    cfg = load_config()
    # Chat history per session
    session_id = payload.session_id or "default"
    if payload.reset:
        # Clear chat history from SQLite
        from .database import SessionLocal
        from .models import ChatMessage
        db = SessionLocal()
        try:
            db.query(ChatMessage).filter(ChatMessage.chat_id == session_id).delete()
            db.commit()
        except Exception as e:
            print(f"[CoolChat] Error resetting chat {session_id}: {e}")
            db.rollback()
        finally:
            db.close()
    history = _load_chat_session(session_id)
    # Build recent text window for lore triggers
    recent_text = "\n".join([m.get("content", "") for m in history[-6:]] + [payload.message])
    try:
        reply = await _llm_reply(payload.message, cfg, recent_text=recent_text)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=str(exc))

    # Record history and trim by rough token budget using SQLite
    _save_chat_message(session_id, "user", payload.message)
    _save_chat_message(session_id, "assistant", reply)
    _trim_history(session_id, cfg)

    # Log the reply for tool calling debugging
    from .debug import get_debug_logger
    logger = get_debug_logger()
    logger.debug_llm_responses(f"Returning reply: {repr(reply)}")
    if 'toolCalls' in reply or 'image_request' in reply or 'phone_url' in reply:
        logger.debug_tool_calls("Reply contains tool call")
    else:
        logger.debug_tool_calls("Reply contains no tool calls")

    return ChatResponse(reply=reply)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    if _estimate_tokens(text) <= max_tokens:
        return text
    target_chars = max_tokens * 4
    return text[:target_chars] + "\n..."


def _build_system_from_character(
    char: Optional[Character],
    user_persona: Optional[object] = None,
    max_tokens: int = 2048,
    recent_text: str = "",
) -> Optional[str]:
    segments: List[str] = []
    # Include active global prompts if any
    try:
        from .storage import load_json as _lj
        prompts = _lj("prompts.json", {"active": [], "all": [], "system": {}})
        system_prompts = prompts.get("system", {}) if isinstance(prompts, dict) else {}
        for p in prompts.get("active", []) or []:
            if isinstance(p, str) and p.strip():
                segments.append(p.strip())
            elif isinstance(p, dict) and p.get("text"):
                segments.append(str(p.get("text")))
    except Exception:
        pass
    # Build pieces for template variables
    persona_text = None
    if user_persona and getattr(user_persona, "name", None):
        persona_text = (f"User Persona: {user_persona.name}\n{getattr(user_persona, 'description', '')}").strip()
    char_text = None
    if char:
        ch_parts = []
        if char.system_prompt: ch_parts.append(char.system_prompt)
        if char.personality: ch_parts.append(f"Personality: {char.personality}")
        if char.scenario: ch_parts.append(f"Scenario: {char.scenario}")
        if char.description: ch_parts.append(f"Description: {char.description}")
        char_text = "\n".join(ch_parts) if ch_parts else None

    # Tools list and tool_call prompt
    tools_lines = []
    try:
        from .storage import load_json as _lj2
        _tools = _lj2("tools.json", {"enabled": {}})
        en = (_tools.get("enabled") or {}) if isinstance(_tools, dict) else {}
        if en.get("phone"): tools_lines.append("PhonePanel: Open a URL on the user's phone panel.")
        if en.get("image_gen"): tools_lines.append("ImageGen: Request an image with a concise prompt.")
        if en.get("lore_suggest"): tools_lines.append("LoreSuggest: Suggest new lore entries (keyword + content).")
    except Exception:
        pass
    tool_list_text = "\n".join(tools_lines)
    # tool_call prompt from user settings or default
    tool_call_prompt = None
    if isinstance(system_prompts, dict) and system_prompts.get("tool_call"):
        tool_call_prompt = str(system_prompts.get("tool_call"))
    else:
        try:
            if getattr(load_config(), 'structured_output', False):
                tool_call_prompt = (
                    "When invoking tools, return JSON with key 'toolCalls' as an array of {type, payload}. "
                    "Types: 'image_request' (payload: {prompt:string}), 'phone_url' (payload:{url:string}), 'lore_suggestions' (payload:{items:[{keyword:string, content:string}]}). "
                    "Optionally include plain 'text' content outside of tool calls. Do not wrap JSON in code fences."
                )
        except Exception:
            pass

    # Tool call prompt from user settings or default based on provider capabilities
    if not tool_call_prompt and isinstance(system_prompts, dict):
        tool_call_prompt = system_prompts.get("tool_call")

    if not tool_call_prompt and tool_list_text:
        # Use structured format for Gemini when structured_output is enabled
        provider, _ = _active_provider_cfg(cfg)  # Get provider from cfg
        if provider == Provider.GEMINI and getattr(cfg, 'structured_output', False):
            tool_call_prompt = '''
When generating tool calls, use this exact JSON format:
{
  "toolCalls": [
    {"type": "image_request", "payload": {"prompt": "detailed prompt"}},
    {"type": "phone_url", "payload": {"url": "https://..."}},
    {"type": "lore_suggestions", "payload": {"items": [{"keyword": "", "content": ""}]}}
  ]
}
For tool calls during a response, include the JSON directly. For post-message tool calls, include them in a message.'''.strip()
        else:
            tool_call_prompt = '''
When generating tool calls, use this structured JSON format:
{"toolCalls": [
  {"type": "image_request", "payload": {"prompt": "concise prompt"}},
  {"type": "phone_url", "payload": {"url": "https://..."}},
  {"type": "lore_suggestions", "payload": {"items": [{"keyword": "...", "content": "..."}]}}
]}
Include optional caption text before the JSON when appropriate.'''

    # If main template provided, use it
    main_tpl = system_prompts.get("main") if isinstance(system_prompts, dict) else None
    if main_tpl and isinstance(main_tpl, str) and main_tpl.strip():
        tpl = main_tpl
        tpl = tpl.replace("{{tool_call_prompt}}", tool_call_prompt or "")
        tpl = tpl.replace("{{user_persona}}", persona_text or "")
        tpl = tpl.replace("{{character_description}}", char_text or "")
        tpl = tpl.replace("{{tool_list}}", tool_list_text or "")
        tpl = tpl.replace("{{conversation}}", recent_text or "")
        return _truncate_to_tokens(tpl, max_tokens)

    # Otherwise keep legacy behavior + tool schema guidance
    try:
        if tool_call_prompt:
            segments.append(tool_call_prompt)
    except Exception:
        pass
    # Include user persona if present
    if user_persona and getattr(user_persona, "name", None):
        up = (
            f"User Persona: {user_persona.name}\n{getattr(user_persona, 'description', '')}"
        ).strip()
        if up:
            segments.append(up)
    if char:
        if char.system_prompt:
            segments.append(char.system_prompt)
        if char.personality:
            segments.append(f"Personality: {char.personality}")
        if char.scenario:
            segments.append(f"Scenario: {char.scenario}")
        if char.description:
            segments.append(f"Description: {char.description}")
        # Append linked lorebook contents; prefer triggered entries if any
        if char.lorebook_ids:
            lore_texts = []
            triggered_any = False
            db = SessionLocal()
            try:
                for lb_id in char.lorebook_ids:
                    lb = db.query(Lorebook).filter(Lorebook.id == lb_id).first()
                    if not lb:
                        continue
                    for entry in lb.entries:
                        include = False
                        if recent_text:
                            hay = recent_text.lower()
                            primaries = [x.lower() for x in (entry.keywords or []) if x]
                            seconds = [x.lower() for x in (entry.secondary_keywords or []) if x]
                            found_primary = [k for k in primaries if k in hay]
                            found_secondary = [k for k in seconds if k in hay]
                            logic = (entry.logic or "AND ANY").upper()
                            if logic == "AND ALL":
                                include = len(found_primary) == len(primaries) and (
                                    not seconds or len(found_secondary) == len(seconds)
                                )
                            elif logic == "NOT ANY":
                                include = len(found_primary) == 0 and len(found_secondary) == 0
                            elif logic == "NOT ALL":
                                include = not (len(found_primary) == len(primaries))
                            else:  # AND ANY default
                                include = bool(found_primary) or bool(found_secondary)
                        else:
                            include = True
                        if include:
                            keyword = entry.keywords[0] if entry.keywords else entry.title
                            lore_texts.append(f"[{keyword}] {entry.content}")
                            triggered_any = True
            finally:
                db.close()
            if lore_texts:
                title = "Triggered World Info" if triggered_any else "World Info"
                segments.append(f"{title}:\n" + "\n".join(lore_texts))
    # Include globally active lorebooks regardless of character linkage
    try:
        from .config import load_config as _lc

        _cfg = _lc()
        actives = getattr(_cfg, "active_lorebook_ids", []) or []
        if actives:
            lore_texts = []
            db = SessionLocal()
            try:
                for lb_id in actives:
                    lb = db.query(Lorebook).filter(Lorebook.id == lb_id).first()
                    if not lb:
                        continue
                    for entry in lb.entries:
                        trigger_found = False
                        if recent_text:
                            hay = recent_text.lower()
                            primaries = [x.lower() for x in (entry.keywords or []) if x]
                            logic = (entry.logic or "AND ANY").upper()
                            for term in hay.split():
                                if any(term in kw for kw in primaries):
                                    trigger_found = True
                                    break
                        else:
                            trigger_found = True
                        if trigger_found:
                            keyword = entry.keywords[0] if entry.keywords else entry.title
                            lore_texts.append(f"[{keyword}] {entry.content}")
                if lore_texts:
                    segments.append("Active Lorebooks:\n" + "\n".join(lore_texts))
            finally:
                db.close()
    except Exception:
        pass

    if not segments:
        return None
    # Append active tool descriptions if any
    try:
        from .storage import load_json as _lj
        _tools = _lj("tools.json", {"enabled": {}})
        en = (_tools.get("enabled") or {}) if isinstance(_tools, dict) else {}
        tool_lines = []
        if en.get("phone"):
            tool_lines.append("Tool: PhonePanel — You can propose opening a URL on the user's phone panel to present web content. Return a JSON field phone_url with https:// URL when appropriate.")
        if en.get("image_gen"):
            tool_lines.append("Tool: ImageGen — You can request an image from the image generator when visual output would help. Return a JSON field image_request with a concise prompt.")
        if en.get("lore_suggest"):
            tool_lines.append("Tool: LoreSuggest — You can suggest new lore entries as keyword+content for the active lorebooks. Return a JSON field lore_suggestions as an array of {keyword, content}.")
        if tool_lines:
            segments.append("\n".join(tool_lines))
    except Exception:
        pass
    return _truncate_to_tokens("\n\n".join(segments), max_tokens)


_chat_histories: Dict[str, List[Dict[str, str]]] = {}


# SQLite chat storage functions
def _create_chat_session(session_id: str, name: str = "Chat") -> None:
    """Create a new chat session in SQLite."""
    from .database import SessionLocal
    from .models import ChatSession

    db = SessionLocal()
    try:
        # Check if session already exists
        existing = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not existing:
            chat_session = ChatSession(id=session_id, name=name)
            db.add(chat_session)
            db.commit()
    except Exception as e:
        print(f"[CoolChat] Error creating chat session: {e}")
        db.rollback()
    finally:
        db.close()


def _save_chat_message(session_id: str, role: str, content: str, image_url: str = None) -> None:
    """Save a chat message to SQLite."""
    from .database import SessionLocal
    from .models import ChatSession, ChatMessage

    db = SessionLocal()
    try:
        # Ensure chat session exists
        _create_chat_session(session_id)

        # Create message
        message = ChatMessage(
            chat_id=session_id,
            role=role,
            content=content,
            image_url=image_url
        )
        db.add(message)
        db.commit()
    except Exception as e:
        print(f"[CoolChat] Error saving chat message: {e}")
        db.rollback()
    finally:
        db.close()


def _load_chat_session(session_id: str) -> List[Dict[str, str]]:
    """Load all messages for a chat session from SQLite."""
    from .database import SessionLocal
    from .models import ChatMessage

    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == session_id).order_by(ChatMessage.created_at).all()
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "image_url": msg.image_url
            } for msg in messages
        ]
    except Exception as e:
        print(f"[CoolChat] Error loading chat session: {e}")
        return []
    finally:
        db.close()


def _migrate_chat_histories_to_sqlite() -> None:
    """Migrate existing in-memory chat histories to SQLite."""
    from .database import SessionLocal

    if not _chat_histories:
        return

    # Check if migration has already been completed by looking for existing sessions in SQLite
    db = SessionLocal()
    try:
        from .models import ChatSession
        existing_sessions = db.query(ChatSession).count()
        if existing_sessions > 0:
            print(f"[CoolChat] Migration appears complete ({existing_sessions} sessions in SQLite), skipping remigration")
            return
    except Exception as e:
        print(f"[CoolChat] Error checking migration status: {e}")
    finally:
        db.close()

    print(f"[CoolChat] Migrating {_chat_histories} chat sessions to SQLite...")

    for session_id, chat_history in _chat_histories.items():
        try:
            # Create session (if not exists)
            _create_chat_session(session_id, f"Session {session_id}")

            # Save all messages
            for msg in chat_history:
                _save_chat_message(
                    session_id=session_id,
                    role=msg.get("role", "assistant"),
                    content=msg.get("content", ""),
                    image_url=msg.get("image_url")
                )

            print(f"[CoolChat] Migrated {len(chat_history)} messages for session {session_id}")

        except Exception as e:
            print(f"[CoolChat] Error migrating session {session_id}: {e}")

    # Clear in-memory histories to prevent dual writes
    _chat_histories.clear()


def _migrate_to_sqlite() -> None:
    """Migrate characters, lorebooks, and memory from JSON files to SQLite database."""

    # Check if migration has already been completed
    db = SessionLocal()
    try:
        from .models import Character as CharModel
        existing_characters = db.query(CharModel).count()
        if existing_characters > 0:
            print(f"[CoolChat] Migration appears complete ({existing_characters} characters in SQLite), skipping")
            return
    finally:
        db.close()

    print("[CoolChat] Migrating data from JSON to SQLite...")

    # Load JSON data
    char_data = load_json("characters.json", {"next_id": 1, "items": []})
    memory_data = load_json("memory.json", {"next_id": 1, "items": []})

    db = SessionLocal()
    try:
        # Migrate characters
        if char_data.get("items"):
            from .models import Character
            print(f"[CoolChat] Migrating {len(char_data['items'])} characters...")
            for char_item in char_data["items"]:
                try:
                    char = Character(**char_item)
                    db.add(char)
                except Exception as e:
                    print(f"[CoolChat] Skipping invalid character: {e}")

        # Migrate memory entries
        if memory_data.get("items"):
            from .models import MemoryEntry
            print(f"[CoolChat] Migrating {len(memory_data['items'])} memory entries...")
            for mem_item in memory_data["items"]:
                try:
                    mem = MemoryEntry(**mem_item)
                    db.add(mem)
                except Exception as e:
                    print(f"[CoolChat] Skipping invalid memory entry: {e}")

        # Migrate lorebooks and entries
        _migrate_lorebooks_to_sqlite(db)

        # Commit all migrations
        db.commit()
        print("[CoolChat] Migration completed successfully!")

    except Exception as e:
        print(f"[CoolChat] Migration error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _migrate_lorebooks_to_sqlite(db) -> None:
    """Migrate lorebooks and entries from JSON to SQLite."""

    # Load lorebook data
    lb_data = load_json("lorebooks.json", {"next_id": 1, "items": []})
    lore_data = load_json("lore.json", {"next_id": 1, "items": []})

    if not lb_data.get("items") and not lore_data.get("items"):
        return

    from .models import Lorebook as LorebookModel, LoreEntry

    # Build mappings for lore entries
    lore_by_id = {}
    for lore_item in lore_data.get("items", []):
        try:
            entry_id = lore_item.get("id")
            # Handle migration from old keyword format
            if "keyword" in lore_item and "keywords" not in lore_item:
                lore_item["keywords"] = [lore_item["keyword"]] if lore_item["keyword"] else []
                lore_item["title"] = lore_item["keyword"]
            lore_by_id[entry_id] = lore_item
        except Exception as e:
            print(f"[CoolChat] Skipping invalid lore entry {entry_id}: {e}")

    # Migrate lorebooks
    print(f"[CoolChat] Migrating {len(lb_data['items'])} lorebooks...")
    for lb_item in lb_data["items"]:
        try:
            # Clean up old format (remove entry_ids since they don't belong in Lorebook model)
            lb_clean = {k: v for k, v in lb_item.items() if k != 'entry_ids'}
            lb = LorebookModel(**lb_clean)
            db.add(lb)

            # Add entries for this lorebook
            entry_ids = lb_item.get("entry_ids", [])
            for entry_id in entry_ids:
                if entry_id in lore_by_id:
                    entry_data = lore_by_id[entry_id]
                    entry_data["lorebook_id"] = lb.id
                    try:
                        entry = LoreEntry(**entry_data)
                        db.add(entry)
                    except Exception as e:
                        print(f"[CoolChat] Skipping invalid entry for lorebook: {e}")
        except Exception as e:
            print(f"[CoolChat] Skipping invalid lorebook: {e}")

    print(f"[CoolChat] Migrated {len(lore_by_id)} lore entries")


def _trim_history(session_id: str, cfg: AppConfig) -> None:
    """Trim chat history to stay within token budget in SQLite."""
    from .database import SessionLocal
    from .models import ChatMessage

    # Get recent messages count for trimming
    budget = max(512, getattr(cfg, "max_context_tokens", 2048))

    db = SessionLocal()
    try:
        # Get all messages for this session
        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == session_id).order_by(ChatMessage.created_at).all()

        if len(messages) <= 20:  # Keep at least last 20 messages
            return

        # Calculate token usage from recent messages
        total = sum(_estimate_tokens(m.content or "") for m in messages[len(messages)-20:])
        k = len(messages)

        # Remove oldest messages if over budget
        while messages and total > budget * 2 and k > 20:
            removed = messages.pop(0)
            total -= _estimate_tokens(removed.content or "")
            db.delete(removed)
            k -= 1

        if messages:
            db.commit()
            print(f"[CoolChat] Trimmed chat {session_id} to {k} messages")

    except Exception as e:
        print(f"[CoolChat] Error trimming history for {session_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _inject_persona(user_message: str, char: Optional[Character]) -> str:
    # For echo provider, we just keep original. For others, the system is built separately in _llm_reply.
    return user_message


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------


class ProviderConfigMasked(BaseModel):
    api_key_masked: str | None = None
    api_base: str | None = None
    model: str | None = None
    temperature: float


class ConfigResponse(BaseModel):
    active_provider: str
    active_character_id: int | None = None
    providers: Dict[str, ProviderConfigMasked]
    debug: Dict[str, bool]
    user_persona: Dict[str, str]
    max_context_tokens: int
    structured_output: bool
    class ImagesOut(BaseModel):
        active: str
        pollinations: Dict[str, object]
        dezgo: Dict[str, object]
    images: ImagesOut
    theme: Dict[str, object] | None = None
    active_lorebook_ids: List[int] | None = None


class ProviderConfigUpdate(BaseModel):
    api_key: str | None = None
    api_base: str | None = None
    model: str | None = None
    temperature: float | None = None


class ConfigUpdate(BaseModel):
    active_provider: str | None = None
    providers: Dict[str, ProviderConfigUpdate] | None = None
    active_character_id: int | None = None
    debug: Dict[str, bool] | None = None
    user_persona: Dict[str, str] | None = None
    max_context_tokens: int | None = None
    images: Dict[str, object] | None = None
    theme: Dict[str, object] | None = None
    active_lorebook_ids: List[int] | None = None
    structured_output: bool | None = None


@app.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    cfg = load_config()
    masked: Dict[str, ProviderConfigMasked] = {}
    for key, pc in cfg.providers.items():
        masked[key] = ProviderConfigMasked(
            api_key_masked=mask_secret(pc.api_key),
            api_base=pc.api_base,
            model=pc.model,
            temperature=pc.temperature,
        )
    return ConfigResponse(
        active_provider=cfg.active_provider,
        active_character_id=cfg.active_character_id,
        providers=masked,
        debug={"log_prompts": getattr(cfg.debug, 'log_prompts', False), "log_responses": getattr(cfg.debug, 'log_responses', False)},
        user_persona={
            "name": getattr(cfg.user_persona, 'name', 'User'),
            "description": getattr(cfg.user_persona, 'description', ''),
            "personality": getattr(cfg.user_persona, 'personality', ''),
            "motivations": getattr(cfg.user_persona, 'motivations', ''),
            "tracking": getattr(cfg.user_persona, 'tracking', ''),
        },
        max_context_tokens=getattr(cfg, 'max_context_tokens', 2048),
        structured_output=getattr(cfg, 'structured_output', False),
        images=ConfigResponse.ImagesOut(
            active=getattr(cfg.images, 'active', ImageProvider.POLLINATIONS),
            pollinations={
                "api_key_masked": (mask_secret(getattr(cfg.images.pollinations, 'api_key', None)) if hasattr(cfg.images, 'pollinations') else None),
                "model": getattr(cfg.images.pollinations, 'model', None),
            },
            dezgo={
                "api_key_masked": (mask_secret(getattr(cfg.images.dezgo, 'api_key', None)) if hasattr(cfg.images, 'dezgo') else None),
                "model": getattr(cfg.images.dezgo, 'model', None),
                "lora_flux_1": getattr(cfg.images.dezgo, 'lora_flux_1', None),
                "lora_flux_2": getattr(cfg.images.dezgo, 'lora_flux_2', None),
                "lora_sd1_1": getattr(cfg.images.dezgo, 'lora_sd1_1', None),
                "lora_sd1_2": getattr(cfg.images.dezgo, 'lora_sd1_2', None),
                "lora1_strength": getattr(cfg.images.dezgo, 'lora1_strength', None),
                "lora2_strength": getattr(cfg.images.dezgo, 'lora2_strength', None),
                "transparent": getattr(cfg.images.dezgo, 'transparent', False),
                "width": getattr(cfg.images.dezgo, 'width', None),
                "height": getattr(cfg.images.dezgo, 'height', None),
                "steps": getattr(cfg.images.dezgo, 'steps', None),
                "upscale": getattr(cfg.images.dezgo, 'upscale', None),
            },
        ),
        theme=getattr(cfg, 'theme', None).model_dump() if getattr(cfg, 'theme', None) else None,
        active_lorebook_ids=getattr(cfg, 'active_lorebook_ids', []) or [],
    )


@app.put("/config", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdate) -> ConfigResponse:
    cfg = load_config()

    # Merge provider-specific overrides
    if payload.providers:
        for key, upd in payload.providers.items():
            base = cfg.providers.get(key, ProviderConfig())
            if upd.api_key is not None and upd.api_key != "":
                base.api_key = upd.api_key
            if upd.api_base is not None and upd.api_base != "":
                base.api_base = upd.api_base
            if upd.model is not None and upd.model != "":
                base.model = upd.model
            if upd.temperature is not None:
                base.temperature = upd.temperature
            # Apply sensible defaults for that provider
            if key == Provider.OPENAI:
                base.api_base = base.api_base or "https://api.openai.com/v1"
                base.model = base.model or "gpt-4o-mini"
            elif key == Provider.OPENROUTER:
                base.api_base = base.api_base or "https://openrouter.ai/api/v1"
                base.model = base.model or "openrouter/auto"
            elif key == Provider.GEMINI:
                base.api_base = base.api_base or "https://generativelanguage.googleapis.com/v1beta/openai"
                base.model = base.model or "gemini-1.5-flash"
            cfg.providers[key] = base

    # Switch active provider if requested
    if payload.active_provider is not None:
        cfg.active_provider = payload.active_provider
    if payload.active_character_id is not None:
        cfg.active_character_id = payload.active_character_id
    if payload.debug is not None:
        if not hasattr(cfg, 'debug') or cfg.debug is None:
            from .config import DebugConfig
            cfg.debug = DebugConfig()
        cfg.debug.log_prompts = bool(payload.debug.get("log_prompts", cfg.debug.log_prompts))
        cfg.debug.log_responses = bool(payload.debug.get("log_responses", cfg.debug.log_responses))
    if payload.user_persona is not None:
        if not hasattr(cfg, 'user_persona') or cfg.user_persona is None:
            from .config import UserPersona
            cfg.user_persona = UserPersona()
        up = payload.user_persona
        cfg.user_persona.name = up.get("name", cfg.user_persona.name)
        cfg.user_persona.description = up.get("description", cfg.user_persona.description)
        cfg.user_persona.personality = up.get("personality", cfg.user_persona.personality)
        cfg.user_persona.motivations = up.get("motivations", cfg.user_persona.motivations)
        cfg.user_persona.tracking = up.get("tracking", cfg.user_persona.tracking)
    if payload.max_context_tokens is not None:
        try:
            cfg.max_context_tokens = int(payload.max_context_tokens)
        except Exception:
            pass
    if getattr(payload, 'structured_output', None) is not None:
        try:
            cfg.structured_output = bool(payload.structured_output)
        except Exception:
            pass

    if payload.images is not None:
        imgs = getattr(cfg, 'images', ImagesConfig())
        active = payload.images.get("active") if isinstance(payload.images, dict) else None
        if isinstance(active, str):
            imgs.active = active
        poll = payload.images.get("pollinations") if isinstance(payload.images, dict) else None
        if isinstance(poll, dict):
            if "model" in poll:
                imgs.pollinations.model = poll.get("model")
            if "api_key" in poll:
                imgs.pollinations.api_key = poll.get("api_key")
        dez = payload.images.get("dezgo") if isinstance(payload.images, dict) else None
        if isinstance(dez, dict):
            for k in ("model","api_key","lora_flux_1","lora_flux_2","lora_sd1_1","lora_sd1_2","lora1_strength","lora2_strength"):
                if k in dez:
                    setattr(imgs.dezgo, k, dez.get(k))
            # Coerce numeric/boolean fields to correct types
            if "transparent" in dez:
                try:
                    imgs.dezgo.transparent = bool(dez.get("transparent"))
                except Exception:
                    pass
            if "upscale" in dez:
                try:
                    imgs.dezgo.upscale = bool(dez.get("upscale"))
                except Exception:
                    pass
            if "width" in dez:
                try:
                    imgs.dezgo.width = int(dez.get("width")) if dez.get("width") not in ("", None) else None
                except Exception:
                    pass
            if "height" in dez:
                try:
                    imgs.dezgo.height = int(dez.get("height")) if dez.get("height") not in ("", None) else None
                except Exception:
                    pass
            if "steps" in dez:
                try:
                    imgs.dezgo.steps = int(dez.get("steps")) if dez.get("steps") not in ("", None) else None
                except Exception:
                    pass
        cfg.images = imgs
    if payload.theme is not None:
        if not hasattr(cfg, 'theme') or cfg.theme is None:
            from .config import AppearanceConfig
            cfg.theme = AppearanceConfig()
        for k in ("primary","secondary","text1","text2","highlight","lowlight","phone_style","background_animations"):
            if k in payload.theme:
                setattr(cfg.theme, k, payload.theme[k])
    if payload.active_lorebook_ids is not None:
        try:
            cfg.active_lorebook_ids = [int(x) for x in payload.active_lorebook_ids]
        except Exception:
            cfg.active_lorebook_ids = payload.active_lorebook_ids

    try:
        save_config(cfg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

    # Update last_connection snapshot
    try:
        ap = cfg.active_provider
        pc = cfg.providers.get(ap, ProviderConfig())
        cfg.last_connection = {
            "provider": ap,
            "api_base": pc.api_base,
            "model": pc.model,
            "temperature": pc.temperature,
            "api_key": pc.api_key,
        }
        save_config(cfg)
    except Exception:
        pass

    # Return masked config
    masked: Dict[str, ProviderConfigMasked] = {}
    for key, pc in cfg.providers.items():
        masked[key] = ProviderConfigMasked(
            api_key_masked=mask_secret(pc.api_key),
            api_base=pc.api_base,
            model=pc.model,
            temperature=pc.temperature,
        )
    return ConfigResponse(
        active_provider=cfg.active_provider,
        active_character_id=cfg.active_character_id,
        providers=masked,
        debug={"log_prompts": getattr(cfg.debug, 'log_prompts', False), "log_responses": getattr(cfg.debug, 'log_responses', False)},
        user_persona={
            "name": getattr(cfg.user_persona, 'name', 'User'),
            "description": getattr(cfg.user_persona, 'description', ''),
            "personality": getattr(cfg.user_persona, 'personality', ''),
            "motivations": getattr(cfg.user_persona, 'motivations', ''),
            "tracking": getattr(cfg.user_persona, 'tracking', ''),
        },
        max_context_tokens=getattr(cfg, 'max_context_tokens', 2048),
        structured_output=getattr(cfg, 'structured_output', False),
        images=ConfigResponse.ImagesOut(
            active=getattr(cfg.images, 'active', ImageProvider.POLLINATIONS),
            pollinations={"api_key": None, "model": getattr(cfg.images.pollinations, 'model', None)},
            dezgo={
                "api_key": None,
                "model": getattr(cfg.images.dezgo, 'model', None),
                "lora_flux_1": getattr(cfg.images.dezgo, 'lora_flux_1', None),
                "lora_flux_2": getattr(cfg.images.dezgo, 'lora_flux_2', None),
                "lora_sd1_1": getattr(cfg.images.dezgo, 'lora_sd1_1', None),
                "lora_sd1_2": getattr(cfg.images.dezgo, 'lora_sd1_2', None),
                "lora1_strength": getattr(cfg.images.dezgo, 'lora1_strength', None),
                "lora2_strength": getattr(cfg.images.dezgo, 'lora2_strength', None),
                "transparent": str(getattr(cfg.images.dezgo, 'transparent', False)),
                "width": str(getattr(cfg.images.dezgo, 'width', '')),
                "height": str(getattr(cfg.images.dezgo, 'height', '')),
                "steps": str(getattr(cfg.images.dezgo, 'steps', '')),
                "upscale": str(getattr(cfg.images.dezgo, 'upscale', '')),
            },
        ),
        theme=getattr(cfg, 'theme', None).model_dump() if getattr(cfg, 'theme', None) else None,
        active_lorebook_ids=getattr(cfg, 'active_lorebook_ids', []) or [],
    )


class ThemeSuggestRequest(BaseModel):
    primary: str


class ThemeSuggestResponse(BaseModel):
    colors: List[str]


@app.post("/theme/suggest", response_model=ThemeSuggestResponse)
async def theme_suggest(payload: ThemeSuggestRequest) -> ThemeSuggestResponse:
    cfg = load_config()
    prompt = f"Given {payload.primary} please suggest 5 more colors that will provide an easily readable and pleasing UI theme. Select a secondary color that compliments the primary, Two text colors that will stand out and be readable with the primary and secondary colors as their background respectively. And include a highlight and lowlight color. Return the colors as comma separated hex codes. Do not include anything else in your reply."
    try:
        print("[CoolChat] theme_suggest provider=", cfg.active_provider)
        reply = await _llm_reply(prompt, cfg)
        print("[CoolChat] theme_suggest reply=", reply)
        text = reply.strip().strip('`')
        if text.lower().startswith('json'):
            text = text[4:].strip()
        parts = [p.strip() for p in text.split(',') if p.strip()]
        parts = parts[:5]
        if len(parts) < 5:
            raise ValueError("insufficient colors")
        return ThemeSuggestResponse(colors=parts)
    except Exception as e:
        print("[CoolChat] theme_suggest fallback due to:", e)
        # simple fallback palette based on primary: generate tints/shades
        base = payload.primary.lstrip('#')
        try:
            r = int(base[0:2], 16); g = int(base[2:4], 16); b = int(base[4:6], 16)
        except Exception:
            r, g, b = (37, 99, 235)
        def clamp(x):
            return max(0, min(255, int(x)))
        def hex3(r,g,b):
            return f"#{r:02x}{g:02x}{b:02x}"
        secondary = hex3(clamp(r*0.6), clamp(g*0.6), clamp(b*0.6))
        text1 = "#e5e7eb"
        text2 = "#cbd5e1"
        highlight = hex3(clamp(255-r*0.2), clamp(255-g*0.2), clamp(255-b*0.2))
        lowlight = "#111827"
        return ThemeSuggestResponse(colors=[secondary, text1, text2, highlight, lowlight])


@app.get("/config/raw")
async def get_config_raw():
    """Return the full config including API keys for Advanced tab."""
    cfg = load_config()
    return cfg.model_dump()


@app.post("/config/raw")
async def replace_config(raw: Dict[str, object]):
    """Replace the entire configuration with the provided JSON."""
    try:
        # Validate by constructing AppConfig
        from .config import AppConfig
        cfg = AppConfig(**raw)
        save_config(cfg)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")


@app.put("/config/active_lorebook_ids")
async def update_active_lorebook_ids(payload: Dict[str, List[int]]):
    """Update the active lorebook IDs for chat context."""
    try:
        ids = payload.get("ids", [])
        if not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="Invalid payload: ids must be a list")
        cfg = load_config()
        cfg.active_lorebook_ids = ids
        save_config(cfg)
        return {"status": "ok", "active_lorebook_ids": cfg.active_lorebook_ids}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update active lorebook IDs: {e}")


# ---------------------------------------------------------------------------
# Models endpoint (provider-aware)
# ---------------------------------------------------------------------------


class ModelsResponse(BaseModel):
    models: List[str]


@app.get("/models", response_model=ModelsResponse)
async def list_models(provider: str | None = None) -> ModelsResponse:
    cfg = load_config()
    p = provider or cfg.active_provider

    async def _err(detail):
        raise HTTPException(status_code=400, detail=detail)

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

    if p == Provider.ECHO:
        return ModelsResponse(models=[])

    if p == Provider.OPENAI:
        pc = cfg.providers.get(p, ProviderConfig())
        if not pc.api_key:
            await _err("Missing API key for openai")
        base = (pc.api_base or "https://api.openai.com/v1").rstrip("/")
        url = base + "/models"
        headers = {"Authorization": f"Bearer {pc.api_key}"}
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
        pc = cfg.providers.get(p, ProviderConfig())
        if pc.api_key:
            headers["Authorization"] = f"Bearer {pc.api_key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=502, detail=detail)
        data = resp.json()
        items = data.get("data", [])
        def is_free(it):
            pricing = it.get("pricing") or {}
            # Heuristic: free if prompt/completion cost is 0
            for k in ("prompt", "completion"):
                v = pricing.get(k)
                if v in (None, "0", 0, "0.0", 0.0):
                    continue
                return False
            return True
        # sort: free first, then name
        items.sort(key=lambda it: (0 if is_free(it) else 1, (it.get("id") or it.get("name") or "z")))
        ids = []
        for item in items:
            mid = item.get("id") or item.get("name")
            if mid:
                ids.append(mid)
        return ModelsResponse(models=ids)

    if p == Provider.GEMINI:
        pc = cfg.providers.get(p, ProviderConfig())
        if not pc.api_key:
            await _err("Missing API key for gemini")
        base = (pc.api_base or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        url = base + "/models"
        headers = {"Authorization": f"Bearer {pc.api_key}"}
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


# ---------------------------------------------------------------------------
# Character import (JSON via multipart or direct JSON)
# ---------------------------------------------------------------------------

from fastapi import UploadFile, File, Form


@app.post("/characters/import", response_model=Character, status_code=201)
async def import_character(
    file: UploadFile | None = File(default=None),
    name: str | None = Form(default=None),
    description: str | None = Form(default=""),
    avatar_url: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    # If a file was provided, detect PNG or JSON
    data = None
    if file is not None:
        raw = await file.read()
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            try:
                data = _parse_png_card(raw)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid PNG card: {e}")
            # Save the PNG to public folder and set avatar_url
            try:
                import os as _os
                static_chars = _os.path.join(_os.path.dirname(__file__), "..", "public", "characters")
                _os.makedirs(static_chars, exist_ok=True)
                fname = f"{int(time.time()*1000)}.png"
                fpath = _os.path.join(static_chars, fname)
                with open(fpath, "wb") as fh:
                    fh.write(raw)
                data["avatar_url"] = f"/public/characters/{fname}"
            except Exception:
                pass
        else:
            try:
                import json as _json
                data = _json.loads(raw.decode("utf-8"))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid import file: {e}")
    else:
        data = {"name": name, "description": description or "", "avatar_url": avatar_url}

    if not data or not data.get("name"):
        raise HTTPException(status_code=400, detail="Missing required field 'name'")

    payload = CharacterCreate(
        name=data.get("name"),
        description=data.get("description", ""),
        avatar_url=data.get("avatar_url"),
        first_message=data.get("first_message") or data.get("first_mes"),
        alternate_greetings=data.get("alternate_greetings") or [],
        scenario=data.get("scenario"),
        system_prompt=data.get("system_prompt"),
        personality=data.get("personality"),
        mes_example=data.get("mes_example"),
        creator_notes=data.get("creator_notes"),
        tags=data.get("tags") or [],
        post_history_instructions=data.get("post_history_instructions"),
        extensions=data.get("extensions"),
        lorebook_ids=data.get("lorebook_ids") or [],
    )
    # Reuse create_character logic
    return await create_character(payload, db)


def _parse_png_card(raw: bytes) -> Dict[str, object]:
    import struct, json, base64
    pos = 8  # after signature
    found = {}
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos:pos+4])[0]; pos += 4
        ctype = raw[pos:pos+4]; pos += 4
        data = raw[pos:pos+length]; pos += length
        crc = raw[pos:pos+4]; pos += 4  # noqa
        if ctype == b"tEXt":
            # keyword\x00text
            try:
                nul = data.index(b"\x00")
                key = data[:nul].decode("latin1")
                text = data[nul+1:].decode("utf-8", errors="ignore")
            except Exception:
                continue
            if key in ("chara_card_v2", "chara"):
                found[key] = text
        elif ctype == b"iTXt":
            # keyword\x00comp_flag\x00comp_method\x00lang\x00translated\x00text
            try:
                parts = data.split(b"\x00", 5)
                key = parts[0].decode("latin1")
                comp_flag = parts[1][:1] if len(parts) > 1 else b"\x00"
                # parts[2]=comp_method, parts[3]=lang, parts[4]=translated
                text = parts[5] if len(parts) > 5 else b""
                if comp_flag == b"\x01":
                    import zlib
                    text = zlib.decompress(text)
                text = text.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if key in ("chara_card_v2", "chara"):
                found[key] = text
        if ctype == b"IEND":
            break
    # Prefer v2 JSON
    if "chara_card_v2" in found:
        try:
            return json.loads(found["chara_card_v2"])  # type: ignore
        except Exception as e:
            raise ValueError(f"bad chara_card_v2 JSON: {e}")
    if "chara" in found:
        # Usually base64 JSON
        try:
            decoded = base64.b64decode(found["chara"])  # type: ignore
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"bad chara base64: {e}")
    raise ValueError("No character JSON found in PNG")


class SuggestRequest(BaseModel):
    field: str
    character: Dict[str, object] | None = None  # current draft fields


class SuggestResponse(BaseModel):
    value: str


@app.post("/characters/suggest_field", response_model=SuggestResponse)
async def suggest_field(payload: SuggestRequest) -> SuggestResponse:
    cfg = load_config()
    char = payload.character or {}
    name = str(char.get("name")) if char.get("name") else "Character"
    field = payload.field
    # Build context: include filled fields except the one being suggested
    ctx_lines = []
    for k, v in char.items():
        if k == field:
            continue
        if v is None:
            continue
        ctx_lines.append(f"- {k}: {v}")
    ctx = "\n".join(ctx_lines)
    prompt = (
        f"You are an AI Character Card creator helper. We are creating a new character named {name}. "
        f"You need to fill in the {field} field. The following fields have been filled out already; use them for context if helpful. "
        f"Reply with a single JSON string with your content, no additional text.\n\n"
        f"Filled fields:\n{ctx}\n\n"
    )
    # Replace tokens
    if hasattr(cfg, 'user_persona') and cfg.user_persona:
        uname = cfg.user_persona.name or "User"
    else:
        uname = "User"
    cname = name
    prompt = prompt.replace("{{char}}", cname).replace("{{user}}", uname)

    # Call LLM
    reply = await _llm_reply(prompt, cfg)
    # Extract a JSON string; accept plain string or quoted JSON; strip code fences
    value = reply.strip()
    # Remove code fences
    if value.startswith("```"):
        value = value.strip('`')
        # Sometimes starts with json\n
        if value.lower().startswith("json\n"):
            value = value[5:]
    # Try parse JSON
    try:
        import json as _json
        j = _json.loads(value)
        if isinstance(j, str):
            value = j
        elif isinstance(j, dict) and 'text' in j and isinstance(j['text'], str):
            value = j['text']
    except Exception:
        # If surrounded by quotes, strip them
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
    return SuggestResponse(value=value)


@app.post("/characters/upload_avatar")
async def upload_avatar(file: UploadFile = File(...)) -> Dict[str, str]:
    data = await file.read()
    import os as _os, time as _time
    ext = ".png"
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
    characters_dir = _os.path.join(_os.path.dirname(__file__), "..", "public", "characters")
    _os.makedirs(characters_dir, exist_ok=True)
    fname = f"gen_{int(_time.time()*1000)}{ext}"
    fpath = _os.path.join(characters_dir, fname)
    with open(fpath, "wb") as fh:
        fh.write(data)
    return {"avatar_url": f"/public/characters/{fname}"}


class GenerateAvatarRequest(BaseModel):
    character: Dict[str, object] | None = None


@app.post("/characters/generate_avatar")
async def generate_avatar(payload: GenerateAvatarRequest) -> Dict[str, str]:
    cfg = load_config()
    char = payload.character or {}
    name = str(char.get("name") or "Character")
    # Compose prompt to LLM for a portrait description
    context_lines = []
    for k in ("description", "personality", "scenario", "system_prompt", "creator_notes", "tags"):
        v = char.get(k)
        if v:
            context_lines.append(f"- {k}: {v}")
    context = "\n".join(context_lines)
    llm_prompt = (
        f"You are an AI visual prompt engineer. Create a concise PORTRAIT description for character '{name}'. "
        f"Focus on face, upper body, clothing, mood, lighting, and style. Avoid names or extra chatter. "
        f"Return a single JSON string with the prompt only.\n\nContext:\n{context}"
    )
    desc = await _llm_reply(llm_prompt, cfg)
    # sanitize
    try:
        import json as _json
        j = _json.loads(desc)
        if isinstance(j, str):
            desc = j
    except Exception:
        pass
    # Fetch image from Pollinations
    import httpx as _httpx, urllib.parse as _urlp, os as _os, time as _time
    url = f"https://image.pollinations.ai/prompt/{_urlp.quote(desc)}"
    # Debug output: print full Pollinations URL when prompt logging is enabled
    if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_prompts', False):
        print("[CoolChat] Pollinations URL:", url)
    timeout = _httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
    async with _httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Pollinations image fetch failed")
        img = r.content
    characters_dir = _os.path.join(_os.path.dirname(__file__), "..", "public", "characters")
    _os.makedirs(characters_dir, exist_ok=True)
    fname = f"gen_{int(_time.time()*1000)}.png"
    fpath = _os.path.join(characters_dir, fname)
    with open(fpath, "wb") as fh:
        fh.write(img)
    return {"avatar_url": f"/public/characters/{fname}", "prompt": desc}


# ---------------------------------------------------------------------------
# Images: configuration and generation from chat
# ---------------------------------------------------------------------------


class ImageModelsResponse(BaseModel):
    models: List[str]


@app.get("/image/models", response_model=ImageModelsResponse)
async def image_models(provider: str | None = None) -> ImageModelsResponse:
    p = (provider or ImageProvider.POLLINATIONS).lower()
    if p == ImageProvider.POLLINATIONS:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                r = await client.get("https://image.pollinations.ai/models")
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        models = []
                        for it in data:
                            mid = it.get("id") or it.get("name") if isinstance(it, dict) else it
                            if mid:
                                models.append(mid)
                        if models:
                            return ImageModelsResponse(models=models)
        except Exception as e:
            print("[CoolChat] pollinations models fetch failed:", e)
        # fallback
        return ImageModelsResponse(models=["flux/dev", "sdxl", "stable-diffusion-2-1", "playground-v2.5"])
    if p == ImageProvider.DEZGO:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
                r = await client.get("https://api.dezgo.com/info")
                if r.status_code == 200:
                    info = r.json()
                    items = info.get("models") if isinstance(info, dict) else None
                    models = []
                    if isinstance(items, list):
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            # Only include models that support any text2image family
                            funcs = [f.lower() for f in (it.get("functions") or []) if isinstance(f, str)]
                            if not any("text2image" in f for f in funcs):
                                continue
                            mid = it.get("id")
                            family = (it.get("family") or "zzz").lower()
                            if mid:
                                models.append((family, mid))
                    if models:
                        # Sort by family then id for stable order
                        models.sort(key=lambda x: (x[0], x[1]))
                        return ImageModelsResponse(models=[m[1] for m in models])
        except Exception as e:
            print("[CoolChat] dezgo models fetch failed:", e)
        # fallback minimal list (ids) by family order
        return ImageModelsResponse(models=["flux_1_dev", "sdxl_lightning_1_0", "stablediffusion_1_5"]) 
    return ImageModelsResponse(models=[])


# ---------------------------------------------------------------------------
# Chats: list and load histories
# ---------------------------------------------------------------------------


class ChatListResponse(BaseModel):
    sessions: List[str]


@app.get("/chats", response_model=ChatListResponse)
async def list_chats() -> ChatListResponse:
    """List all chat sessions from SQLite."""
    from .database import SessionLocal
    from .models import ChatSession

    db = SessionLocal()
    try:
        sessions = db.query(ChatSession).all()
        session_ids = [s.id for s in sessions]
        return ChatListResponse(sessions=session_ids)
    except Exception as e:
        print(f"[CoolChat] Error listing chats: {e}")
        return ChatListResponse(sessions=[])
    finally:
        db.close()


class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, Union[str, None]]]


@app.get("/chats/{session_id}", response_model=ChatHistoryResponse)
async def get_chat(session_id: str) -> ChatHistoryResponse:
    """Return all messages for a chat session from SQLite."""
    messages = _load_chat_session(session_id)
    return ChatHistoryResponse(messages=messages)


@app.post("/chats/{session_id}/reset")
async def reset_chat(session_id: str) -> Dict[str, str]:
    """Delete all messages for a chat session (keep the session)."""
    from .database import SessionLocal
    from .models import ChatMessage

    db = SessionLocal()
    try:
        db.query(ChatMessage).filter(ChatMessage.chat_id == session_id).delete()
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        print(f"[CoolChat] Error resetting chat {session_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting chat: {e}")
    finally:
        db.close()


@app.get("/chats/{session_id}/export/jsonl")
async def export_chat_jsonl(session_id: str):
    """Export chat history as SillyTavern-compatible JSONL file."""
    hist = _load_chat_session(session_id)
    if not hist:
        raise HTTPException(status_code=404, detail="Chat session not found or empty")

    # Try to get active character for the export
    cfg = load_config()
    char_name = ""
    if getattr(cfg, 'active_character_id', None):
        char_obj = _get_character(cfg.active_character_id)
        if char_obj:
            char_name = char_obj.name
    if not char_name:
        char_name = "Character"

    # Generate chat metadata
    from datetime import datetime
    create_date = datetime.now().strftime("%Y-%m-%d@%Hh%Mm%Ss")

    def generate():
        import io
        output = io.StringIO()

        # First line: Metadata
        metadata = {
            "user_name": "User",  # Default, could be from config
            "character_name": char_name,
            "create_date": create_date,
            "chat_metadata": {
                "integrity": "00000000-0000-0000-0000-000000000000",  # Placeholder
                "chat_id_hash": hash(session_id) % 2**63,
                "objective": None,
                "variables": {},
                "note_prompt": "",
                "note_interval": 1,
                "note_position": 1,
                "note_depth": 4,
                "note_role": 0,
                "timedWorldInfo": {"sticky": {}, "cooldown": {}},
                "tainted": False,
                "attachments": [],
                "lastInContextMessageId": len(hist)
            }
        }
        output.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        # Message lines
        current_time = datetime.now()
        for i, msg in enumerate(hist):
            role = msg.get("role", "assistant").lower()
            content = msg.get("content", "")
            image_url = msg.get("image_url")

            if role == "assistant":
                name = char_name
                is_user = False
                is_system = True if i == 0 else False  # First system message
            else:
                name = "User"  # Could be from config
                is_user = True
                is_system = False

            send_date = (current_time - timedelta(seconds=len(hist) - i)).strftime("%B %d, %Y %I:%M%p")

            entry = {
                "name": name,
                "is_user": is_user,
                "is_system": is_system,
                "send_date": send_date,
                "mes": content,
                "extra": {
                    "isSmallSys": is_system and len(content) < 100,
                    "token_count": len(content) // 4,  # Rough estimate
                    "reasoning": "",
                    "qvink_memory": {"lagging": False, "include": None}
                },
                "tracker": {},
                "title": "",
                "gen_started": "",  # Empty for now
                "gen_finished": "",
                "swipe_id": 0,
                "swipes": [content],
                "swipe_info": []
            }

            if image_url:
                entry["extra"]["image"] = image_url
                entry["extra"]["generationType"] = 6  # Image type
                entry["extra"]["negative"] = ""
                entry["extra"]["inline_image"] = False
                entry["extra"]["image_swipes"] = [image_url]

            if not is_user and not is_system:
                entry["force_avatar"] = "/thumbnail?type=persona&file=user-default.png"

            output.write(json.dumps(entry, ensure_ascii=False) + "\n")

        output.seek(0)
        yield output.getvalue()
        output.close()

    fname = f"{session_id} - {create_date}.jsonl"
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )


# ---------------------------------------------------------------------------
# Tools / MCP registry (storage only for now)
# ---------------------------------------------------------------------------


@app.get("/tools/mcp")
async def list_mcp_servers():
    data = load_json("mcp.json", {"servers": []})
    return data


@app.post("/tools/mcp")
async def save_mcp_servers(payload: Dict[str, object]):
    if not isinstance(payload, dict) or "servers" not in payload or not isinstance(payload["servers"], list):
        raise HTTPException(status_code=400, detail="invalid payload")
    save_json("mcp.json", {"servers": payload["servers"]})
    return {"status": "ok"}


@app.get("/tools/mcp/awesome")
async def list_mcp_awesome():
    """Fetch and parse the Awesome MCP Servers list into a lightweight catalog.

    Returns: { items: [{ name, url, description }] }
    """
    import httpx
    import re
    url = "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/refs/heads/main/README.md"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=30.0)) as client:
            r = await client.get(url)
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch awesome list")
            md = r.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    items = []
    # Parse lines like: - [Name](https://link) - description
    for line in md.splitlines():
        m = re.match(r"^\s*[-*]\s*\[(.+?)\]\((https?://[^\)]+)\)\s*-\s*(.+)$", line.strip())
        if m:
            name, link, desc = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            items.append({"name": name, "url": link, "description": desc})
    return {"items": items}


# Store tool enablement (public/tools.json)
@app.get("/tools/settings")
async def get_tool_settings(character_id: int | None = None):
    data = load_json("tools.json", {"enabled": {"phone": False, "image_gen": False, "lore_suggest": False}, "per_character": {}})
    if character_id is not None:
        en = (data.get("per_character", {}).get(str(character_id)) if isinstance(data.get("per_character"), dict) else None)
        if isinstance(en, dict):
            return {"enabled": en}
    return {"enabled": data.get("enabled", {})}


@app.post("/tools/settings")
async def save_tool_settings(payload: Dict[str, object], character_id: int | None = None):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")
    en = payload.get("enabled") if isinstance(payload.get("enabled"), dict) else None
    if en is None:
        raise HTTPException(status_code=400, detail="missing enabled map")
    data = load_json("tools.json", {"enabled": {"phone": False, "image_gen": False, "lore_suggest": False}, "per_character": {}})
    if character_id is not None:
        data.setdefault("per_character", {})
        data["per_character"][str(character_id)] = en
    else:
        data["enabled"] = en
    save_json("tools.json", data)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Lore suggestion from chat
# ---------------------------------------------------------------------------


class LoreSuggestResponse(BaseModel):
    suggestions: List[Dict[str, str]]  # [{ keyword, content }]


@app.post("/lore/suggest_from_chat", response_model=LoreSuggestResponse)
async def lore_suggest_from_chat(payload: Dict[str, str] | None = None) -> LoreSuggestResponse:
    cfg = load_config()
    sid = None
    if isinstance(payload, dict):
        sid = payload.get("session_id")
    sid = sid or "default"
    # Prepare context from chat
    hist = _load_chat_session(sid)
    convo = "\n".join([f"{m['role']}: {m.get('content','')}" for m in hist][-20:])
    # Collect existing keywords from active lorebooks
    existing = set()
    active_ids = (getattr(cfg, 'active_lorebook_ids', []) or [])
    db = SessionLocal()
    try:
        for lb_id in active_ids:
            lb = db.query(Lorebook).filter(Lorebook.id == lb_id).first()
            if not lb:
                continue
            for entry in lb.entries:
                if entry.keyword:
                    existing.add(entry.keyword.strip().lower())
                for k in (entry.keywords or []):
                    if k:
                        existing.add(k.strip().lower())
    finally:
        db.close()
    # Build prompt
    prompt = (
        "You are a World Info assistant. Based on the conversation below, "
        "suggest 3-6 lore entries (keyword + one-paragraph content) that would help future replies. "
        "Avoid duplicates of existing keywords. Output JSON with an array under key 'suggestions', "
        "each item like {\"keyword\": string, \"content\": string}. Keep keywords concise.\n\n"
        f"Existing keywords (lowercase): {sorted(existing)}\n\n"
        f"Conversation:\n{convo}\n"
    )
    try:
        raw = await _llm_reply(prompt, cfg)
        import json as _json, re as _re
        txt = raw.strip()
        # Strip Markdown fences if present
        if txt.startswith("```"):
            # remove first line ```json or ``` and trailing ```
            if "\n" in txt:
                txt = txt.split("\n", 1)[1]
            if txt.endswith("```"):
                txt = txt[:-3]
            txt = txt.strip()
        # Try parse object or array
        data = None
        try:
            data = _json.loads(txt)
        except Exception:
            # Extract first JSON object in text as fallback
            m = _re.search(r"\{[\s\S]*\}", txt)
            if m:
                data = _json.loads(m.group(0))
        if data is None:
            # If the model returned a bare array, wrap it
            try:
                arr = _json.loads(txt)
                if isinstance(arr, list):
                    data = {"suggestions": arr}
            except Exception:
                pass
        if data is None:
            raise ValueError("Could not parse suggestions JSON")
        out = []
        for it in data.get("suggestions", []) or []:
            if not isinstance(it, dict):
                continue
            kw = (it.get("keyword") or "").strip()
            ct = (it.get("content") or "").strip()
            if not kw or not ct:
                continue
            if kw.lower() in existing:
                continue
            out.append({"keyword": kw, "content": ct})
        return LoreSuggestResponse(suggestions=out)
    except Exception as e:
        # Fallback: no suggestions
        print("[CoolChat] lore suggest error:", e)
        return LoreSuggestResponse(suggestions=[])


class GenerateFromChatRequest(BaseModel):
    session_id: str | None = None


class GenerateFromChatResponse(BaseModel):
    image_url: str
    prompt: str


@app.post("/images/generate_from_chat", response_model=GenerateFromChatResponse)
async def generate_from_chat(payload: GenerateFromChatRequest) -> GenerateFromChatResponse:
    cfg = load_config()
    sid = payload.session_id or "default"
    hist = _load_chat_session(sid)
    convo = "\n".join([f"{m['role']}: {m['content']}" for m in hist][-10:])
    # Ask LLM for a one-line scene prompt
    # Scene summary prompt (user-editable system prompt)
    try:
        from .storage import load_json as _lj
        _p = _lj("prompts.json", {})
        sys_p = (_p.get("system", {}) or {}).get("image_summary") if isinstance(_p, dict) else None
    except Exception:
        sys_p = None
    if not sys_p:
        sys_p = (
            "Summarize the current scene for an image in a single concise line suitable as a text-to-image prompt. "
            "Focus on salient visual elements and avoid names, extra quotes, or brackets.\n\nConversation:\n{{conversation}}"
        )
    scene_req = sys_p.replace("{{conversation}}", convo)
    desc = await _llm_reply(scene_req, cfg, recent_text=None, disable_system=True)
    # Clean JSON-string replies
    try:
        import json as _json
        parsed = _json.loads(desc)
        if isinstance(parsed, str):
            desc = parsed
    except Exception:
        pass
    # Character-specific prepend/append
    char = _get_character(cfg.active_character_id) if getattr(cfg, 'active_character_id', None) else None
    prefix = getattr(char, 'image_prompt_prefix', None) or ""
    suffix = getattr(char, 'image_prompt_suffix', None) or ""
    final_prompt = (prefix + " " + desc + " " + suffix).strip()

    # Dispatch to configured image backend
    img_cfg: ImagesConfig = getattr(cfg, 'images', ImagesConfig())
    active = getattr(img_cfg, 'active', ImageProvider.POLLINATIONS)
    url = None
    if active == ImageProvider.POLLINATIONS:
        import httpx as _httpx, urllib.parse as _urlp, os as _os, time as _time
        model = getattr(img_cfg.pollinations, 'model', None)
        poll_url = f"https://image.pollinations.ai/prompt/{_urlp.quote(final_prompt)}"
        if model:
            poll_url += f"?model={_urlp.quote(model)}"
        print("[CoolChat] Pollinations URL:", poll_url)
        timeout = _httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with _httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(poll_url)
            print("[CoolChat] Pollinations status=", r.status_code)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail="Pollinations image fetch failed")
            img = r.content
        images_root = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_root, exist_ok=True)
        # Save under character folder
        try:
            cname = char.name if char else "default"
        except Exception:
            cname = "default"
        try:
            from pathlib import Path as _Path
            cdir = _Path(images_root) / (_safe_name(cname))
            cdir.mkdir(parents=True, exist_ok=True)
            images_dir = str(cdir)
        except Exception:
            images_dir = images_root
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        sub = images_dir.replace(images_root, "").strip("/\\")
        url = f"/public/images/{(sub + '/' if sub else '')}{fname}"
        # Append to chat history for persistence
        try:
            _save_chat_message(sid, "assistant", final_prompt, image_url)
        except Exception:
            pass
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    elif active == ImageProvider.DEZGO:
        import httpx as _httpx, os as _os, time as _time
        key = getattr(img_cfg.dezgo, 'api_key', None)
        if not key:
            raise HTTPException(status_code=400, detail="Missing Dezgo API key")
        model = (getattr(img_cfg.dezgo, 'model', None) or '').strip()

        # Determine the correct endpoint based on model
        endpoint = "text2image"  # SD1 default
        mlow = model.lower()
        if "flux" in mlow:
            endpoint = "text2image_flux"
        elif "lightning" in mlow:
            endpoint = "text2image_sdxl_lightning"
        elif "sdxl" in mlow or " xl" in f" {mlow}" or "realistic" in mlow:
            # Heuristic for SDXL models (e.g., realistic-vision-v5)
            endpoint = "text2image_sdxl"

        form = {"prompt": final_prompt, "format": "png"}
        if model:
            form["model"] = model

        # Attach LORAs according to family
        if endpoint == "text2image_flux":
            for kconf, kapi in (("lora_flux_1", "lora1"), ("lora_flux_2", "lora2")):
                v = getattr(img_cfg.dezgo, kconf, None)
                if v:
                    form[kapi] = v
        elif endpoint == "text2image":
            for kconf, kapi in (("lora_sd1_1", "lora1"), ("lora_sd1_2", "lora2")):
                v = getattr(img_cfg.dezgo, kconf, None)
                if v:
                    form[kapi] = v
        # LoRA strengths if provided
        s1 = getattr(img_cfg.dezgo, 'lora1_strength', None)
        s2 = getattr(img_cfg.dezgo, 'lora2_strength', None)
        if s1 is not None:
            form["lora1_strength"] = str(s1)
        if s2 is not None:
            form["lora2_strength"] = str(s2)
        # Common options: width/height; steps only where supported
        w = getattr(img_cfg.dezgo, 'width', None)
        h = getattr(img_cfg.dezgo, 'height', None)
        if w:
            form["width"] = str(w)
        if h:
            form["height"] = str(h)
        st = getattr(img_cfg.dezgo, 'steps', None)
        if endpoint in ("text2image", "text2image_flux", "text2image_sdxl") and st:
            form["steps"] = str(st)
        # Transparent background supported for Flux/SDXL families; Upscale is SD1-only
        if endpoint != "text2image":
            if getattr(img_cfg.dezgo, 'transparent', False):
                form["transparent_background"] = "true"
        else:
            if getattr(img_cfg.dezgo, 'upscale', None):
                form["upscale"] = "true"

        # Dezgo expects the API key in the X-Dezgo-Key header
        headers = {"X-Dezgo-Key": key}
        print("[CoolChat] Dezgo endpoint=", endpoint)
        print("[CoolChat] Dezgo headers= X-Dezgo-Key length:", len(key) if key else 0)
        print("[CoolChat] Dezgo body=", form)
        # Emit a debug-friendly, curl-like summary for troubleshooting
        try:
            safe_key = mask_secret(key)
            curl = [
                "curl -X POST",
                f"'https://api.dezgo.com/{endpoint}'",
                "-H 'accept: */*'",
                f"-H 'X-Dezgo-Key: {safe_key}'",
                "-H 'Content-Type: multipart/form-data'",
            ]
            for k, v in form.items():
                curl.append(f"-F '{k}={v}'")
            print("[CoolChat] Dezgo curl:", " ".join(curl))
        except Exception:
            pass
        # Force multipart/form-data per Dezgo examples
        multipart = {k: (None, v) for k, v in form.items()}
        async with _httpx.AsyncClient(timeout=_httpx.Timeout(10.0, read=60.0)) as client:
            # Build request to inspect headers too
            req = client.build_request("POST", f"https://api.dezgo.com/{endpoint}", files=multipart, headers=headers)
            # Log content-type with boundary for debugging
            try:
                print("[CoolChat] Dezgo Content-Type:", req.headers.get("Content-Type"))
            except Exception:
                pass
            r = await client.send(req)
            print("[CoolChat] Dezgo status=", r.status_code)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Dezgo error: {r.text}")
            img = r.content
        images_root = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_root, exist_ok=True)
        try:
            cname = char.name if char else "default"
        except Exception:
            cname = "default"
        try:
            from pathlib import Path as _Path
            cdir = _Path(images_root) / (_safe_name(cname))
            cdir.mkdir(parents=True, exist_ok=True)
            images_dir = str(cdir)
        except Exception:
            images_dir = images_root
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        sub = images_dir.replace(images_root, "").strip("/\\")
        url = f"/public/images/{(sub + '/' if sub else '')}{fname}"
        try:
            _save_chat_message(sid, "assistant", final_prompt, image_url)
        except Exception:
            pass
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported image provider: {active}")


# Direct image generation with explicit prompt
class GenerateImageRequest(BaseModel):
    prompt: str
    session_id: str | None = None


@app.post("/images/generate", response_model=GenerateFromChatResponse)
async def generate_image(payload: GenerateImageRequest) -> GenerateFromChatResponse:
    cfg = load_config()
    final_prompt = payload.prompt.strip()
    char = _get_character(cfg.active_character_id) if getattr(cfg, 'active_character_id', None) else None
    # Reuse provider dispatch from generate_from_chat
    class _P(BaseModel):
        session_id: str | None = None
    dummy = _P(session_id=payload.session_id)
    # Hack: call generate_from_chat-like flow but bypass LLM summary; duplicate minimal dispatch
    img_cfg: ImagesConfig = getattr(cfg, 'images', ImagesConfig())
    active = getattr(img_cfg, 'active', ImageProvider.POLLINATIONS)
    if active == ImageProvider.POLLINATIONS:
        import httpx as _httpx, urllib.parse as _urlp, os as _os, time as _time
        poll_url = f"https://image.pollinations.ai/prompt/{_urlp.quote(final_prompt)}"
        timeout = _httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with _httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(poll_url)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail="Pollinations image fetch failed")
            img = r.content
        images_root = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_root, exist_ok=True)
        try:
            cname = char.name if char else "default"
        except Exception:
            cname = "default"
        from pathlib import Path as _Path
        cdir = _Path(images_root) / (_safe_name(cname))
        cdir.mkdir(parents=True, exist_ok=True)
        images_dir = str(cdir)
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        sub = images_dir.replace(images_root, "").strip("/\\")
        url = f"/public/images/{(sub + '/' if sub else '')}{fname}"
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    elif active == ImageProvider.DEZGO:
        # Reuse Dezgo branch with provided final_prompt
        import httpx as _httpx, os as _os, time as _time
        key = getattr(img_cfg.dezgo, 'api_key', None)
        if not key:
            raise HTTPException(status_code=400, detail="Missing Dezgo API key")
        model = (getattr(img_cfg.dezgo, 'model', None) or '').strip()
        endpoint = "text2image"
        mlow = model.lower()
        if "flux" in mlow:
            endpoint = "text2image_flux"
        elif "lightning" in mlow:
            endpoint = "text2image_sdxl_lightning"
        elif "sdxl" in mlow or " xl" in f" {mlow}" or "realistic" in mlow:
            endpoint = "text2image_sdxl"
        form = {"prompt": final_prompt, "format": "png"}
        if model:
            form["model"] = model
        if endpoint == "text2image_flux":
            for kconf, kapi in (("lora_flux_1", "lora1"), ("lora_flux_2", "lora2")):
                v = getattr(img_cfg.dezgo, kconf, None)
                if v:
                    form[kapi] = v
        elif endpoint == "text2image":
            for kconf, kapi in (("lora_sd1_1", "lora1"), ("lora_sd1_2", "lora2")):
                v = getattr(img_cfg.dezgo, kconf, None)
                if v:
                    form[kapi] = v
        s1 = getattr(img_cfg.dezgo, 'lora1_strength', None)
        s2 = getattr(img_cfg.dezgo, 'lora2_strength', None)
        if s1 is not None:
            form["lora1_strength"] = str(s1)
        if s2 is not None:
            form["lora2_strength"] = str(s2)
        w = getattr(img_cfg.dezgo, 'width', None)
        h = getattr(img_cfg.dezgo, 'height', None)
        if w:
            form["width"] = str(w)
        if h:
            form["height"] = str(h)
        st = getattr(img_cfg.dezgo, 'steps', None)
        if endpoint in ("text2image", "text2image_flux", "text2image_sdxl") and st:
            form["steps"] = str(st)
        if endpoint != "text2image":
            if getattr(img_cfg.dezgo, 'transparent', False):
                form["transparent_background"] = "true"
        else:
            if getattr(img_cfg.dezgo, 'upscale', None):
                form["upscale"] = "true"
        headers = {"X-Dezgo-Key": key}
        multipart = {k: (None, v) for k, v in form.items()}
        async with _httpx.AsyncClient(timeout=_httpx.Timeout(10.0, read=60.0)) as client:
            r = await client.post(f"https://api.dezgo.com/{endpoint}", files=multipart, headers=headers)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Dezgo error: {r.text}")
            img = r.content
        images_root = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_root, exist_ok=True)
        try:
            cname = char.name if char else "default"
        except Exception:
            cname = "default"
        from pathlib import Path as _Path
        cdir = _Path(images_root) / (_safe_name(cname))
        cdir.mkdir(parents=True, exist_ok=True)
        images_dir = str(cdir)
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        sub = images_dir.replace(images_root, "").strip("/\\")
        url = f"/public/images/{(sub + '/' if sub else '')}{fname}"
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported image provider: {active}")


# ---------------------------------------------------------------------------
# Lorebook import
# ---------------------------------------------------------------------------


# Removed conflicting /lorebooks/import endpoint - now using database router


# ---------------------------------------------------------------------------
# ST-compatible export
# ---------------------------------------------------------------------------


@app.get("/characters/{char_id}/export")
async def export_character(char_id: int, db: Session = Depends(get_db)):
    char = db.get(CharacterModel, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    data = Character.model_validate(char).model_dump() if hasattr(Character, "model_validate") else Character.from_orm(char).dict()
    # Map to a simple ST-like JSON; full PNG card export is future work
    st = {
        "name": data.get("name"),
        "description": data.get("description", ""),
        "first_mes": data.get("first_message"),
        "alternate_greetings": data.get("alternate_greetings", []),
        "scenario": data.get("scenario"),
        "system_prompt": data.get("system_prompt"),
        "personality": data.get("personality"),
        "mes_example": data.get("mes_example"),
        "creator_notes": data.get("creator_notes"),
        "tags": data.get("tags", []),
    }
    from fastapi.responses import JSONResponse
    return JSONResponse(st, media_type="application/json")


# ---------------------------------------------------------------------------
# Themes storage (public/themes.json)
# ---------------------------------------------------------------------------


@app.get("/themes")
async def list_themes():
    data = load_json("themes.json", {})
    return {"names": list(data.keys())}


class SaveThemeRequest(BaseModel):
    name: str
    theme: Dict[str, str]


@app.post("/themes")
async def save_theme(req: SaveThemeRequest):
    data = load_json("themes.json", {})
    data[req.name] = req.theme
    save_json("themes.json", data)
    # also set as current theme
    cfg = load_config()
    try:
        from .config import AppearanceConfig
        cfg.theme = AppearanceConfig(**req.theme)
        save_config(cfg)
    except Exception:
        pass
    return {"status": "ok"}


@app.get("/themes/{name}")
async def get_theme(name: str):
    data = load_json("themes.json", {})
    if name not in data:
        raise HTTPException(status_code=404, detail="Theme not found")
    return data[name]


# ---------------------------------------------------------------------------
# Prompts storage (public/prompts.json)
# ---------------------------------------------------------------------------


@app.get("/prompts")
async def get_prompts():
    data = load_json("prompts.json", {"active": [], "all": [], "system": {"lore_suggest": "", "image_summary": ""}, "variables": {} })
    return data


@app.post("/prompts")
async def save_prompts(payload: Dict[str, object]):
    # Expect shape { active: list, all: list, system: { ... }, variables: { name: value } }
    try:
        if not isinstance(payload, dict):
            raise ValueError("invalid payload")
        active = payload.get("active") or []
        allp = payload.get("all") or []
        system = payload.get("system") or {}
        variables = payload.get("variables") or {}
        if not isinstance(active, list) or not isinstance(allp, list):
            raise ValueError("invalid prompts arrays")
        if not isinstance(system, dict) or not isinstance(variables, dict):
            raise ValueError("invalid system/variables")
        data = {"active": active, "all": allp, "system": system, "variables": variables}
        save_json("prompts.json", data)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------pressure
# RAG endpoints
# ---------------------------------------------------------------------------


class RAGStatsResponse(BaseModel):
    """RAG statistics dashboard response."""
    total_entries: int
    embedded_entries: int
    embedding_percentage: float
    last_embedding_date: str | None
    provider_type: str
    provider_status: str
    api_key_configured: bool


@app.get("/rag/stats", response_model=RAGStatsResponse)
async def get_rag_stats() -> RAGStatsResponse:
    """Return dashboard statistics for RAG functionality."""
    from .database import SessionLocal
    from .models import LoreEntry
    from .config import load_config
    import os

    db = SessionLocal()
    try:
        # Get total entries count
        total_entries = db.query(LoreEntry).count()

        # Get embedded entries count and most recent embedding date
        embedded_entries = db.query(LoreEntry).filter(LoreEntry.embedding.isnot(None)).count()

        # Calculate percentage
        embedding_percentage = round((embedded_entries / total_entries * 100), 1) if total_entries > 0 else 0.0

        # Get last embedding date from most recent entry
        last_entry = db.query(LoreEntry).filter(LoreEntry.embedding.isnot(None)).order_by(LoreEntry.updated_at.desc()).first()
        last_embedding_date = last_entry.updated_at.isoformat() if last_entry else None

        # Get active provider information
        cfg = load_config()
        provider_type = cfg.active_provider.value if hasattr(cfg, 'active_provider') and cfg.active_provider else "unknown"

        # Check API key status based on provider
        api_key_configured = False
        if cfg.active_provider and cfg.providers.get(cfg.active_provider):
            provider_config = cfg.providers[cfg.active_provider]
            api_key_configured = bool(provider_config.api_key)

        # Determine provider status
        provider_status = "Ready" if api_key_configured else "Requires API Key"

        return RAGStatsResponse(
            total_entries=total_entries,
            embedded_entries=embedded_entries,
            embedding_percentage=embedding_percentage,
            last_embedding_date=last_embedding_date,
            provider_type=provider_type,
            provider_status=provider_status,
            api_key_configured=api_key_configured
        )

    finally:
        db.close()


# Legacy lorebook export removed - now using database system


"""Primary FastAPI application for the CoolChat backend.

This module currently exposes a couple of utility endpoints as well as a very
small in-memory implementation of "character cards".  The goal is to mimic a
subset of SillyTavern's functionality so the front-end can store and retrieve
character definitions.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import httpx
from .config import AppConfig, ProviderConfig, load_config, save_config, mask_secret, Provider, ImagesConfig, ImageProvider
from .storage import load_json, save_json, public_dir
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

# Serve static files (e.g., imported character images) from repo ./public
try:
    import os as _os
    _public_dir = _os.path.join(_os.path.dirname(__file__), "..", "public")
    _public_dir = _os.path.abspath(_public_dir)
    _os.makedirs(_public_dir, exist_ok=True)
    app.mount("/public", StaticFiles(directory=_public_dir), name="public")
except Exception:
    pass


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
    data = payload.model_dump()
    if data.get("alternate_greetings") is None:
        data["alternate_greetings"] = []
    if data.get("tags") is None:
        data["tags"] = []
    if data.get("lorebook_ids") is None:
        data["lorebook_ids"] = []
    char = Character(id=_next_id, **data)
    _characters[_next_id] = char
    _next_id += 1
    _save_characters()
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
    _save_characters()
    return None


@app.put("/characters/{char_id}", response_model=Character)
async def update_character(char_id: int, payload: CharacterUpdate) -> Character:
    char = _characters.get(char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    data = payload.model_dump(exclude_unset=True)
    updated = char.model_copy(update=data)
    _characters[char_id] = updated
    _save_characters()
    return updated


# ---------------------------------------------------------------------------
# Lorebook endpoints
# ---------------------------------------------------------------------------


class LoreEntry(BaseModel):
    """Simple world info entry used for context injection."""

    id: int
    keyword: str
    content: str
    # Extended matching
    keywords: List[str] = []  # primary keywords (comma list in UI)
    logic: str = "AND ANY"  # AND ANY, AND ALL, NOT ANY, NOT ALL
    secondary_keywords: List[str] = []
    order: int = 0
    trigger: int = 100


class LoreEntryCreate(BaseModel):
    keyword: str
    content: str
    keywords: Optional[List[str]] = None
    logic: Optional[str] = None
    secondary_keywords: Optional[List[str]] = None
    order: Optional[int] = None
    trigger: Optional[int] = None


_lore: Dict[int, LoreEntry] = {}
_next_lore_id: int = 1


class Lorebook(BaseModel):
    id: int
    name: str
    description: str = ""
    entry_ids: List[int] = []


class LorebookCreate(BaseModel):
    name: str
    description: str = ""
    entries: Optional[List[LoreEntryCreate]] = None


_lorebooks: Dict[int, Lorebook] = {}
_next_lorebook_id: int = 1


@app.get("/lore", response_model=List[LoreEntry])
async def list_lore() -> List[LoreEntry]:
    """Return all lore entries."""

    return list(_lore.values())


@app.post("/lore", response_model=LoreEntry, status_code=201)
async def create_lore(payload: LoreEntryCreate) -> LoreEntry:
    """Create a new lore entry."""

    global _next_lore_id
    data = payload.model_dump()
    if data.get("keywords") is None:
        data["keywords"] = []
    if data.get("logic") is None:
        data["logic"] = "AND ANY"
    if data.get("secondary_keywords") is None:
        data["secondary_keywords"] = []
    data["order"] = data.get("order") or 0
    data["trigger"] = data.get("trigger") or 100
    entry = LoreEntry(id=_next_lore_id, **data)
    _lore[_next_lore_id] = entry
    _next_lore_id += 1
    _save_lore()
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
    _save_lore()
    return None


class LoreEntryUpdate(BaseModel):
    keyword: str | None = None
    content: str | None = None


@app.put("/lore/{entry_id}", response_model=LoreEntry)
async def update_lore(entry_id: int, payload: LoreEntryUpdate) -> LoreEntry:
    entry = _lore.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Lore entry not found")
    data = entry.model_dump()
    if payload.keyword is not None:
        data['keyword'] = payload.keyword
    if payload.content is not None:
        data['content'] = payload.content
    updated = LoreEntry(**data)
    _lore[entry_id] = updated
    _save_lore()
    return updated


@app.get("/lorebooks", response_model=List[Lorebook])
async def list_lorebooks() -> List[Lorebook]:
    return list(_lorebooks.values())


@app.post("/lorebooks", response_model=Lorebook, status_code=201)
async def create_lorebook(payload: LorebookCreate) -> Lorebook:
    global _next_lorebook_id, _next_lore
    lb = Lorebook(id=_next_lorebook_id, name=payload.name, description=payload.description, entry_ids=[])
    # Optionally create entries provided inline
    if payload.entries:
        global _next_lore_id
        for le in payload.entries:
            entry = LoreEntry(
                id=_next_lore_id,
                keyword=le.keyword,
                content=le.content,
                keywords=le.keywords or [],
                logic=le.logic or "AND ANY",
                secondary_keywords=le.secondary_keywords or [],
                order=le.order or 0,
                trigger=le.trigger or 100,
            )
            _lore[_next_lore_id] = entry
            lb.entry_ids.append(_next_lore_id)
            _next_lore_id += 1
    _lorebooks[_next_lorebook_id] = lb
    _next_lorebook_id += 1
    _save_lorebooks(); _save_lore()
    return lb


@app.get("/lorebooks/{lb_id}", response_model=Lorebook)
async def get_lorebook(lb_id: int) -> Lorebook:
    lb = _lorebooks.get(lb_id)
    if lb is None:
        raise HTTPException(status_code=404, detail="Lorebook not found")
    return lb


@app.delete("/lorebooks/{lb_id}", status_code=204)
async def delete_lorebook(lb_id: int) -> None:
    if lb_id not in _lorebooks:
        raise HTTPException(status_code=404, detail="Lorebook not found")
    del _lorebooks[lb_id]
    _save_lorebooks()
    return None


class LorebookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    entry_ids: Optional[List[int]] = None


@app.put("/lorebooks/{lb_id}", response_model=Lorebook)
async def update_lorebook(lb_id: int, payload: LorebookUpdate) -> Lorebook:
    lb = _lorebooks.get(lb_id)
    if lb is None:
        raise HTTPException(status_code=404, detail="Lorebook not found")
    data = lb.model_dump()
    if payload.name is not None:
        data['name'] = payload.name
    if payload.description is not None:
        data['description'] = payload.description
    if payload.entry_ids is not None:
        data['entry_ids'] = payload.entry_ids
    updated = Lorebook(**data)
    _lorebooks[lb_id] = updated
    _save_lorebooks()
    return updated


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
    global _characters, _next_id, _lore, _next_lore_id, _lorebooks, _next_lorebook_id, _memory, _next_memory_id, _chat_histories
    data = load_json("characters.json", {"next_id": 1, "items": []})
    _next_id = int(data.get("next_id", 1))
    _characters = {c["id"]: Character(**c) for c in data.get("items", [])}

    data = load_json("lore.json", {"next_id": 1, "items": []})
    _next_lore_id = int(data.get("next_id", 1))
    _lore = {e["id"]: LoreEntry(**e) for e in data.get("items", [])}

    data = load_json("lorebooks.json", {"next_id": 1, "items": []})
    _next_lorebook_id = int(data.get("next_id", 1))
    _lorebooks = {lb["id"]: Lorebook(**lb) for lb in data.get("items", [])}

    data = load_json("memory.json", {"next_id": 1, "items": []})
    _next_memory_id = int(data.get("next_id", 1))
    _memory = {m["id"]: MemoryEntry(**m) for m in data.get("items", [])}

    globals_dict = load_json("histories.json", {})
    _chat_histories.clear(); _chat_histories.update(globals_dict)


def _save_characters() -> None:
    save_json("characters.json", {"next_id": _next_id, "items": [c.model_dump() for c in _characters.values()]})


def _save_lore() -> None:
    save_json("lore.json", {"next_id": _next_lore_id, "items": [e.model_dump() for e in _lore.values()]})


def _save_lorebooks() -> None:
    save_json("lorebooks.json", {"next_id": _next_lorebook_id, "items": [lb.model_dump() for lb in _lorebooks.values()]})


def _save_memory() -> None:
    save_json("memory.json", {"next_id": _next_memory_id, "items": [m.model_dump() for m in _memory.values()]})


def _save_histories() -> None:
    save_json("histories.json", _chat_histories)


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


async def _llm_reply(message: str, cfg: AppConfig, recent_text: str | None = None) -> str:
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
    system_msg = _build_system_from_character(
        _characters.get(cfg.active_character_id) if hasattr(cfg, 'active_character_id') else None,
        getattr(cfg, 'user_persona', None),
        getattr(cfg, 'max_context_tokens', 2048),
        recent_text or "",
    )

    # Replace tokens in messages
    def _replace(text: str) -> str:
        char_name = None
        if cfg.active_character_id and cfg.active_character_id in _characters:
            char_name = _characters[cfg.active_character_id].name
        user_name = getattr(cfg, 'user_persona', None).name if getattr(cfg, 'user_persona', None) else "User"
        if not text:
            return text
        t = text.replace("{{char}}", char_name or "Character")
        t = t.replace("{{user}}", user_name)
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
            print("[CoolChat] OpenAI request:", {"url": url, "body": body})
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
                    print("[CoolChat] OpenAI response:", resp.json())
                except Exception:
                    print("[CoolChat] OpenAI response text:", resp.text)
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
        _chat_histories.pop(session_id, None)
    history = _chat_histories.setdefault(session_id, [])
    # Build recent text window for lore triggers
    recent_text = "\n".join([m.get("content", "") for m in history[-6:]] + [payload.message])
    try:
        reply = await _llm_reply(payload.message, cfg, recent_text=recent_text)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=str(exc))

    # Record history and trim by rough token budget
    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": reply})
    _trim_history(session_id, cfg)
    _save_histories()

    return ChatResponse(reply=reply)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    if _estimate_tokens(text) <= max_tokens:
        return text
    target_chars = max_tokens * 4
    return text[:target_chars] + "\n..."


def _build_system_from_character(char: Optional[Character], user_persona: Optional[object] = None, max_tokens: int = 2048, recent_text: str = "") -> Optional[str]:
    segments: List[str] = []
    # Include user persona if present
    if user_persona and getattr(user_persona, 'name', None):
        up = f"User Persona: {user_persona.name}\n{getattr(user_persona, 'description', '')}".strip()
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
            for lb_id in char.lorebook_ids:
                lb = _lorebooks.get(lb_id)
                if not lb:
                    continue
                for eid in lb.entry_ids:
                    e = _lore.get(eid)
                    if e:
                        include = False
                        if recent_text:
                            hay = recent_text.lower()
                            primaries = [x.lower() for x in (e.keywords or [e.keyword]) if x]
                            seconds = [x.lower() for x in (e.secondary_keywords or []) if x]
                            found_primary = [k for k in primaries if k in hay]
                            found_secondary = [k for k in seconds if k in hay]
                            logic = (e.logic or "AND ANY").upper()
                            if logic == "AND ALL":
                                include = len(found_primary) == len(primaries) and (not seconds or len(found_secondary) == len(seconds))
                            elif logic == "NOT ANY":
                                include = len(found_primary) == 0 and len(found_secondary) == 0
                            elif logic == "NOT ALL":
                                include = not (len(found_primary) == len(primaries))
                            else:  # AND ANY default
                                include = bool(found_primary) or bool(found_secondary)
                        else:
                            include = True
                        if include:
                            lore_texts.append(f"[{e.keyword}] {e.content}")
                            triggered_any = True
            if lore_texts:
                title = "Triggered World Info" if triggered_any else "World Info"
                segments.append(f"{title}:\n" + "\n".join(lore_texts))
    if not segments:
        return None
    return _truncate_to_tokens("\n\n".join(segments), max_tokens)


_chat_histories: Dict[str, List[Dict[str, str]]] = {}


def _trim_history(session_id: str, cfg: AppConfig) -> None:
    hist = _chat_histories.get(session_id)
    if not hist:
        return
    # Leave last N messages within budget (approx)
    budget = max(512, getattr(cfg, 'max_context_tokens', 2048))
    total = sum(_estimate_tokens(m.get("content", "")) for m in hist)
    while hist and total > budget * 2:
        removed = hist.pop(0)
        total -= _estimate_tokens(removed.get("content", ""))


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
    class ImagesOut(BaseModel):
        active: str
        pollinations: Dict[str, str | None]
        dezgo: Dict[str, str | None]
    images: ImagesOut
    theme: Dict[str, str] | None = None


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
    theme: Dict[str, str] | None = None


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
                "transparent": str(getattr(cfg.images.dezgo, 'transparent', False)),
                "width": str(getattr(cfg.images.dezgo, 'width', '')),
                "height": str(getattr(cfg.images.dezgo, 'height', '')),
                "steps": str(getattr(cfg.images.dezgo, 'steps', '')),
                "upscale": str(getattr(cfg.images.dezgo, 'upscale', '')),
            },
        ),
        theme=getattr(cfg, 'theme', None).model_dump() if getattr(cfg, 'theme', None) else None,
    )


@app.put("/config", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdate) -> ConfigResponse:
    cfg = load_config()

    # Merge provider-specific overrides
    if payload.providers:
        for key, upd in payload.providers.items():
            base = cfg.providers.get(key, ProviderConfig())
            if upd.api_key is not None:
                base.api_key = upd.api_key
            if upd.api_base is not None:
                base.api_base = upd.api_base
            if upd.model is not None:
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
            for k in ("model","api_key","lora_flux_1","lora_flux_2","lora_sd1_1","lora_sd1_2"):
                if k in dez:
                    setattr(imgs.dezgo, k, dez.get(k))
            for k in ("transparent","width","height","steps","upscale"):
                if k in dez:
                    setattr(imgs.dezgo, k, dez.get(k))
        cfg.images = imgs
    if payload.theme is not None:
        if not hasattr(cfg, 'theme') or cfg.theme is None:
            from .config import AppearanceConfig
            cfg.theme = AppearanceConfig()
        for k in ("primary","secondary","text1","text2","highlight","lowlight"):
            if k in payload.theme:
                setattr(cfg.theme, k, payload.theme[k])

    try:
        save_config(cfg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")

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
                "transparent": str(getattr(cfg.images.dezgo, 'transparent', False)),
                "width": str(getattr(cfg.images.dezgo, 'width', '')),
                "height": str(getattr(cfg.images.dezgo, 'height', '')),
                "steps": str(getattr(cfg.images.dezgo, 'steps', '')),
                "upscale": str(getattr(cfg.images.dezgo, 'upscale', '')),
            },
        ),
        theme=getattr(cfg, 'theme', None).model_dump() if getattr(cfg, 'theme', None) else None,
    )


class ThemeSuggestRequest(BaseModel):
    primary: str


class ThemeSuggestResponse(BaseModel):
    colors: List[str]


@app.post("/theme/suggest", response_model=ThemeSuggestResponse)
async def theme_suggest(payload: ThemeSuggestRequest) -> ThemeSuggestResponse:
    cfg = load_config()
    prompt = f"Given {payload.primary} please suggest 5 more colors that will provide an easily readable and pleasing UI theme. Select a secondary color that compliments the primary, Two text colors that will stand out and be readable with the primary and secondary colors as their background respectively. And include a highlight and lowlight color. Return the colors as comma separated hex codes. Do not include anything else in your reply."
    reply = await _llm_reply(prompt, cfg)
    text = reply.strip().strip('`')
    if text.lower().startswith('json'):
        text = text[4:].strip()
    parts = [p.strip() for p in text.split(',') if p.strip()]
    parts = parts[:5]
    return ThemeSuggestResponse(colors=parts)


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
                fname = f"{_next_id}.png"
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
    return await create_character(payload)


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
        # Pollinations docs list examples; no public models endpoint — provide common examples
        return ImageModelsResponse(models=["flux/dev", "sdxl", "stable-diffusion-2-1", "playground-v2.5"])
    if p == ImageProvider.DEZGO:
        # Subset examples per docs
        return ImageModelsResponse(models=["anything-v4", "realistic-vision-v5", "deliberate-v2", "sdxl-base-1.0"])
    return ImageModelsResponse(models=[])


class GenerateFromChatRequest(BaseModel):
    session_id: str | None = None


class GenerateFromChatResponse(BaseModel):
    image_url: str
    prompt: str


@app.post("/images/generate_from_chat", response_model=GenerateFromChatResponse)
async def generate_from_chat(payload: GenerateFromChatRequest) -> GenerateFromChatResponse:
    cfg = load_config()
    sid = payload.session_id or "default"
    hist = _chat_histories.get(sid, [])
    convo = "\n".join([f"{m['role']}: {m['content']}" for m in hist][-10:])
    # Ask LLM for a one-line scene prompt
    scene_req = (
        "Summarize the current scene for an image in a single concise line suitable as a text-to-image prompt. "
        "Focus on salient visual elements and avoid names, extra quotes, or brackets."
        "\n\nConversation:\n" + convo
    )
    desc = await _llm_reply(scene_req, cfg)
    # Clean JSON-string replies
    try:
        import json as _json
        parsed = _json.loads(desc)
        if isinstance(parsed, str):
            desc = parsed
    except Exception:
        pass
    # Character-specific prepend/append
    char = _characters.get(cfg.active_character_id) if getattr(cfg, 'active_character_id', None) else None
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
        q = final_prompt if not model else f"{final_prompt}, model={model}"
        poll_url = f"https://image.pollinations.ai/prompt/{_urlp.quote(q)}"
        if getattr(cfg, 'debug', None) and getattr(cfg.debug, 'log_prompts', False):
            print("[CoolChat] Pollinations URL:", poll_url)
        timeout = _httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with _httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(poll_url)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail="Pollinations image fetch failed")
            img = r.content
        images_dir = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_dir, exist_ok=True)
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        url = f"/public/images/{fname}"
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    elif active == ImageProvider.DEZGO:
        import httpx as _httpx, os as _os, time as _time
        key = getattr(img_cfg.dezgo, 'api_key', None)
        if not key:
            raise HTTPException(status_code=400, detail="Missing Dezgo API key")
        model = getattr(img_cfg.dezgo, 'model', None)
        body = {"prompt": final_prompt}
        if model:
            body["model"] = model
        # LORAs
        for k in ("lora_flux_1","lora_flux_2","lora_sd1_1","lora_sd1_2"):
            v = getattr(img_cfg.dezgo, k, None)
            if v:
                body[k] = v
        # Options
        if getattr(img_cfg.dezgo, 'transparent', False):
            body["transparent"] = "true"
        for k in ("width","height","steps"):
            v = getattr(img_cfg.dezgo, k, None)
            if v:
                body[k] = str(v)
        if getattr(img_cfg.dezgo, 'upscale', None):
            body["upscale"] = "true"
        headers = {"Authorization": key}
        async with _httpx.AsyncClient(timeout=_httpx.Timeout(10.0, read=60.0)) as client:
            r = await client.post("https://api.dezgo.com/text2image", data=body, headers=headers)
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Dezgo error: {r.text}")
            img = r.content
        images_dir = _os.path.join(_os.path.dirname(__file__), "..", "public", "images")
        _os.makedirs(images_dir, exist_ok=True)
        fname = f"scene_{int(_time.time()*1000)}.png"
        fpath = _os.path.join(images_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(img)
        url = f"/public/images/{fname}"
        return GenerateFromChatResponse(image_url=url, prompt=final_prompt)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported image provider: {active}")


# ---------------------------------------------------------------------------
# Lorebook import
# ---------------------------------------------------------------------------


@app.post("/lorebooks/import", response_model=Lorebook, status_code=201)
async def import_lorebook(file: UploadFile = File(...)) -> Lorebook:
    raw = await file.read()
    import json as _json
    try:
        data = _json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid lorebook file: {e}")
    # Support SillyTavern World Info format and simple formats
    def _st_to_entries(items):
        out = []
        for i in items or []:
            # Accept either dict entries or simple strings
            if isinstance(i, str):
                out.append(LoreEntryCreate(keyword=i, content=""))
                continue
            if not isinstance(i, dict):
                continue
            # SillyTavern: keys or triggers specify array of keywords
            keys = i.get("keys") or i.get("triggers") or []
            kw = keys[0] if isinstance(keys, list) and keys else (i.get("keyword") or "")
            content = i.get("content") or i.get("text") or i.get("entry") or ""
            logic = i.get("logic") or "AND ANY"
            secondary = i.get("secondary_keys") or i.get("secondary_keywords") or []
            order = i.get("order") or 0
            trigger = i.get("probability") or i.get("trigger") or 100
            out.append(LoreEntryCreate(keyword=kw, content=content, keywords=keys if isinstance(keys, list) else [], logic=logic, secondary_keywords=secondary, order=order, trigger=trigger))
        return out

    if isinstance(data, list):
        entries = _st_to_entries(data)
        lb = await create_lorebook(LorebookCreate(name="Imported Lorebook", description="", entries=entries))
        return lb
    elif isinstance(data, dict):
        # SillyTavern commonly: { name, description?, entries: [...] }
        name = data.get("name") or data.get("book_name") or data.get("title") or "Imported Lorebook"
        description = data.get("description") or ""
        entries_data = data.get("entries") or data.get("world_info") or []
        entries = _st_to_entries(entries_data)
        lb = await create_lorebook(LorebookCreate(name=name, description=description, entries=entries))
        return lb
    else:
        raise HTTPException(status_code=400, detail="Unsupported lorebook JSON structure")


# ---------------------------------------------------------------------------
# ST-compatible export
# ---------------------------------------------------------------------------


@app.get("/characters/{char_id}/export")
async def export_character(char_id: int):
    char = _characters.get(char_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    data = char.model_dump()
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


@app.get("/lorebooks/{lb_id}/export")
async def export_lorebook(lb_id: int):
    lb = _lorebooks.get(lb_id)
    if not lb:
        raise HTTPException(status_code=404, detail="Lorebook not found")
    entries = []
    for eid in lb.entry_ids:
        e = _lore.get(eid)
        if not e:
            continue
        entries.append({"keys": [e.keyword], "content": e.content})
    st = {
        "name": lb.name,
        "description": lb.description,
        "entries": entries,
    }
    from fastapi.responses import JSONResponse
    return JSONResponse(st, media_type="application/json")


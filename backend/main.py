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
from .config import AppConfig, ProviderConfig, load_config, save_config, mask_secret, Provider
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

# Serve static files (e.g., imported character images)
try:
    import os as _os
    _static_dir = _os.path.join(_os.path.dirname(__file__), "static")
    _os.makedirs(_static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
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


@app.put("/characters/{char_id}", response_model=Character)
async def update_character(char_id: int, payload: CharacterUpdate) -> Character:
    char = _characters.get(char_id)
    if char is None:
        raise HTTPException(status_code=404, detail="Character not found")
    data = payload.model_dump(exclude_unset=True)
    updated = char.model_copy(update=data)
    _characters[char_id] = updated
    return updated


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
            entry = LoreEntry(id=_next_lore_id, keyword=le.keyword, content=le.content)
            _lore[_next_lore_id] = entry
            lb.entry_ids.append(_next_lore_id)
            _next_lore_id += 1
    _lorebooks[_next_lorebook_id] = lb
    _next_lorebook_id += 1
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


def _active_provider_cfg(cfg: AppConfig) -> tuple[str, ProviderConfig]:
    p = cfg.active_provider
    pc = cfg.providers.get(p)
    if pc is None:
        # Fallback to echo config if missing
        p = Provider.ECHO
        pc = cfg.providers.get(p, ProviderConfig())
    return p, pc


async def _llm_reply(message: str, cfg: AppConfig) -> str:
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
    # Build optional system message from active character
    system_msg = _build_system_from_character(_characters.get(cfg.active_character_id) if hasattr(cfg, 'active_character_id') else None)

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

    # Unknown provider
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Return a chat reply using configured provider (echo by default)."""

    cfg = load_config()
    # Try to incorporate active character persona as a system prompt when calling LLMs
    active_char = None
    if cfg.active_character_id and cfg.active_character_id in _characters:
        active_char = _characters[cfg.active_character_id]
    # For now we only pass the user message; system persona is stitched inside _llm_reply
    try:
        reply = await _llm_reply(_inject_persona(payload.message, active_char), cfg)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(reply=reply)


def _build_system_from_character(char: Optional[Character]) -> Optional[str]:
    if not char:
        return None
    segments: List[str] = []
    if char.system_prompt:
        segments.append(char.system_prompt)
    if char.personality:
        segments.append(f"Personality: {char.personality}")
    if char.scenario:
        segments.append(f"Scenario: {char.scenario}")
    if char.description:
        segments.append(f"Description: {char.description}")
    # Append linked lorebook contents naively
    if char.lorebook_ids:
        lore_texts = []
        for lb_id in char.lorebook_ids:
            lb = _lorebooks.get(lb_id)
            if not lb:
                continue
            for eid in lb.entry_ids:
                e = _lore.get(eid)
                if e:
                    lore_texts.append(f"[{e.keyword}] {e.content}")
        if lore_texts:
            segments.append("World Info:\n" + "\n".join(lore_texts))
    if not segments:
        return None
    return "\n\n".join(segments)


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
    )


@app.get("/config/raw")
async def get_config_raw():
    """Return the full config including API keys for Advanced tab."""
    cfg = load_config()
    return cfg.model_dump()


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
        ids = []
        for item in data.get("data", []):
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
            # Save the PNG to static folder and set avatar_url
            try:
                import os as _os
                static_chars = _os.path.join(_os.path.dirname(__file__), "static", "characters")
                _os.makedirs(static_chars, exist_ok=True)
                fname = f"{_next_id}.png"
                fpath = _os.path.join(static_chars, fname)
                with open(fpath, "wb") as fh:
                    fh.write(raw)
                data["avatar_url"] = f"/static/characters/{fname}"
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
    # Extract a JSON string; accept plain string or quoted JSON
    value = reply
    try:
        import json as _json
        j = _json.loads(reply)
        if isinstance(j, str):
            value = j
    except Exception:
        pass
    return SuggestResponse(value=value)


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
    # Accept either { name, description?, entries: [{keyword, content}] } or just [ {keyword, content} ]
    if isinstance(data, list):
        entries = [LoreEntryCreate(keyword=i.get("keyword", ""), content=i.get("content", "")) for i in data]
        lb = await create_lorebook(LorebookCreate(name="Imported Lorebook", description="", entries=entries))
        return lb
    elif isinstance(data, dict):
        name = data.get("name") or "Imported Lorebook"
        description = data.get("description") or ""
        entries_data = data.get("entries") or []
        entries = [LoreEntryCreate(keyword=i.get("keyword", ""), content=i.get("content", "")) for i in entries_data]
        lb = await create_lorebook(LorebookCreate(name=name, description=description, entries=entries))
        return lb
    else:
        raise HTTPException(status_code=400, detail="Unsupported lorebook JSON structure")


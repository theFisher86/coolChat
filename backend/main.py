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
import uuid
import html as _html
from pathlib import Path as _Path

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

# Serve plugins directory statically and list manifests
try:
    import os as _os
    _plugins_dir = _os.path.join(_os.path.dirname(__file__), "..", "plugins")
    _plugins_dir = _os.path.abspath(_plugins_dir)
    _os.makedirs(_plugins_dir, exist_ok=True)
    app.mount("/plugins", StaticFiles(directory=_plugins_dir), name="plugins")
except Exception:
    pass

@app.get("/plugins")
async def list_plugins() -> Dict[str, object]:
    items: List[Dict[str, object]] = []
    try:
        import json as _json
        root = _Path(_plugins_dir)
        if root.exists():
            for p in sorted(root.iterdir()):
                try:
                    if not p.is_dir():
                        continue
                    man = p / "manifest.json"
                    if not man.exists():
                        continue
                    data = _json.loads(man.read_text(encoding="utf-8"))
                    pid = data.get("id") or p.name
                    items.append({
                        "id": pid,
                        "name": data.get("name") or pid,
                        "version": data.get("version") or "",
                        "client": data.get("client") or {},
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return {"plugins": items}


@app.post("/phone/debug")
async def phone_debug(payload: Dict[str, object]):
    try:
        print("[CoolChat] Phone debug:", payload)
    except Exception:
        pass
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Phone: templates and iframe allowlist
# ---------------------------------------------------------------------------


class PhoneRenderRequest(BaseModel):
    template: str
    data: Dict[str, object] | None = None


class PhoneRenderResponse(BaseModel):
    url: str


def _phone_templates_dir() -> _Path:
    return (public_dir() / "templates").resolve()


def _phone_views_dir() -> _Path:
    d = (public_dir() / "phone_views").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _escape(v: object) -> str:
    if v is None:
        return ""
    return _html.escape(str(v), quote=True)


def _render_template_html(tpl_html: str, tpl_css: str | None, data: Dict[str, object] | None) -> str:
    # Very small mustache-like replacer: {{key}} -> escaped value
    out = tpl_html
    for k, v in (data or {}).items():
        token = "{{" + str(k) + "}}"
        # Allow basic non-escaped insertion with triple braces {{{key}}}
        out = out.replace("{{{" + str(k) + "}}}", str(v) if v is not None else "")
        out = out.replace(token, _escape(v))
    # Inject CSS if present
    if tpl_css:
        if "</head>" in out:
            out = out.replace("</head>", f"<style>\n{tpl_css}\n</style>\n</head>")
        else:
            out = f"<style>\n{tpl_css}\n</style>\n" + out
    return out


@app.get("/phone/templates")
async def phone_list_templates() -> Dict[str, object]:
    root = _phone_templates_dir()
    items: List[Dict[str, str]] = []
    if root.exists():
        for p in root.iterdir():
            if p.is_dir():
                name = p.name
                title = name.replace("_", " ").title()
                manifest = p / "manifest.json"
                try:
                    if manifest.exists():
                        import json as _json
                        m = _json.loads(manifest.read_text(encoding="utf-8"))
                        title = m.get("title", title)
                except Exception:
                    pass
                items.append({"name": name, "title": title})
    return {"templates": items}


class PhoneCreateTemplateRequest(BaseModel):
    name: str
    html: str
    css: Optional[str] = None
    overwrite: bool = False
    title: Optional[str] = None


@app.post("/phone/templates")
async def phone_create_template(payload: PhoneCreateTemplateRequest) -> Dict[str, object]:
    name = (payload.name or "").strip()
    if not name or not all(ch.isalnum() or ch in ("-", "_") for ch in name):
        raise HTTPException(status_code=400, detail="Invalid template name")
    tdir = _phone_templates_dir() / name
    if tdir.exists() and not payload.overwrite:
        raise HTTPException(status_code=409, detail="Template already exists")
    tdir.mkdir(parents=True, exist_ok=True)
    # Write HTML and CSS
    (tdir / "template.html").write_text(payload.html, encoding="utf-8")
    if payload.css is not None:
        (tdir / "styles.css").write_text(payload.css, encoding="utf-8")
    # Optional manifest
    try:
        import json as _json
        (tdir / "manifest.json").write_text(_json.dumps({"title": payload.title or name}, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok", "name": name}


@app.post("/phone/render", response_model=PhoneRenderResponse)
async def phone_render(payload: PhoneRenderRequest) -> PhoneRenderResponse:
    name = (payload.template or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Missing template name")
    tdir = _phone_templates_dir() / name
    if not tdir.exists():
        raise HTTPException(status_code=404, detail="Unknown template")
    html_path = tdir / "template.html"
    css_path = tdir / "styles.css"
    if not html_path.exists():
        raise HTTPException(status_code=500, detail="Template missing template.html")
    tpl_html = html_path.read_text(encoding="utf-8")
    tpl_css = css_path.read_text(encoding="utf-8") if css_path.exists() else None
    out_html = _render_template_html(tpl_html, tpl_css, payload.data or {})
    vid = f"{uuid.uuid4().hex}.html"
    out_path = _phone_views_dir() / vid
    out_path.write_text(out_html, encoding="utf-8")
    return PhoneRenderResponse(url=f"/public/phone_views/{vid}")


@app.get("/phone/allowlist")
async def phone_allowlist_get() -> Dict[str, object]:
    data = load_json("phone.json", {"allowlist": []})
    al = data.get("allowlist") if isinstance(data, dict) else []
    if not isinstance(al, list):
        al = []
    # Normalize to strings
    al = [str(x) for x in al if isinstance(x, (str, int, float))]
    return {"allowlist": al}


class PhoneAllowlistAdd(BaseModel):
    url: str


@app.post("/phone/allowlist")
async def phone_allowlist_add(payload: PhoneAllowlistAdd) -> Dict[str, object]:
    raw = (payload.url or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Missing url")
    data = load_json("phone.json", {"allowlist": []})
    al = data.get("allowlist") if isinstance(data, dict) else []
    if not isinstance(al, list):
        al = []
    if raw not in al:
        al = [raw] + al  # prepend as requested
    data["allowlist"] = al
    save_json("phone.json", data)
    return {"allowlist": al}


@app.delete("/phone/allowlist")
async def phone_allowlist_remove(url: str) -> Dict[str, object]:
    data = load_json("phone.json", {"allowlist": []})
    al = data.get("allowlist") if isinstance(data, dict) else []
    if not isinstance(al, list):
        al = []
    al = [x for x in al if str(x) != url]
    data["allowlist"] = al
    save_json("phone.json", data)
    return {"allowlist": al}


@app.on_event("startup")
async def _startup_load_state():
    try:
        _load_state()
    except Exception as e:
        try:
            print("[CoolChat] startup load_state error:", e)
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
    try:
        _save_character_snapshot(char)
    except Exception:
        pass
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
    try:
        _save_character_snapshot(updated)
    except Exception:
        pass
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
    title: str | None = None


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
    if payload.title is not None:
        data['title'] = payload.title
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
    try:
        _save_lorebook_snapshot(lb)
    except Exception:
        pass
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
    try:
        _save_lorebook_snapshot(updated)
    except Exception:
        pass
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


def _st_to_entries(items):
    out = []
    for i in items or []:
        if isinstance(i, str):
            out.append(LoreEntryCreate(keyword=i, content=""))
            continue
        if not isinstance(i, dict):
            continue
        keys = i.get("keys") or i.get("triggers") or i.get("key") or []
        if isinstance(keys, dict):
            keys = list(keys.values())
        kw = keys[0] if isinstance(keys, list) and keys else (i.get("keyword") or i.get("comment") or "")
        content = i.get("content") or i.get("text") or i.get("entry") or ""
        secondary = i.get("secondary_keys") or i.get("secondary_keywords") or i.get("keysecondary") or []
        logic_map = {0: "AND ANY", 3: "AND ALL", 1: "NOT ALL", 2: "NOT ANY"}
        logic_val = i.get("logic")
        if logic_val is None:
            sl = i.get("selectiveLogic")
            if isinstance(sl, int):
                logic_val = logic_map.get(sl, "AND ANY")
        if not logic_val:
            logic_val = "AND ANY"
        order = i.get("order") or 0
        trigger = i.get("probability") or i.get("trigger") or 100
        out.append(LoreEntryCreate(keyword=kw, content=content, keywords=keys if isinstance(keys, list) else [], logic=logic_val, secondary_keywords=secondary, order=order, trigger=trigger))
    return out


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

    # Additionally auto-load any characters/lorebooks from public folders
    try:
        _load_from_public_folders()
    except Exception as e:
        try:
            print("[CoolChat] load_from_public_folders error:", e)
        except Exception:
            pass


def _safe_name(name: str) -> str:
    import re
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "").strip())
    return s or "item"


def _export_character_st_json(char: Character) -> Dict[str, object]:
    data = char.model_dump()
    return {
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
        # Non-standard extras
        "avatar_url": data.get("avatar_url"),
        "lorebook_ids": data.get("lorebook_ids", []),
        "image_prompt_prefix": data.get("image_prompt_prefix"),
        "image_prompt_suffix": data.get("image_prompt_suffix"),
    }


def _save_character_snapshot(char: Character) -> None:
    import json as _json, os as _os
    chars_dir = public_dir() / "characters"
    try:
        chars_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{char.id}_{_safe_name(char.name)}.json"
        (chars_dir / fname).write_text(_json.dumps(_export_character_st_json(char), indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


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


def _parse_lorebook_data_to_entries(data: object) -> tuple[str, str, List["LoreEntryCreate"]]:
    import os as _os
    # Support SillyTavern World Info format and simple formats

    name = "Imported Lorebook"
    description = ""
    if isinstance(data, list):
        entries = _st_to_entries(data)
    elif isinstance(data, dict):
        entries_data = data.get("entries") or data.get("world_info") or []
        if isinstance(entries_data, dict):
            items = list(entries_data.values())
        else:
            items = entries_data
        entries = _st_to_entries(items)
        name = data.get("name") or data.get("book_name") or data.get("title") or name
        description = data.get("description") or ""
    else:
        entries = []
    return name, description, entries


def _load_from_public_folders() -> None:
    """Auto-import any characters and lorebooks found in public folders."""
    import json as _json
    import os as _os
    # Characters
    cdir = public_dir() / "characters"
    if cdir.exists():
        # Build a set of existing names (case-insensitive)
        existing_names = {c.name.strip().lower() for c in _characters.values()}
        for entry in sorted(cdir.iterdir()):
            try:
                if entry.is_file() and entry.suffix.lower() == ".png":
                    raw = entry.read_bytes()
                    if raw[:8] != b"\x89PNG\r\n\x1a\n":
                        continue
                    data = _parse_png_card(raw)
                    name = (data.get("name") or "").strip()
                    if not name or name.lower() in existing_names:
                        continue
                    payload = CharacterCreate(
                        name=name,
                        description=data.get("description", ""),
                        avatar_url=f"/public/characters/{entry.name}",
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
                    # Create directly (inline rather than HTTP)
                    global _next_id
                    data_c = payload.model_dump()
                    if data_c.get("alternate_greetings") is None:
                        data_c["alternate_greetings"] = []
                    if data_c.get("tags") is None:
                        data_c["tags"] = []
                    if data_c.get("lorebook_ids") is None:
                        data_c["lorebook_ids"] = []
                    char = Character(id=_next_id, **data_c)
                    _characters[_next_id] = char
                    _next_id += 1
                    existing_names.add(name.lower())
                elif entry.is_file() and entry.suffix.lower() == ".json":
                    obj = _json.loads(entry.read_text(encoding="utf-8"))
                    name = (obj.get("name") or obj.get("title") or "").strip()
                    if not name or name.lower() in existing_names:
                        continue
                    payload = CharacterCreate(
                        name=name,
                        description=obj.get("description", ""),
                        avatar_url=obj.get("avatar_url"),
                        first_message=obj.get("first_message") or obj.get("first_mes"),
                        alternate_greetings=obj.get("alternate_greetings") or [],
                        scenario=obj.get("scenario"),
                        system_prompt=obj.get("system_prompt"),
                        personality=obj.get("personality"),
                        mes_example=obj.get("mes_example"),
                        creator_notes=obj.get("creator_notes"),
                        tags=obj.get("tags") or [],
                        post_history_instructions=obj.get("post_history_instructions"),
                        extensions=obj.get("extensions"),
                        lorebook_ids=obj.get("lorebook_ids") or [],
                    )
                    data_c = payload.model_dump()
                    if data_c.get("alternate_greetings") is None:
                        data_c["alternate_greetings"] = []
                    if data_c.get("tags") is None:
                        data_c["tags"] = []
                    if data_c.get("lorebook_ids") is None:
                        data_c["lorebook_ids"] = []
                    char = Character(id=_next_id, **data_c)
                    _characters[_next_id] = char
                    _next_id += 1
                    existing_names.add(name.lower())
            except Exception:
                continue

    # Lorebooks
    ldir = public_dir() / "lorebooks"
    if ldir.exists():
        existing_lb_names = {lb.name.strip().lower() for lb in _lorebooks.values()}
        for entry in sorted(ldir.iterdir()):
            try:
                if not (entry.is_file() and entry.suffix.lower() == ".json"):
                    continue
                obj = _json.loads(entry.read_text(encoding="utf-8"))
                name, description, entries = _parse_lorebook_data_to_entries(obj)
                if not name or name.strip().lower() in existing_lb_names:
                    continue
                # Create Lorebook
                global _next_lorebook_id, _next_lore_id
                lb = Lorebook(id=_next_lorebook_id, name=name, description=description, entry_ids=[])
                for le in entries:
                    entry_obj = LoreEntry(
                        id=_next_lore_id,
                        keyword=le.keyword,
                        content=le.content,
                        keywords=le.keywords or [],
                        logic=le.logic or "AND ANY",
                        secondary_keywords=le.secondary_keywords or [],
                        order=le.order or 0,
                        trigger=le.trigger or 100,
                    )
                    _lore[_next_lore_id] = entry_obj
                    lb.entry_ids.append(_next_lore_id)
                    _next_lore_id += 1
                _lorebooks[_next_lorebook_id] = lb
                _next_lorebook_id += 1
                existing_lb_names.add(name.strip().lower())
            except Exception:
                continue


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
    system_msg = None if disable_system else (
        system_override if system_override is not None else _build_system_from_character(
            _characters.get(cfg.active_character_id) if hasattr(cfg, 'active_character_id') else None,
            getattr(cfg, 'user_persona', None),
            (getattr(cfg.providers.get(provider, ProviderConfig()), 'max_context_tokens', None) or getattr(cfg, 'max_context_tokens', 2048)),
            recent_text or "",
        )
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
        if en.get("phone"):
            tools_lines.append("PhonePanel: Open a URL on the user's phone panel.")
        if en.get("phone_template"):
            tools_lines.append("PhoneTemplates: Render a predefined mini-site in the phone using a template and variables.")
        if en.get("phone_allowlist_add"):
            tools_lines.append("PhoneAllowlist: Add an iframe-friendly site to the allowlist when relevant.")
        if en.get("phone_create_template"):
            tools_lines.append("PhoneCreateTemplate: Save a new template (html/css) for future use.")
        if en.get("image_gen"): tools_lines.append("ImageGen: Request an image with a concise prompt.")
        if en.get("lore_suggest"): tools_lines.append("LoreSuggest: Suggest new lore entries (keyword + content).")
    except Exception:
        en = {}
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
                    "Types: 'image_request' (payload:{prompt:string}), 'phone_url' (payload:{url:string}), 'phone_template' (payload:{template:string, data:object}), 'phone_allowlist_add' (payload:{url:string}), 'phone_create_template' (payload:{name:string, html:string, css?:string, overwrite?:boolean}), 'lore_suggestions' (payload:{items:[{keyword:string, content:string}]}). "
                    "Optionally include plain 'text' content outside of tool calls. Do not wrap JSON in code fences."
                )
        except Exception:
            pass

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
    # Include phone template/allowlist/create guidance if present and enabled
    try:
        if isinstance(system_prompts, dict):
            if en.get("phone_template") and system_prompts.get("phone_templates"):
                segments.append(str(system_prompts.get("phone_templates")))
            if en.get("phone_allowlist_add") and system_prompts.get("phone_allowlist"):
                segments.append(str(system_prompts.get("phone_allowlist")))
            if en.get("phone_create_template") and system_prompts.get("phone_create_template"):
                segments.append(str(system_prompts.get("phone_create_template")))
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
                            lore_texts.append(f"[{e.keyword}] {e.content}")
                            triggered_any = True
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
            for lb_id in actives:
                lb = _lorebooks.get(lb_id)
                if not lb:
                    continue
                for eid in lb.entry_ids:
                    e = _lore.get(eid)
                    if e:
                        lore_texts.append(f"[{e.keyword}] {e.content}")
            if lore_texts:
                segments.append("Active Lorebooks:\n" + "\n".join(lore_texts))
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
            tool_lines.append("Tool: PhoneTemplates — Use 'phone_template' to render a mini-site with variables. Example payload: {template:'storefront', data:{store_name:'Fake Mart', item_name:'Leg Lamp', description:'...', price:'$59.95', image_url:'/public/images/default/item.png', quantity:1}}.")
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


def _trim_history(session_id: str, cfg: AppConfig) -> None:
    hist = _chat_histories.get(session_id)
    if not hist:
        return
    # Leave last N messages within budget (approx)
    budget = max(512, getattr(cfg, "max_context_tokens", 2048))
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
    # Ensure state loaded
    if not _chat_histories:
        try:
            _load_state()
        except Exception:
            pass
    return ChatListResponse(sessions=list(_chat_histories.keys()))


class ChatHistoryResponse(BaseModel):
    messages: List[Dict[str, str]]


@app.get("/chats/{session_id}", response_model=ChatHistoryResponse)
async def get_chat(session_id: str) -> ChatHistoryResponse:
    msgs = _chat_histories.get(session_id) or []
    return ChatHistoryResponse(messages=msgs)


@app.post("/chats/{session_id}/reset")
async def reset_chat(session_id: str) -> Dict[str, str]:
    _chat_histories.pop(session_id, None)
    _save_histories()
    return {"status": "ok"}


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
    data = load_json("tools.json", {"enabled": {"phone": False, "phone_template": False, "phone_allowlist_add": False, "phone_create_template": False, "image_gen": False, "lore_suggest": False}, "per_character": {}})
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
    data = load_json("tools.json", {"enabled": {"phone": False, "phone_template": False, "phone_allowlist_add": False, "phone_create_template": False, "image_gen": False, "lore_suggest": False}, "per_character": {}})
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
    hist = _chat_histories.get(sid, [])
    convo = "\n".join([f"{m['role']}: {m.get('content','')}" for m in hist][-20:])
    # Collect existing keywords from active lorebooks
    existing = set()
    active_ids = (getattr(cfg, 'active_lorebook_ids', []) or [])
    for lb_id in active_ids:
        lb = _lorebooks.get(lb_id)
        if not lb:
            continue
        for eid in lb.entry_ids:
            e = _lore.get(eid)
            if e and e.keyword:
                existing.add(e.keyword.strip().lower())
            for k in (e.keywords or []):
                if k:
                    existing.add(k.strip().lower())
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
    hist = _chat_histories.get(sid, [])
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
    char = _characters.get(cfg.active_character_id) if getattr(cfg, 'active_character_id', None) else None
    prefix = getattr(char, 'image_prompt_prefix', None) or ""
    suffix = getattr(char, 'image_prompt_suffix', None) or ""
    final_prompt = (prefix + " " + desc + " " + suffix).strip()

    # Dispatch to configured image backend
    img_cfg: ImagesConfig = getattr(cfg, 'images', ImagesConfig())
    active = getattr(img_cfg, 'active', ImageProvider.POLLINATIONS)
    print("[CoolChat] images.generate_from_chat active=", active)
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
            cname = _characters.get(getattr(cfg, 'active_character_id', None)).name if getattr(cfg, 'active_character_id', None) in _characters else "default"
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
            hist = _chat_histories.setdefault(sid, [])
            hist.append({"role": "assistant", "image_url": url, "content": final_prompt})
            _save_histories()
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
            cname = _characters.get(getattr(cfg, 'active_character_id', None)).name if getattr(cfg, 'active_character_id', None) in _characters else "default"
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
            hist = _chat_histories.setdefault(sid, [])
            hist.append({"role": "assistant", "image_url": url, "content": final_prompt})
            _save_histories()
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
            cname = _characters.get(getattr(cfg, 'active_character_id', None)).name if getattr(cfg, 'active_character_id', None) in _characters else "default"
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
            cname = _characters.get(getattr(cfg, 'active_character_id', None)).name if getattr(cfg, 'active_character_id', None) in _characters else "default"
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


@app.post("/lorebooks/import", response_model=Lorebook, status_code=201)
async def import_lorebook(file: UploadFile = File(...)) -> Lorebook:
    raw = await file.read()
    import json as _json
    try:
        data = _json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid lorebook file: {e}")
    # Support SillyTavern World Info format and simple formats

    if isinstance(data, (list, dict)):
        fname = getattr(file, 'filename', None)
        inferred = os.path.splitext(os.path.basename(fname))[0] if fname else None
        name, description, entries = _parse_lorebook_data_to_entries(data)
        if inferred and name == "Imported Lorebook":
            name = inferred
        print("[CoolChat] lore import: parsed entries count:", len(entries))
        lb = await create_lorebook(LorebookCreate(name=name, description=description, entries=entries))
        try:
            _save_lorebook_snapshot(lb)
        except Exception:
            pass
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
    data = load_json(
        "prompts.json",
        {
            "active": [],
            "all": [],
            "system": {
                "main": "",
                "tool_call": "",
                "lore_suggest": "",
                "image_summary": "",
                "phone_templates": "When a compact in-app experience suits the task (storefront, profile, article, gallery), render a phone template: return a toolCalls entry with type 'phone_template' and payload {template:string, data:object}. Choose from /phone/templates. Include keys like store_name, item_name, description (short), price, quantity, image_url, etc. Then continue with concise guidance if needed.",
                "phone_allowlist": "If a website is iframe-friendly and relevant (e.g., payment or settings pages), add it to the persistent allowlist by returning a toolCalls entry with type 'phone_allowlist_add' and payload {url}. Prefer https URLs.",
                "phone_create_template": "When no existing template fits, you may define a new minimal template. Return a toolCalls entry with type 'phone_create_template' and payload {name, html, css?, overwrite?}. Keep HTML small, use {{variable}} placeholders, and avoid external assets. After creation, render it using 'phone_template'."
            },
            "variables": {}
        }
    )
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


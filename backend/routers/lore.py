from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, String
from typing import List, Optional, Any
import json
from pathlib import Path
import os
import time
from collections import deque, OrderedDict
import asyncio
import logging

# Configure logging
logger = logging.getLogger(__name__)

from ..database import get_db
from ..models import Lorebook, LoreEntry, Character
from ..hybrid_search import HybridSearch
from ..rag_service import get_rag_service

# Sliding-window rate limiter with LRU expiration
class RateLimiter:
    def __init__(self, requests_per_minute: int = 30, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.requests: "OrderedDict[str, deque[float]]" = OrderedDict()
        self.lock = asyncio.Lock()

    async def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        async with self.lock:
            bucket = self.requests.get(client_key)
            if bucket is None:
                bucket = deque()
                self.requests[client_key] = bucket

            # Remove timestamps outside the window
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            if len(bucket) < self.requests_per_minute:
                bucket.append(now)
                self.requests.move_to_end(client_key)
                self._expire_clients(now)
                return True

            return False

    def _expire_clients(self, now: float) -> None:
        # Remove clients with no activity within the window using LRU order
        for key, bucket in list(self.requests.items()):
            if bucket and now - bucket[-1] <= self.window_seconds:
                break
            del self.requests[key]

rate_limiter = RateLimiter()

# Context injection recursion control
context_injection_depth = 0
max_recursion_depth = 5

async def check_rate_limit(request: Request):
    client_ip = request.client.host  # Assuming FastAPI request provides client
    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")
    return True

router = APIRouter(prefix="/lorebooks", tags=["lore"])

# Helper function to get public directory
def get_public_dir() -> Path:
    here = Path(__file__).resolve().parent.parent
    return (here / "public").resolve()

# Lorebooks CRUD endpoints

@router.get("/")
async def list_lorebooks(db: Session = Depends(get_db)) -> dict:
    """List all lorebooks with their entry counts"""
    lorebooks = db.query(Lorebook).options(
        joinedload(Lorebook.entries)
    ).all()

    return {
        "lorebooks": [
            {
                "id": lb.id,
                "name": lb.name,
                "description": lb.description,
                "entry_count": len(lb.entries),
                "created_at": lb.created_at.isoformat(),
                "updated_at": lb.updated_at.isoformat()
            }
            for lb in lorebooks
        ]
    }

@router.post("/")
async def create_lorebook(lorebook_data: dict, db: Session = Depends(get_db)):
    """Create a new lorebook"""
    lorebook = Lorebook(
        name=lorebook_data["name"],
        description=lorebook_data.get("description", ""),
    )
    db.add(lorebook)
    db.commit()
    db.refresh(lorebook)

    # Process initial entries if provided
    if "entries" in lorebook_data:
        for entry_data in lorebook_data["entries"]:
            entry = LoreEntry(
                lorebook_id=lorebook.id,
                title=entry_data.get("title", entry_data.get("keyword", "")),
                content=entry_data["content"],
                keywords=entry_data.get("keywords", [entry_data.get("keyword", "")] if entry_data.get("keyword") else []),
                secondary_keywords=entry_data.get("secondary_keywords", []),
                logic=entry_data.get("logic", "AND ANY"),
                trigger=entry_data.get("trigger", 100.0),
                order=entry_data.get("order", 0.0)
            )
            db.add(entry)

    db.commit()
    return {
        "id": lorebook.id,
        "name": lorebook.name,
        "description": lorebook.description,
        "created_at": lorebook.created_at.isoformat()
    }

# Lore search and context injection API - moved before dynamic routes

@router.get("/search")
async def search_lorebooks(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, description="Maximum number of results"),
    use_rag: bool = Query(False, description="Enable RAG-powered semantic search"),
    db: Session = Depends(get_db)
):
    """Search lore entries with advanced keyword matching or RAG-powered search"""
    if use_rag:
        # Use RAG-powered semantic search
        query_terms = [term.strip().lower() for term in (q or "").split() if term.strip()]
        if not query_terms:
            return {"results": [], "total_found": 0}

        logger.info(f"[CoolChat] Using RAG search for query: '{q}' with use_rag=true")

        try:
            hybrid_search = HybridSearch()
            results = await hybrid_search.search(q, db, limit)
            total_found = len(results)

            logger.info(f"[CoolChat] RAG search completed: found {total_found} results")
            return {"results": results, "total_found": total_found}

        except Exception as e:
            logger.error(f"[CoolChat] RAG search failed, falling back to keyword search: {e}")
            # Fall back to keyword search on error

    # Keyword-based search (fallback or when use_rag=False)
    logger.info(f"[CoolChat] Using keyword search for query: '{q}' with use_rag=false")
    query_terms = [term.strip().lower() for term in (q or "").split() if term.strip()]

    if not query_terms:
        return {"results": [], "total_found": 0}

    results = []

    # Build database filter conditions for content and keywords
    content_filters = [LoreEntry.content.ilike(f"%{term}%") for term in query_terms]
    keyword_filters = [LoreEntry.keywords.cast(String).ilike(f"%{term}%") for term in query_terms]
    secondary_keyword_filters = [LoreEntry.secondary_keywords.cast(String).ilike(f"%{term}%") for term in query_terms]

    # Combine filters - entries that match any term in content or keywords
    combined_filters = content_filters + keyword_filters + secondary_keyword_filters

    query = db.query(LoreEntry).options(joinedload(LoreEntry.lorebook)).filter(or_(*combined_filters))

    # Load candidates (limit to a reasonable number to avoid memory issues, e.g., 1000 candidates max)
    candidates = query.limit(1000).all()

    for entry in candidates:
        score = 0
        matched = False

        # Prepare keywords for matching
        primary_kw = [kw.lower() if kw else "" for kw in entry.keywords or []]
        secondary_kw = [kw.lower() if kw else "" for kw in entry.secondary_keywords or []]
        all_keywords = primary_kw + secondary_kw
        content_lower = entry.content.lower()

        # Enhanced scoring based on logic settings
        logic = entry.logic.upper() if entry.logic else "AND ANY"

        # Check for exact keyword matches first (including spaces)
        exact_keyword_match = any(term == kw for term in query_terms for kw in all_keywords)
        if exact_keyword_match:
            score += 30 if any(term == kw for term in query_terms for kw in primary_kw) else 20
            matched = True
        elif logic == "AND ANY":
            # Matches if any search term is found in keywords or content
            for term in query_terms:
                if (any(term in kw for kw in all_keywords) or term in content_lower):
                    score += 20 if any(term in kw for kw in primary_kw) else 10
                    matched = True
                    break

        elif logic == "AND ALL":
            # All query terms must be found (at least in secondary keywords)
            all_matched = True
            primary_boost = 0
            for term in query_terms:
                term_matched = (any(term in kw for kw in all_keywords) or term in content_lower)
                if not term_matched:
                    all_matched = False
                    break
                if any(term in kw for kw in primary_kw):
                    primary_boost += 10
            if all_matched:
                score += 30 + primary_boost
                matched = True

        elif logic == "NOT ANY":
            # Matches only if none of the query terms are found
            no_matches = True
            for term in query_terms:
                if any(term in kw for kw in all_keywords) or term in content_lower:
                    no_matches = False
                    break
            if no_matches:
                score += 15
                matched = True

        elif logic == "NOT ALL":
            # Matches if at least one query term is NOT found
            some_not_found = False
            for term in query_terms:
                if not (any(term in kw for kw in all_keywords) or term in content_lower):
                    some_not_found = True
                    score += 15
                    matched = True
                    break

        # Additional scoring for content matches
        if matched:
            # Exact phrase match gets highest score
            query_lower = (q or "").lower()
            if query_lower and query_lower in content_lower:
                score += 25

            # Apply trigger percentage (higher means more likely to be included)
            trigger_multiplier = entry.trigger / 100.0 if entry.trigger else 1.0
            score *= trigger_multiplier

            results.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "lorebook_name": entry.lorebook.name,
                "lorebook_id": entry.lorebook.id,
                "keywords": entry.keywords,
                "secondary_keywords": entry.secondary_keywords,
                "logic": entry.logic,
                "trigger": entry.trigger,
                "order": entry.order,
                "score": score,
                "matched_terms": query_terms  # Useful for debugging
            })

    # Sort by score, then by order (higher order = higher priority)
    results.sort(key=lambda x: (-x["score"], -x["order"]), reverse=False)
    return {"results": results[:limit], "total_found": len(results)}
@router.post("/generate_embeddings", status_code=200)
async def generate_embeddings(db: Session = Depends(get_db)):
    """Generate embeddings for all lore entries without them"""
    logger.info("[CoolChat] Starting embedding generation for all lore entries")

    start_time = time.time()
    successful_count = 0
    failed_count = 0
    skipped_count = 0

    try:
        # Get all entries without embeddings
        entries_without_embeddings = db.query(LoreEntry).filter(
            LoreEntry.embedding.is_(None) | (LoreEntry.embedding == "")
        ).all()

        logger.info(f"[CoolChat] Found {len(entries_without_embeddings)} entries without embeddings")

        if not entries_without_embeddings:
            logger.info("[CoolChat] No entries need embedding generation")
            return {
                "message": "All entries already have embeddings",
                "total_entries": db.query(LoreEntry).count(),
                "entries_processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "elapsed_time": 0.0
            }

        # Get RAG configuration info
        rag_service = get_rag_service(db)
        try:
            rag_config = rag_service.config
            logger.info(f"[CoolChat] Using RAG provider: {rag_config.provider}")
        except Exception as config_e:
            logger.warning(f"[CoolChat] Could not retrieve RAG config: {config_e}")

        logger.info(f"[CoolChat] Starting batch processing of {len(entries_without_embeddings)} entries...")
        logger.info(f"[CoolChat] Progress updates will be logged every 10 entries")

        # Generate embeddings in batches
        batch_size = 10  # Process in smaller batches to avoid timeout
        processed_count = 0

        for i in range(0, len(entries_without_embeddings), batch_size):
            batch = entries_without_embeddings[i:i + batch_size]
            batch_start_time = time.time()

            try:
                logger.info(f"[CoolChat] Processing batch {i//batch_size + 1}/{(len(entries_without_embeddings)-1)//batch_size + 1} ({len(batch)} entries)")
                await rag_service.batch_process_lore_entries(batch)

                successful_count += len(batch)
                processed_count += len(batch)
                batch_elapsed = time.time() - batch_start_time

                logger.info(f"[CoolChat] ✓ Batch completed in {batch_elapsed:.2f}s - Success: {successful_count}, Processed: {processed_count}/{len(entries_without_embeddings)}")

                # Progress update every 10 entries (or every batch with our batch_size)
                if processed_count % 10 == 0 or processed_count == len(entries_without_embeddings):
                    elapsed = time.time() - start_time
                    remaining = len(entries_without_embeddings) - processed_count
                    if processed_count > 0 and elapsed > 0:
                        rate = processed_count / elapsed
                        eta = remaining / rate if rate > 0 else 0
                        logger.info(",.1f")
            except Exception as batch_e:
                failed_count += len(batch)
                processed_count += len(batch)
                logger.error(f"[CoolChat] ✗ Batch failed - Failed: {failed_count}, Error: {batch_e}")

        total_elapsed = time.time() - start_time
        skipped_count = len(entries_without_embeddings) - (successful_count + failed_count)

        logger.info(f"[CoolChat] ===== FINAL SUMMARY =====")
        logger.info(f"[CoolChat] Total entries processed: {len(entries_without_embeddings)}")
        logger.info(f"[CoolChat] ✓ Successful: {successful_count}")
        logger.info(f"[CoolChat] ✗ Failed: {failed_count}")
        logger.info(".2f")
        logger.info(".3f" if total_elapsed > 0 else 0)
        logger.info("[CoolChat] Embedding generation completed")

        return {
            "message": "Embeddings generated successfully",
            "total_entries": db.query(LoreEntry).count(),
            "entries_processed": len(entries_without_embeddings),
            "successful": successful_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "elapsed_time": total_elapsed
        }

    except Exception as e:
        total_elapsed = time.time() - start_time
        logger.error(f"[CoolChat] CRITICAL ERROR in embedding generation: {e}")
        logger.error(f"[CoolChat] Processing stopped after {total_elapsed:.2f} seconds")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@router.get("/{lorebook_id}")
async def get_lorebook(lorebook_id: int, db: Session = Depends(get_db)):
    """Get a specific lorebook with all its entries"""
    lorebook = db.query(Lorebook).options(
        joinedload(Lorebook.entries)
    ).filter(Lorebook.id == lorebook_id).first()

    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    return {
        "id": lorebook.id,
        "name": lorebook.name,
        "description": lorebook.description,
        "created_at": lorebook.created_at.isoformat(),
        "updated_at": lorebook.updated_at.isoformat(),
        "entries": [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content,
                "keywords": entry.keywords,
                "secondary_keywords": entry.secondary_keywords,
                "logic": entry.logic,
                "trigger": entry.trigger,
                "order": entry.order,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            }
            for entry in lorebook.entries
        ]
    }

@router.put("/{lorebook_id}")
async def update_lorebook(lorebook_id: int, updates: dict, db: Session = Depends(get_db)):
    """Update a lorebook"""
    lorebook = db.query(Lorebook).filter(Lorebook.id == lorebook_id).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    if "name" in updates:
        lorebook.name = updates["name"]
    if "description" in updates:
        lorebook.description = updates["description"]
    if "entry_ids" in updates:
        # Update entry order - could implement more complex ordering logic here
        pass

    db.commit()
    db.refresh(lorebook)
    return {"message": "Lorebook updated successfully"}

@router.delete("/{lorebook_id}")
async def delete_lorebook(lorebook_id: int, db: Session = Depends(get_db)):
    """Delete a lorebook and all its entries"""
    lorebook = db.query(Lorebook).filter(Lorebook.id == lorebook_id).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    db.delete(lorebook)
    db.commit()
    return {"message": "Lorebook deleted successfully"}

# Individual Lore Entries CRUD

@router.post("/entries")
async def create_lore_entry(entry_data: dict, db: Session = Depends(get_db)):
    """Create a new lore entry"""
    # Validate that lorebook exists
    lorebook = db.query(Lorebook).filter(Lorebook.id == entry_data["lorebook_id"]).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    entry = LoreEntry(
        lorebook_id=entry_data["lorebook_id"],
        title=entry_data.get("title", ""),
        content=entry_data["content"],
        keywords=entry_data.get("keywords", []),
        secondary_keywords=entry_data.get("secondary_keywords", []),
        logic=entry_data.get("logic", "AND ANY"),
        trigger=entry_data.get("trigger", 100.0),
        order=entry_data.get("order", 0.0)
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "lorebook_id": entry.lorebook_id,
        "title": entry.title,
        "content": entry.content,
        "keywords": entry.keywords,
        "secondary_keywords": entry.secondary_keywords,
        "logic": entry.logic,
        "trigger": entry.trigger,
        "order": entry.order,
        "created_at": entry.created_at.isoformat()
    }

@router.put("/entries/{entry_id}")
async def update_lore_entry(entry_id: int, updates: dict, db: Session = Depends(get_db)):
    """Update a lore entry"""
    print(f"[CoolChat] Router updating lore entry {entry_id} with updates: {list(updates.keys())}")
    entry = db.query(LoreEntry).filter(LoreEntry.id == entry_id).first()
    if not entry:
        print(f"[CoolChat] Router error: Lore entry {entry_id} not found")
        raise HTTPException(status_code=404, detail="Lore entry not found")

    # Update fields
    if "title" in updates:
        entry.title = updates["title"]
        print(f"[CoolChat] Router updating title to: {updates['title']}")
    if "content" in updates:
        entry.content = updates["content"]
        print(f"[CoolChat] Router updating content length: {len(updates.get('content', ''))}")
    if "keywords" in updates:
        entry.keywords = updates["keywords"]
        print(f"[CoolChat] Router updating keywords: {updates['keywords']}")
    if "secondary_keywords" in updates:
        entry.secondary_keywords = updates["secondary_keywords"]
        print(f"[CoolChat] Router updating secondary_keywords: {updates['secondary_keywords']}")
    if "logic" in updates:
        entry.logic = updates["logic"]
        print(f"[CoolChat] Router updating logic: {updates['logic']}")
    if "trigger" in updates:
        entry.trigger = updates["trigger"]
        print(f"[CoolChat] Router updating trigger: {updates['trigger']}")
    if "order" in updates:
        entry.order = updates["order"]
        print(f"[CoolChat] Router updating order: {updates['order']}")

    db.commit()
    db.refresh(entry)
    print(f"[CoolChat] Router successfully updated lore entry {entry_id}")
    return {"message": "Lore entry updated successfully"}

@router.delete("/entries/{entry_id}")
async def delete_lore_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a lore entry"""
    entry = db.query(LoreEntry).filter(LoreEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Lore entry not found")

    db.delete(entry)
    db.commit()
    return {"message": "Lore entry deleted successfully"}

# Import/Export functionality

@router.post("/import")
async def import_lorebook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import a lorebook from JSON file"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    try:
        content = await file.read()
        lorebook_data = json.loads(content.decode('utf-8'))

        # Validate structure
        if not isinstance(lorebook_data, dict) or "entries" not in lorebook_data:
            raise HTTPException(status_code=400, detail="Invalid lorebook format")

        # Create lorebook - use filename if available
        filename = file.filename
        default_name = filename.replace('.json', '') if filename else "Imported Lorebook"
        lorebook_name = lorebook_data.get("name", default_name)

        lorebook = Lorebook(
            name=lorebook_name,
            description=lorebook_data.get("description", "")
        )
        db.add(lorebook)
        db.commit()
        db.refresh(lorebook)

        # Process entries - handle both array and object formats
        entries = lorebook_data["entries"]
        if isinstance(entries, dict):
            # Convert object format like {"0": {...}, "1": {...}} to list format
            entries = list(entries.values())

        # Add entries
        for entry_data in entries:
            # Handle SillyTavern format conversion
            title = entry_data.get("title", entry_data.get("comment", ""))
            content = entry_data["content"]
            keywords = entry_data.get("keywords", entry_data.get("key", []))
            secondary_keywords = entry_data.get("secondary_keywords", entry_data.get("keysecondary", []))
            logic = "AND ANY"  # Default logic
            if entry_data.get("selective", True):
                logic = "AND ANY"
            elif "logic" in entry_data:
                # Could map selectiveLogic numeric values here if needed
                logic = "AND ANY"
            trigger = entry_data.get("trigger", entry_data.get("probability", 100))
            order = entry_data.get("order", entry_data.get("depth", 4))

            entry = LoreEntry(
                lorebook_id=lorebook.id,
                title=title,
                content=content,
                keywords=keywords,
                secondary_keywords=secondary_keywords,
                logic=logic,
                trigger=trigger,
                order=order
            )
            db.add(entry)

        db.commit()
        return {"message": "Lorebook imported successfully", "id": lorebook.id}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# Character-Lorebook relationship management

@router.post("/characters/{character_id}/lorebooks/{lorebook_id}")
async def link_character_to_lorebook(character_id: int, lorebook_id: int, db: Session = Depends(get_db)):
    """Link a character to a lorebook"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    lorebook = db.query(Lorebook).filter(Lorebook.id == lorebook_id).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    # Check if already linked
    if lorebook in character.lorebooks:
        return {"message": "Character already linked to this lorebook"}

    character.lorebooks.append(lorebook)
    db.commit()
    return {"message": "Character linked to lorebook successfully"}

@router.delete("/characters/{character_id}/lorebooks/{lorebook_id}")
async def unlink_character_from_lorebook(character_id: int, lorebook_id: int, db: Session = Depends(get_db)):
    """Unlink a character from a lorebook"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    lorebook = db.query(Lorebook).filter(Lorebook.id == lorebook_id).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail="Lorebook not found")

    if lorebook not in character.lorebooks:
        raise HTTPException(status_code=404, detail="Character not linked to this lorebook")

    character.lorebooks.remove(lorebook)
    db.commit()
    return {"message": "Character unlinked from lorebook successfully"}

@router.get("/characters/{character_id}/lorebooks")
async def get_character_lorebooks(character_id: int, db: Session = Depends(get_db)):
    """Get all lorebooks linked to a character"""
    character = db.query(Character).options(joinedload(Character.lorebooks)).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return {
        "character_id": character.id,
        "character_name": character.name,
        "lorebooks": [
            {
                "id": lb.id,
                "name": lb.name,
                "description": lb.description,
                "entry_count": len(lb.entries),
                "created_at": lb.created_at.isoformat()
            } for lb in character.lorebooks
        ]
    }

# Legacy lore routes (for compatibility)

@router.get("/legacy/lore")
async def list_lore_entries(db: Session = Depends(get_db)) -> List[dict]:
    """Legacy endpoint for backward compatibility with tests"""
    entries = db.query(LoreEntry).options(joinedload(LoreEntry.lorebook)).all()
    return [
        {
            "id": entry.id,
            "keyword": entry.keywords[0] if entry.keywords else "",
            "content": entry.content
        }
        for entry in entries
    ]

@router.post("/legacy/lore")
async def create_lore_entry_legacy(entry_data: dict, db: Session = Depends(get_db)):
    """Legacy post route for backward compatibility"""
    # Create or get default lorebook
    lorebook = db.query(Lorebook).first()
    if not lorebook:
        lorebook = Lorebook(name="Default Lorebook", description="Auto-created")
        db.add(lorebook)
        db.commit()
        db.refresh(lorebook)

    entry = LoreEntry(
        lorebook_id=lorebook.id,
        title=entry_data.get("keyword", ""),
        content=entry_data["content"],
        keywords=[entry_data.get("keyword")] if entry_data.get("keyword") else []
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "keyword": entry_data.get("keyword", ""),
        "content": entry.content
    }

# Bulk operations API

@router.post("/entries/bulk")
async def bulk_create_entries(bulk_data: dict, db: Session = Depends(get_db)):
    """Create multiple lore entries at once"""
    if not isinstance(bulk_data.get("entries"), list):
        raise HTTPException(status_code=400, detail="entries must be a list")

    entries = bulk_data["entries"]
    if not entries:
        raise HTTPException(status_code=400, detail="entries list cannot be empty")

    # Require explicit lorebook_id for safety
    if "lorebook_id" not in bulk_data:
        raise HTTPException(status_code=400, detail="lorebook_id is required")
    lorebook_id = bulk_data["lorebook_id"]
    if not isinstance(lorebook_id, int) or lorebook_id <= 0:
        raise HTTPException(status_code=400, detail="lorebook_id must be a positive integer")

    # Validate lorebook exists
    lorebook = db.query(Lorebook).filter(Lorebook.id == lorebook_id).first()
    if not lorebook:
        raise HTTPException(status_code=404, detail=f"Lorebook {lorebook_id} not found")

    # Safeguard: limit bulk size to prevent abuse
    max_bulk_size = 100
    if len(entries) > max_bulk_size:
        raise HTTPException(status_code=400, detail=f"Bulk operation limited to {max_bulk_size} entries")

    created_entries = []

    for entry_data in entries:
        # Validate entry data
        if not isinstance(entry_data.get("content"), str) or not entry_data["content"].strip():
            raise HTTPException(status_code=400, detail="Each entry must have non-empty content")

        entry = LoreEntry(
            lorebook_id=lorebook.id,
            title=entry_data.get("title", ""),
            content=entry_data["content"],
            keywords=entry_data.get("keywords", []),
            secondary_keywords=entry_data.get("secondary_keywords", []),
            logic=entry_data.get("logic", "AND ANY"),
            trigger=entry_data.get("trigger", 100.0),
            order=entry_data.get("order", 0.0)
        )
        db.add(entry)
        created_entries.append(entry)

    db.commit()

    # Refresh to get IDs
    for entry in created_entries:
        db.refresh(entry)

    return {
        "message": f"Created {len(created_entries)} lore entries",
        "entries": [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content,
                "lorebook_id": entry.lorebook_id
            } for entry in created_entries
        ]
    }

# Context injection API for system prompts

@router.post("/inject_context")
async def inject_lore_context(request_data: dict, db: Session = Depends(get_db)):
    """Generate system prompt with relevant lore entries for a conversation"""
    global context_injection_depth
    context_injection_depth += 1
    try:
        if context_injection_depth > max_recursion_depth:
            raise HTTPException(status_code=400, detail="Context injection recursion depth exceeded")

        session_id = request_data.get("session_id")
        max_tokens = request_data.get("max_tokens", 1000)
        recent_text = request_data.get("recent_text", "")

        lorebook_ids = request_data.get("lorebook_ids", [])

        # Get active lorebooks if none specified
        if not lorebook_ids:
            # Try to get from character if session has one
            if session_id:
                # This could be enhanced to get character ID from session
                pass

        # Search for relevant entries
        search_results = await search_lorebooks(q=recent_text, limit=20, db=db)

        # Select entries that fit within token budget
        selected_entries = []
        total_tokens = 0
        max_tokens_per_entry = 200

        for result in search_results["results"]:
            entry_tokens = len(result["content"]) // 4  # Rough estimate
            if total_tokens + entry_tokens > max_tokens:
                continue

            if entry_tokens > max_tokens_per_entry:
                # Truncate content if too long
                content_tokens = max_tokens_per_entry * 4
                result["content"] = result["content"][:content_tokens] + "..."
                entry_tokens = max_tokens_per_entry

            selected_entries.append(result)
            total_tokens += entry_tokens

        # Format as context injection
        context_parts = []
        for entry in selected_entries:
            context_parts.append(f"[{entry['title'] or 'Lore'}] {entry['content']}")

        context_text = "\n\n".join(context_parts)

        return {
            "context": context_text,
            "entry_count": len(selected_entries),
            "estimated_tokens": total_tokens,
            "entries": [
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "lorebook_name": entry["lorebook_name"],
                    "score": entry["score"]
                } for entry in selected_entries
            ]
        }
    finally:
        context_injection_depth -= 1
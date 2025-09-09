#!/usr/bin/env python3
"""Hybrid Search Implementation for RAG System"""

import asyncio
import base64
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from .models import LoreEntry
from .rag_service import EmbeddingService
from .database import SessionLocal


@dataclass
class SearchResult:
    """Structure for search results"""
    entry: LoreEntry
    keyword_score: float
    semantic_score: float
    hybrid_score: float
    matched_terms: List[str]


class HybridSearch:
    """Hybrid search combining keyword and semantic similarity"""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

    async def search(self, query: str, db_session: Optional[Session] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search with extensive logging
        Returns results in format compatible with existing lore search API
        """
        print(f"🔍 HYBRID SEARCH: '{query}' - Limit: {limit}")

        # Step 1: Initialize components
        await self.embedding_service._ensure_initialized()
        config = self.embedding_service.config
        print(f"📊 RAG Config: Provider={config.provider}, KW Weight={config.keyword_weight}, "
              f"Semantic Weight={config.semantic_weight}, Top-K={config.top_k_candidates}")

        try:
            # Step 2: Generate query embedding
            print("🔄 Generating query embedding...")
            query_embedding = await self.embedding_service.generate_embedding(query)
            print("✅ Query embedding generated successfully")

            # Step 3: Get keyword candidates
            print(f"🔍 Getting keyword candidates (top {config.top_k_candidates})...")
            keyword_candidates = await self._get_keyword_candidates(query, db_session, config.top_k_candidates)
            print(f"✅ Found {len(keyword_candidates)} keyword candidates")

            if not keyword_candidates:
                print("⏭️  No keyword candidates found, returning empty results")
                return []

            # Step 4: Calculate hybrid scores
            print("🧮 Calculating hybrid scores...")
            search_results = await self._calculate_hybrid_scores(
                keyword_candidates, query_embedding, config
            )

            # Step 5: Sort and prepare final results
            search_results.sort(key=lambda x: x.hybrid_score, reverse=True)
            top_results = search_results[:limit]

            # Log results
            print(f"🏆 TOP {len(top_results)} RESULTS:")
            for i, result in enumerate(top_results, 1):
                entry = result.entry
                print(f"   #{i} - ID:{entry.id} | KW:{result.keyword_score:.3f} | "
                      f"SEM:{result.semantic_score:.3f} | HYBRID:{result.hybrid_score:.3f}")
                print(f"       Title: '{entry.title or 'Untitled'}'")
                print(f"       Content: '{entry.content[:100]}...'")

            # Convert to API format
            final_results = []
            for result in top_results:
                entry = result.entry
                final_results.append({
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
                    "score": result.hybrid_score,
                    "keyword_score": result.keyword_score,
                    "semantic_score": result.semantic_score,
                    "matched_terms": result.matched_terms
                })

            print(f"✅ Hybrid search completed successfully - Returning {len(final_results)} results")
            return final_results

        except Exception as e:
            print(f"❌ Error in hybrid search: {e}")
            print("⏭️  Falling back to keyword-only search")
            return await self._keyword_search_fallback(query, db_session, limit)

    async def _get_keyword_candidates(self, query: str, db_session: Optional[Session], limit: int) -> List[LoreEntry]:
        """Get initial candidates using keyword search"""
        from sqlalchemy import or_
        from sqlalchemy.orm import joinedload

        if db_session:
            db = db_session
            close = False
        elif self.embedding_service._db:
            db = self.embedding_service._db
            close = False
        else:
            db = SessionLocal()
            close = True
        try:
            query_terms = [term.strip().lower() for term in query.split() if term.strip()]

            if not query_terms:
                return []

            # Build keyword filters
            content_filters = [LoreEntry.content.ilike(f"%{term}%") for term in query_terms]
            keyword_filters = [LoreEntry.keywords.cast(str).ilike(f"%{term}%") for term in query_terms]
            secondary_keyword_filters = [LoreEntry.secondary_keywords.cast(str).ilike(f"%{term}%") for term in query_terms]

            combined_filters = content_filters + keyword_filters + secondary_keyword_filters

            entries = db.query(LoreEntry).options(joinedload(LoreEntry.lorebook)).filter(
                or_(*combined_filters)
            ).limit(limit).all()

            # Add keyword scores to entries
            for entry in entries:
                entry.keyword_score = self._calculate_keyword_score(entry, query_terms)

            return entries

        finally:
            if close:
                db.close()

    def _calculate_keyword_score(self, entry: LoreEntry, query_terms: List[str]) -> float:
        """Calculate keyword relevance score for an entry"""
        score = 0
        primary_keywords = [kw.lower() for kw in (entry.keywords or [])]
        secondary_keywords = [kw.lower() for kw in (entry.secondary_keywords or [])]
        content_lower = entry.content.lower()

        for term in query_terms:
            # Primary keyword matches
            if any(term in kw for kw in primary_keywords):
                score += 20
            # Secondary keyword matches
            elif any(term in kw for kw in secondary_keywords):
                score += 10
            # Content matches
            elif term in content_lower:
                score += 5

        # Apply trigger multiplier
        trigger_multiplier = entry.trigger / 100.0 if entry.trigger else 1.0
        return score * trigger_multiplier

    async def _calculate_hybrid_scores(self, candidates: List[LoreEntry],
                                      query_embedding: str, config) -> List[SearchResult]:
        """Calculate hybrid keyword + semantic scores"""
        query_vector = self.embedding_service.decode_embedding(query_embedding)
        semantic_scores = {}
        entries_with_embeddings = 0

        for candidate in candidates:
            # Calculate semantic score with dimension validation
            if candidate.embedding:
                if candidate.embedding_dimensions == config.dimensions:
                    entries_with_embeddings += 1
                    entry_vector = self.embedding_service.decode_embedding(candidate.embedding)
                    similarity = self.embedding_service.cosine_similarity(query_vector, entry_vector)
                    semantic_score = max(0, similarity)  # Ensure non-negative
                elif candidate.embedding_dimensions == len(query_vector):
                    # Allow backward compatibility: use the candidate's dimension if it matches query
                    print(f"ℹ️  Using backward-compatible embedding for entry {candidate.id}: "
                          f"stored_dimensions={candidate.embedding_dimensions} (config expects {config.dimensions})")
                    entries_with_embeddings += 1
                    entry_vector = self.embedding_service.decode_embedding(candidate.embedding)
                    similarity = self.embedding_service.cosine_similarity(query_vector, entry_vector)
                    semantic_score = max(0, similarity)  # Ensure non-negative
                else:
                    # Complete dimension mismatch - skip this entry
                    print(f"⚠️  Skipping entry {candidate.id} due to dimension mismatch: "
                          f"stored={candidate.embedding_dimensions}, query={len(query_vector)}, config={config.dimensions}")
                    semantic_score = 0.0
            else:
                semantic_score = 0.0

            semantic_scores[candidate.id] = semantic_score

        print(f"📈 Semantic analysis complete:")
        print(f"   - Entries with embeddings: {entries_with_embeddings}/{len(candidates)}")
        print(f"   - Average semantic score: {sum(semantic_scores.values())/len(semantic_scores):.3f}")

        # Calculate hybrid scores
        search_results = []
        for candidate in candidates:
            keyword_score = candidate.keyword_score
            semantic_score = semantic_scores[candidate.id]

            # Apply weights
            hybrid_score = (config.keyword_weight * keyword_score +
                          config.semantic_weight * semantic_score)

            search_results.append(SearchResult(
                entry=candidate,
                keyword_score=keyword_score,
                semantic_score=semantic_score,
                hybrid_score=hybrid_score,
                matched_terms=candidate.content.lower().split()[:5]  # Approximate
            ))

        return search_results

    async def _keyword_search_fallback(self, query: str, db_session: Optional[Session], limit: int) -> List[Dict[str, Any]]:
        """Fallback keyword-only search when embeddings fail"""
        print("🔍 Performing keyword-only search fallback")
        candidates = await self._get_keyword_candidates(query, db_session, limit * 2)

        results = []
        for candidate in candidates[:limit]:
            results.append({
                "id": candidate.id,
                "title": candidate.title,
                "content": candidate.content,
                "lorebook_name": candidate.lorebook.name,
                "lorebook_id": candidate.lorebook.id,
                "keywords": candidate.keywords,
                "secondary_keywords": candidate.secondary_keywords,
                "logic": candidate.logic,
                "trigger": candidate.trigger,
                "order": candidate.order,
                "score": candidate.keyword_score,
                "keyword_score": candidate.keyword_score,
                "semantic_score": 0.0,
                "matched_terms": query.split()
            })

        print(f"✅ Keyword fallback search returned {len(results)} results")
        return results
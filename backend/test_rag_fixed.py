#!/usr/bin/env python3
"""RAG Testing Script - Set up credentials and test hybrid search"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from config import config
from rag_service import EmbeddingService, get_rag_service
from models import RAGConfig
from database import SessionLocal

async def test_credentials():
    """Test if the configured credentials work"""
    print("🔍 Testing RAG Provider Credentials...")
    print(f"📊 Provider: {config.RAG_PROVIDER}")

    try:
        if config.RAG_PROVIDER == "ollama":
            if not config.OLLAMA_MODEL:
                print("❌ Ollama model not configured")
                return False
            print(f"🦙 Ollama URL: {config.OLLAMA_BASE_URL}")
            print(f"🤖 Ollama Model: {config.OLLAMA_MODEL}")

        elif config.RAG_PROVIDER == "gemini":
            if not config.GEMINI_API_KEY:
                print("❌ Gemini API key not configured")
                return False
            print(f"🔑 Gemini API Key: {config.GEMINI_API_KEY[:10]}...")
            print(f"🎯 Gemini Model: {config.GEMINI_MODEL}")

        print("✅ Provider credentials configured")

        # Test embedding generation
        service = get_rag_service()
        await service._ensure_initialized()
        print(f"🔄 Provider: {service._provider.provider_name}")

        test_text = "Hello, this is a test for the RAG system."
        print(f"📝 Test text: '{test_text}'")

        embedding = await service.generate_embedding(test_text)
        print("✅ Embedding generated successfully")
        print(f"📏 Embedding length: {len(embedding)} bytes")

        # Decode to verify
        decoded = service.decode_embedding(embedding)
        print(f"📐 Vector dimensions: {len(decoded)}")

        return True

    except Exception as e:
        print(f"❌ Credential test failed: {e}")
        return False

async def generate_embeddings():
    """Generate embeddings for existing lore entries"""
    print("🤖 Generating embeddings for existing entries...")

    from models import LoreEntry
    from sqlalchemy import and_

    db = SessionLocal()
    try:
        # Find entries without embeddings
        entries_without_embeddings = db.query(LoreEntry).filter(
            and_(
                LoreEntry.content.is_not(None),
                LoreEntry.embedding.is_(None)
            )
        ).limit(5).all()  # Generate fewer for test

        if not entries_without_embeddings:
            print("✅ All entries already have embeddings")
            return

        print(f"📝 Found {len(entries_without_embeddings)} entries without embeddings")

        service = get_rag_service()
        await service._ensure_initialized()

        for i, entry in enumerate(entries_without_embeddings, 1):
            try:
                text = f"{entry.title or ''} {entry.content}".strip()
                print(f"🔄 [{i}/{len(entries_without_embeddings)}] Processing entry {entry.id}: '{text[:50]}...'")

                # Generate embedding
                embedding_b64 = await service.generate_embedding(text)

                # Update entry
                entry.embedding = embedding_b64
                entry.embedding_model = service.config.model
                entry.embedding_dimensions = service.config.dimensions
                entry.embedding_provider = config.RAG_PROVIDER
                entry.embedding_updated_at = db.func.now()

                print(f"✅ Generated embedding for entry {entry.id}")

            except Exception as e:
                print(f"❌ Failed to generate embedding for entry {entry.id}: {e}")

        db.commit()
        print(f"✅ Embedding generation complete")

    finally:
        db.close()

async def test_search():
    """Test search functionality"""
    print("🔍 Testing search...")

    test_queries = ["magic", "kingdom"]

    from hybrid_search import HybridSearch

    for query in test_queries:
        print(f"\n--- Testing Query: '{query}' ---")
        try:
            hybrid_search = HybridSearch(get_rag_service())
            results = await hybrid_search.search(query, limit=3)

            print(f"🎯 Found {len(results)} results")
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Untitled')
                score = result['score']
                print(f"  {i}. {title} | Score: {score:.2f}")

        except Exception as e:
            print(f"❌ Search failed for '{query}': {e}")

def show_current_status():
    """Show current database status"""
    print("📊 Current Database Status:")

    from models import LoreEntry, RAGConfig

    db = SessionLocal()
    try:
        # Count entries
        total_entries = db.query(LoreEntry).count()
        entries_with_embeddings = db.query(LoreEntry).filter(LoreEntry.embedding.is_not(None)).count()

        print(f"📚 Total lore entries: {total_entries}")
        if total_entries > 0:
            print(f"🧠 Entries with embeddings: {entries_with_embeddings} ({entries_with_embeddings/total_entries*100:.1f}%)")

        # Show config
        rag_config = db.query(RAGConfig).first()
        if rag_config:
            print("⚙️ RAG Configuration:")
            print(f"  Provider: {rag_config.provider}")
            print(f"  Ollama: {rag_config.ollama_base_url} / {rag_config.ollama_model}")
            print(f"  Gemini: {rag_config.gemini_model}")
            print(f"  Keyword Weight: {rag_config.keyword_weight}")
            print(f"  Semantic Weight: {rag_config.semantic_weight}")
            print(f"  Similarity Threshold: {rag_config.similarity_threshold}")
        else:
            print("⚠️ No RAG configuration found")

    finally:
        db.close()

async def main():
    """Main test function"""
    print("🤖 CoolChat RAG Testing Suite")
    print("=" * 50)

    if len(sys.argv) < 2:
        show_current_status()
        print("\n📋 Usage:")
        print("  python test_rag_fixed.py status")
        print("  python test_rag_fixed.py test_credentials")
        print("  python test_rag_fixed.py generate_embeddings")
        print("  python test_rag_fixed.py test_search")
        return

    command = sys.argv[1]

    if command == "status":
        show_current_status()
    elif command == "test_credentials":
        success = await test_credentials()
        if success:
            print("\n✅ Credentials test passed - RAG is ready!")
        else:
            print("\n❌ Credentials test failed - Check your configuration")
    elif command == "generate_embeddings":
        await generate_embeddings()
    elif command == "test_search":
        await test_search()
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())
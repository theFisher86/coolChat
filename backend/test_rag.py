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
from rag_providers import create_provider
from models import RAGConfig
from database import SessionLocal

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

            # Test basic connectivity (this will be implemented when we create the Ollama provider)

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

async def generate_sample_embeddings():
    """Generate embeddings for existing lore entries if none exist"""
    print("🤖 Generating sample embeddings ...")

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
        ).limit(10).all()  # Limit to 10 for testing

        if not entries_without_embeddings:
            print("✅ All entries already have embeddings")
            return

        print(f"📝 Found {len(entries_without_embeddings)} entries without embeddings")

        service = get_rag_service()
        await service._ensure_initialized()

        success_count = 0
        for i, entry in enumerate(entries_without_embeddings, 1):
            try:
                text = f"{entry.title or ''} {entry.content}".strip()
                print(f"🔄 [{i}/{len(entries_without_embeddings)}] Processing entry {entry.id}: '{text[:50]}...'")
                embedding = await service.generate_embedding(text)
                success_count += 1

            except Exception as e:
                print(f"❌ Failed to generate embedding for entry {entry.id}: {e}")

        print(f"✅ Generated embeddings for {success_count}/{len(entries_without_embeddings)} entries")

    finally:
        db.close()

async def test_hybrid_search():
    """Test the hybrid search functionality with sample queries"""
    print("🔍 Testing Hybrid Search...")

    test_queries = [
        "magic kingdoms",
        "elven archers",
        "dragon fighting",
        "crystal chambers",
        "mystical artifacts"
    ]

    for query in test_queries:
        print(f"\n--- Testing Query: '{query}' ---")
        try:
            from hybrid_search import HybridSearch

            hybrid_search = HybridSearch()
            results = await hybrid_search.search(query, limit=5)

            print(f"🎯 Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('title', 'Untitled')} | Score: {result['score']:.2f}")

        except Exception as e:
            print(f"❌ Search failed for '{query}': {e}")

async def show_current_status():
    """Show current database status"""
    print("📊 Current Database Status:")

    from models import LoreEntry, RAGConfig

    db = SessionLocal()
    try:
        # Count entries
        total_entries = db.query(LoreEntry).count()
        entries_with_embeddings = db.query(LoreEntry).filter(LoreEntry.embedding.is_not(None)).count()

        print(f"📚 Total lore entries: {total_entries}")
        print(f"🧠 Entries with embeddings: {entries_with_embeddings} ({entries_with_embeddings/total_entries*100:.1f}%)"        # Show config
        rag_config = db.query(RAGConfig).first()
        if rag_config:
            print("⚙️ RAG Configuration:"
            print(f"  Provider: {rag_config.provider}")
            print(f"  Ollama: {rag_config.ollama_base_url} / {rag_config.ollama_model}")
            print(f"  Gemini: {rag_config.gemini_model}")
            print(".2f"            print(".3f"            print(f"  Similarity Threshold: {rag_config.similarity_threshold}")
        else:
            print("⚠️ No RAG configuration found")

    finally:
        db.close()

def show_configuration_help():
    """Show help for configuration"""
    print("📋 RAG Configuration Help:")
    print()
    print("1️⃣ Create .env file in backend/ directory:")
    print("   cp .env.example .env")
    print()
    print("2️⃣ For Ollama (local models):")
    print("   OLLAMA_BASE_URL=http://localhost:11434")
    print("   OLLAMA_MODEL=nomic-embed-text:latest  # or mxbai-embed-large:latest")
    print("   RAG_PROVIDER=ollama")
    print()
    print("3️⃣ For Gemini (Google AI):")
    print("   GEMINI_API_KEY=your_api_key_here")
    print("   GEMINI_MODEL=models/text-embedding-004")
    print("   RAG_PROVIDER=gemini")
    print()
    print("4️⃣ Test configuration:")
    print("   python test_rag.py test_credentials")
    print()
    print("5️⃣ Generate embeddings for existing entries:")
    print("   python test_rag.py generate_embeddings")
    print()
    print("6️⃣ Test search (once embeddings exist):")
    print("   python test_rag.py test_search")

async def main():
    """Main test function"""
    print("🤖 CoolChat RAG Testing Suite")
    print("=" * 50)

    if len(sys.argv) < 2:
        await show_current_status()
        print()
        show_configuration_help()
        return

    command = sys.argv[1]

    if command == "status":
        await show_current_status()
    elif command == "test_credentials":
        success = await test_credentials()
        if success:
            print("✅ Credentials test passed")
        else:
            print("❌ Credentials test failed")
    elif command == "generate_embeddings":
        await generate_sample_embeddings()
    elif command == "test_search":
        await test_hybrid_search()
    else:
        print(f"❌ Unknown command: {command}")
        show_configuration_help()

if __name__ == "__main__":
    asyncio.run(main())
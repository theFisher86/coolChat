#!/usr/bin/env python3
"""Migration script to add RAG support to existing database"""

import os
import sys
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Text, Float, JSON, func
from sqlalchemy.orm import declarative_base

# Set up Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from database import SQLALCHEMY_DATABASE_URL


def migrate_rag_support():
    """Add RAG support to existing database"""

    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

    try:
        with engine.connect() as conn:
            # Check if columns already exist (safety check)
            result = conn.execute(text("""
                PRAGMA table_info(lore_entries);
            """))

            column_names = [row[1] for row in result.fetchall()]
            new_columns = ['embedding', 'embedding_model', 'embedding_dimensions',
                          'embedding_updated_at', 'embedding_provider']

            # Add new columns if they don't exist
            for column in new_columns:
                if column not in column_names:
                    print(f"[RAG Migration] Adding column {column} to lore_entries")
                    conn.execute(text(f"""
                        ALTER TABLE lore_entries ADD COLUMN {column} NULL;
                    """))
                    conn.commit()

            # Check if rag_config table exists
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='rag_config';
            """))

            if not result.fetchone():
                print("[RAG Migration] Creating rag_config table")
                # Create table manually since modified models might not be available
                conn.execute(text("""
                    CREATE TABLE rag_config (
                        id INTEGER PRIMARY KEY,
                        provider VARCHAR(50) NOT NULL DEFAULT 'ollama',
                        ollama_base_url VARCHAR(255) NOT NULL DEFAULT 'http://localhost:11434',
                        ollama_model VARCHAR(100) NOT NULL DEFAULT 'nomic-embed-text:latest',
                        gemini_api_key VARCHAR(255) NULL,
                        gemini_model VARCHAR(100) NOT NULL DEFAULT 'models/text-embedding-004',
                        top_k_candidates INTEGER NOT NULL DEFAULT 200,
                        keyword_weight REAL NOT NULL DEFAULT 0.6,
                        semantic_weight REAL NOT NULL DEFAULT 0.4,
                        similarity_threshold REAL NOT NULL DEFAULT 0.5,
                        batch_size INTEGER NOT NULL DEFAULT 32,
                        regenerate_on_content_update REAL NOT NULL DEFAULT 1,
                        embedding_dimensions INTEGER NOT NULL DEFAULT 384,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """))

                # Insert default configuration
                print("[RAG Migration] Inserting default RAG configuration")
                conn.execute(text("""
                    INSERT INTO rag_config (
                        provider, ollama_base_url, ollama_model, gemini_model,
                        top_k_candidates, keyword_weight, semantic_weight, similarity_threshold,
                        batch_size, regenerate_on_content_update, embedding_dimensions
                    ) VALUES (
                        'ollama', 'http://localhost:11434', 'nomic-embed-text:latest', 'models/text-embedding-004',
                        200, 0.6, 0.4, 0.5, 32, 1, 384
                    );
                """))

            conn.commit()
            print("[RAG Migration] Migration completed successfully")

    except Exception as e:
        print(f"[RAG Migration] Error during migration: {e}")
        raise


def verify_migration():
    """Verify the migration was successful"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

    try:
        with engine.connect() as conn:
            # Check lore_entries columns
            result = conn.execute(text("PRAGMA table_info(lore_entries);"))
            column_names = [row[1] for row in result.fetchall()]
            embedding_cols = ['embedding', 'embedding_model', 'embedding_dimensions',
                             'embedding_updated_at', 'embedding_provider']

            for col in embedding_cols:
                if col in column_names:
                    print(f"✓ lore_entries.{col} exists")
                else:
                    print(f"✗ lore_entries.{col} missing")

            # Check rag_config table
            result = conn.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='rag_config';
            """))

            if result.fetchone():
                print("✓ rag_config table exists")

                # Check default config
                result = conn.execute(text("SELECT COUNT(*) FROM rag_config;"))
                count = result.scalar()
                print(f"✓ rag_config has {count} record(s)")
            else:
                print("✗ rag_config table missing")

    except Exception as e:
        print(f"[RAG Migration] Error verifying migration: {e}")


if __name__ == "__main__":
    print("[CoolChat RAG] Starting RAG migration...")

    try:
        migrate_rag_support()
        print("[CoolChat RAG] Migration step completed")

        print("[CoolChat RAG] Verifying migration...")
        verify_migration()
        print("[CoolChat RAG] Migration verification completed")

        print("[CoolChat RAG] RAG support added successfully!")
        print("[CoolChat RAG] Note: Embedding generation for existing entries will be handled separately")

    except Exception as e:
        print(f"[CoolChat RAG] Migration failed: {e}")
        import traceback
        traceback.print_exc()
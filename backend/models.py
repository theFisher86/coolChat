from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func, Float, JSON, Table
from sqlalchemy.orm import relationship, declarative_base

# Define Base here to avoid circular imports
Base = declarative_base()


class CharacterCard(Base):
    __tablename__ = "character_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, unique=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    chat = relationship("ChatSession", back_populates="messages")


# Add messages relationship to ChatSession
ChatSession.messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


# Junction table for many-to-many relationship between characters and lorebooks
character_lorebook_association = Table(
    'character_lorebook_association',
    Base.metadata,
    Column('character_id', Integer, ForeignKey('characters.id')),
    Column('lorebook_id', Integer, ForeignKey('lorebooks.id'))
)


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Extended character fields for compatibility
    first_message = Column(Text, nullable=True)
    alternate_greetings = Column(JSON, nullable=True, default=list)
    scenario = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)
    mes_example = Column(Text, nullable=True)
    creator_notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    post_history_instructions = Column(Text, nullable=True)
    extensions = Column(JSON, nullable=True)

    # Image generation settings
    image_prompt_prefix = Column(Text, nullable=True)
    image_prompt_suffix = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    lorebooks = relationship(
        "Lorebook",
        secondary=character_lorebook_association,
        back_populates="characters",
        lazy="joined"
    )


class Lorebook(Base):
    __tablename__ = "lorebooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    entries = relationship("LoreEntry", back_populates="lorebook", cascade="all, delete-orphan")
    characters = relationship(
        "Character",
        secondary=character_lorebook_association,
        back_populates="lorebooks",
        lazy="joined"
    )


class LoreEntry(Base):
    __tablename__ = "lore_entries"

    id = Column(Integer, primary_key=True, index=True)
    lorebook_id = Column(Integer, ForeignKey("lorebooks.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)  # Optional title for UI
    content = Column(Text, nullable=False)

    # Keywords for search and matching
    keywords = Column(JSON, nullable=False, default=list)  # List of primary keywords
    secondary_keywords = Column(JSON, nullable=False, default=list)  # Less important keywords

    # Search and context settings
    logic = Column(String(50), nullable=False, default="AND ANY")  # AND ANY, AND ALL, NOT ANY, NOT ALL
    trigger = Column(Float, nullable=False, default=100.0)  # Percentage trigger (0-100)
    order = Column(Float, nullable=False, default=0.0)  # Sorting order

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Vector embeddings for RAG
    embedding = Column(Text, nullable=True)  # Base64 encoded embedding vector
    embedding_model = Column(String(100), nullable=True)  # Model identifier (e.g., "nomic-embed-text:latest")
    embedding_dimensions = Column(Integer, nullable=True)  # Vector dimensions for validation
    embedding_updated_at = Column(DateTime, nullable=True)  # Timestamp for embedding regeneration tracking
    embedding_provider = Column(String(50), nullable=True)  # Provider type ("ollama", "gemini", "openai")

    # Relationships
    lorebook = relationship("Lorebook", back_populates="entries", lazy="joined")


class Circuit(Base):
    """Stored prompt circuit definitions."""
    __tablename__ = "circuits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RAGConfig(Base):
    """Configuration for RAG embedding service"""
    __tablename__ = "rag_config"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False, default="ollama")  # "ollama", "gemini", "openai"

    # Provider-specific settings
    ollama_base_url = Column(String(255), nullable=False, default="http://localhost:11434")
    ollama_model = Column(String(100), nullable=False, default="nomic-embed-text:latest")
    gemini_api_key = Column(String(255), nullable=True)
    gemini_model = Column(String(100), nullable=False, default="models/text-embedding-004")

    # Retrieval settings
    top_k_candidates = Column(Integer, nullable=False, default=200)  # Candidates for reranking
    keyword_weight = Column(Float, nullable=False, default=0.6)  # Weight for keyword scores
    semantic_weight = Column(Float, nullable=False, default=0.4)  # Weight for semantic scores
    similarity_threshold = Column(Float, nullable=False, default=0.5)  # Minimum similarity to consider

    # Performance settings
    batch_size = Column(Integer, nullable=False, default=32)  # Batch size for embedding generation
    regenerate_on_content_update = Column(JSON, nullable=False, default=True)  # Auto-regenerate embeddings
    embedding_dimensions = Column(Integer, nullable=False, default=384)  # Expected embedding dimensions

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
class AppSettings(Base):
    """Main application settings storage"""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "main_config"
    value = Column(JSON, nullable=False)  # Store all settings as JSON
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# Add messages relationship to ChatSession
ChatSession.messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")

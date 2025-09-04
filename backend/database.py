from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).resolve().parent / "app.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from models
try:
    from .models import Base
except ImportError:
    from models import Base

def create_tables():
    """Create all database tables."""

    # Ensure models are imported
    try:
        from .models import ChatSession, ChatMessage
    except ImportError:
        from models import ChatSession, ChatMessage
    print("[CoolChat] Models loaded for table creation")

    Base.metadata.create_all(bind=engine)
    print("[CoolChat] Tables created successfully")

def get_db():
    """Dependency function to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

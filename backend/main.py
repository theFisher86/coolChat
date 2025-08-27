from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import Base, engine
from .routers import characters

app = FastAPI(title="CoolChat")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
app.include_router(characters.router)

frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/app", StaticFiles(directory=frontend_build, html=True), name="frontend")


@app.get("/health")
async def health_check():
    """Simple endpoint to confirm the service is running."""
    return {"status": "ok"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="CoolChat")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        """Root endpoint with a friendly message."""
        return {"message": "Welcome to CoolChat API. Visit /docs for API documentation."}


@app.get("/health")
async def health_check():
    """Simple endpoint to confirm the service is running."""
    return {"status": "ok"}



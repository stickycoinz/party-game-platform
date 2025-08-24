from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routers import lobby_routes, ws_routes
import os

app = FastAPI(
    title="Party Game Platform",
    description="A lightweight, browser-based party game platform",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lobby_routes.router)
app.include_router(ws_routes.router)

# Static files for test client
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Party Game Platform",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "test_client": "/static/index.html"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv

load_dotenv('../.env')

# Import routers
from routers import rooms, participants, calls, transfers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Warm Transfer API",
    description="LiveKit-based warm call transfer system with AI-generated summaries",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rooms.router)
app.include_router(participants.router)
app.include_router(calls.router)
app.include_router(transfers.router)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "warm-transfer-api",
        "version": "1.0.0",
        "livekit_configured": bool(os.getenv("LIVEKIT_API_KEY")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY"))
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Warm Transfer API",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

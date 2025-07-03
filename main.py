import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.embedding_service import embedding_service
from app.routes import auth, admin, doctor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Doctor Assistant API...")
    await connect_to_mongo()
    
    # Initialize embedding service
    try:
        await embedding_service.initialize()
        logger.info("Embedding service initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize embedding service: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Doctor Assistant API...")
    await close_mongo_connection()

# Create FastAPI app
app = FastAPI(
    title="Doctor Assistant API",
    description="AI-powered medical assistant system for doctors",
    version="1.0.0",
    lifespan=lifespan,
    # Define only bearer token security scheme
    openapi_tags=[
        {"name": "Authentication", "description": "Login and token management"},
        {"name": "Admin", "description": "Admin operations"},
        {"name": "Doctor", "description": "Doctor operations"},
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(doctor.router, prefix="/doctors", tags=["Doctor"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Doctor Assistant API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 
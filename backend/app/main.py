"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

FastAPI application entry point.

Registers all routers and configures CORS.
Database tables are created on startup via the lifespan handler.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables and run column migrations on startup."""
    from database import create_tables, migrate_tables
    create_tables()
    migrate_tables()
    yield


app = FastAPI(
    title="NJIT AI-Assisted Digital Badge Classification Tool",
    version=os.getenv("APP_VERSION", "1.0.0"),
    description=(
        "Deterministic, explainable, auditable badge classification "
        "based on NJIT's official taxonomy."
    ),
    lifespan=lifespan,
)

# CORS — must be registered immediately after app creation, before any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers after middleware
from app.routes.ingestion import router as ingestion_router
from app.routes.classification import router as classification_router
from app.routes.review import router as review_router
from app.routes.logs import router as logs_router
from app.routes.reviewer import router as reviewer_router

app.include_router(ingestion_router)
app.include_router(classification_router)
app.include_router(review_router)
app.include_router(logs_router)
app.include_router(reviewer_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": os.getenv("APP_VERSION", "1.0.0")}

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.gis import router as gis_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.rainfall import router as rainfall_router
from backend.app.api.readiness import router as readiness_router

app = FastAPI(
    title="Ballari Urban Flood Digital Twin API",
    description="GIS-based urban flood risk research and decision-support platform.",
    version="0.1.0",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes only after creating the application.
app.include_router(gis_router)

app.include_router(evidence_router)
app.include_router(rainfall_router)

app.include_router(readiness_router)

@app.get("/")
def root():
    return {
        "project": "Ballari Urban Flood Digital Twin",
        "status": "online",
        "version": "0.1.0",
        "message": "Flood research and decision-support API is running.",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "urban-flood-digital-twin-api",
    }

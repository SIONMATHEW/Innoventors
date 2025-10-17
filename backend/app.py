"""
File: app.py
Purpose: Main FastAPI application for Innoventors backend.
"""

from fastapi import FastAPI, Depends, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
import os

from . import models
from .db import SessionLocal
from .analyzer import analyze_text, extract_text_from_pdf

# ------------------------------------------------------
# App initialization
# ------------------------------------------------------
app = FastAPI(
    title="Innoventors API",
    description="AI-driven incident management platform for PSA Code Sprint 2025",
    version="1.0.0"
)

# ------------------------------------------------------
# Database Dependency
# ------------------------------------------------------
def get_db():
    """Provide a database session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------
# Routes
# ------------------------------------------------------
@app.get("/")
def home():
    """Root endpoint – confirms the API is running."""
    return {
        "message": "🚀 Innoventors API is up and running!",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health_check():
    """Quick health check endpoint."""
    return {"health": "✅ healthy"}

@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    """Return all incidents from the database."""
    incidents = db.query(models.Incident).all()
    return {
        "incidents": [
            {
                "id": i.id,
                "title": i.title,
                "description": i.description,
                "root_cause": i.root_cause,
                "recommendation": i.recommendation,
                "timestamp": i.timestamp
            }
            for i in incidents
        ]
    }

# ------------------------------------------------------
# AI-powered Analyze Endpoint
# ------------------------------------------------------
@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Analyze uploaded text or PDF, generate AI insights using OpenAI,
    and store the result in the database.
    """
    content = ""

    # Save and read the uploaded file
    if file.filename.endswith(".pdf"):
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as temp_file:
            temp_file.write(await file.read())
        content = extract_text_from_pdf(temp_path)
        os.remove(temp_path)
    else:
        content = (await file.read()).decode("utf-8")

    # Run AI analysis (normal OpenAI)
    result = analyze_text(content)

    # Store in DB
    incident = models.Incident(
        title=file.filename,
        description=content[:500],
        root_cause=result["analysis"],
        recommendation="See AI report"
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return {
        "status": "success",
        "incident_id": incident.id,
        "ai_result": result
    }

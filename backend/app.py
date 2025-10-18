"""
File: app.py
Purpose: Main FastAPI app for Innoventors (v3) – robust AI RCA pipeline.
"""

from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import os

from . import models
from .db import SessionLocal, create_all
from .analyzer import analyze_text, extract_text_from_pdf, _split_sections, _coerce_to_fields

app = FastAPI(
    title="Innoventors API",
    description="AI-driven incident management backend (v3)",
    version="3.0.0"
)

# ------------------------------------------------------------
# DB session helper
# ------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def _startup():
    """Auto-create DB tables."""
    create_all()

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "🚀 Innoventors API v3 active", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    """Fetch all incidents with their file and analysis details."""
    rows = (
        db.query(models.Incident, models.File, models.Analysis)
        .join(models.File, models.Incident.file_id == models.File.id)
        .outerjoin(models.Analysis, models.Analysis.incident_id == models.Incident.id)
        .order_by(models.Incident.created_at.desc())
        .all()
    )

    return {
        "count": len(rows),
        "incidents": [
            {
                "id": inc.id,
                "case_name": inc.case_name,
                "file": f.filename,
                "uploaded_at": f.upload_time.isoformat(),
                "summary": a.summary if a else None,
                "root_cause": a.root_cause if a else None,
                "recommendation": a.recommendation if a else None,
                "severity": a.severity if a else None,
                "category": a.category if a else None,
            }
            for (inc, f, a) in rows
        ]
    }

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a text/PDF incident file, run AI RCA for each test case, and store detailed results.
    """
    # Step 1: Read file content
    if file.filename.endswith(".pdf"):
        tmp_path = f"temp_{file.filename}"
        with open(tmp_path, "wb") as temp_file:
            temp_file.write(await file.read())
        content = extract_text_from_pdf(tmp_path)
        os.remove(tmp_path)
    else:
        content = (await file.read()).decode("utf-8", errors="ignore")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty or unreadable.")

    # Step 2: Create file record
    new_file = models.File(filename=file.filename)
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # Step 3: Run analysis
    ai_result = analyze_text(content)
    ai_list = ai_result.get("analysis", [])
    sections = _split_sections(content)

    # Step 4: Insert into DB
    inserted = []
    for idx, sec in enumerate(sections):
        title, body = sec.get("title"), sec.get("body", "")
        inc = models.Incident(file_id=new_file.id, case_name=title, body=body)
        db.add(inc)
        db.commit()
        db.refresh(inc)

        ai_text = ai_list[idx]["analysis"] if idx < len(ai_list) else "{}"
        fields = _coerce_to_fields(ai_text)
        analysis = models.Analysis(
            incident_id=inc.id,
            root_cause=fields.get("root_cause"),
            summary=fields.get("summary"),
            recommendation=fields.get("recommendation"),
            category=fields.get("category"),
            severity=fields.get("severity"),
            ai_model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "azure-gpt-4.1-nano")
        )
        db.add(analysis)
        db.commit()

        inserted.append({"incident_id": inc.id, "case": title})

    return {
        "status": "success",
        "file": {"id": new_file.id, "filename": new_file.filename},
        "total_incidents": len(inserted),
        "inserted": inserted
    }

@app.delete("/reset")
def reset_database(db: Session = Depends(get_db)):
    """Deletes all records in the database (manual reset)."""
    try:
        db.query(models.Analysis).delete()
    except Exception:
        pass
    db.query(models.Incident).delete()
    db.query(models.File).delete()
    db.commit()
    return {"status": "success", "message": "All data cleared successfully"}

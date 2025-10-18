"""
File: models.py
Purpose: Define database tables (File, Incident, Analysis) using SQLAlchemy ORM.
Readable and relational.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    source = Column(String(100), default="user_upload")
    upload_time = Column(DateTime, default=datetime.utcnow)

    incidents = relationship("Incident", back_populates="file", cascade="all, delete-orphan")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    case_name = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    file = relationship("File", back_populates="incidents")
    analysis = relationship("Analysis", back_populates="incident",
                            uselist=False, cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    root_cause = Column(Text)
    summary = Column(Text)
    recommendation = Column(Text)
    category = Column(String(120))
    severity = Column(String(50))
    ai_model = Column(String(120), default="azure-gpt")
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="analysis")

"""
File: models.py
Purpose: Define database models (tables) for incidents and related entities.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .db import Base

# ------------------------------------------------------
# Incident Table
# ------------------------------------------------------

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    root_cause = Column(Text)
    recommendation = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

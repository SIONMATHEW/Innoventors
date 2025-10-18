"""
File: db.py
Purpose: Initialize SQLite database and SQLAlchemy engine.
Simple and reliable.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./innoventors.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_all():
    """Create all database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

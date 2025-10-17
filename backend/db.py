"""
File: db.py
Purpose: Initialize SQLite database and SQLAlchemy engine.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ------------------------------------------------------
# Database Configuration
# ------------------------------------------------------

# Read database URL from environment variable or fallback to local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./innoventors.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()

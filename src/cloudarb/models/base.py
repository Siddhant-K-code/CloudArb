"""
Base model class for CloudArb database models.
"""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


class Base:
    """Base class for all database models."""

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update(self, db: Session, **kwargs) -> "Base":
        """Update model with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.commit()
        db.refresh(self)
        return self

    @classmethod
    def get_by_id(cls, db: Session, id: int) -> "Base":
        """Get model by ID."""
        return db.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100) -> list["Base"]:
        """Get all models with pagination."""
        return db.query(cls).offset(skip).limit(limit).all()

    def delete(self, db: Session) -> bool:
        """Delete model from database."""
        db.delete(self)
        db.commit()
        return True


# Create declarative base
Base = declarative_base(cls=Base)
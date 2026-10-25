"""User model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, default="Learner")
    preferences = Column(JSON, default=lambda: {"language": "en", "level": "intermediate", "mode": "answer"})
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

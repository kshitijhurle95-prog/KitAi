"""Self-learning Experience log model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Boolean, Float, JSON
from app.models import Base


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, default="default_user", index=True)
    query = Column(Text, nullable=False)
    task_type = Column(String, nullable=False, index=True)
    solution = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    feedback_score = Column(Float, nullable=True)  # User rating (e.g., 1.0 or -1.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

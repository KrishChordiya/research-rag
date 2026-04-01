import uuid
from sqlalchemy import JSON, Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "sessions"

    # Using UUIDs for session IDs is a best practice for API security
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    metrics = Column(JSON, default={"total_tokens": 0, "total_messages": 0})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

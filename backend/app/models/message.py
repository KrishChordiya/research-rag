import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum as SQLEnum,
    JSON,
    ForeignKey,
)
from sqlalchemy.sql import func
from app.core.database import Base


class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(String, nullable=False)

    metrics = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())

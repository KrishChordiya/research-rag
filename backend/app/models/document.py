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


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    filename = Column(String, index=True)
    file_path = Column(String)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    extracted_data_path = Column(String, nullable=True)
    metrics = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

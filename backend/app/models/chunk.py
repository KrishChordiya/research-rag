from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from app.core.config import settings
from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    text = Column(String, nullable=False)
    payload = Column(JSON, default={})
    embedding = Column(Vector(settings.EMBEDDING_DIM))

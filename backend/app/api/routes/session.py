from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import ChatSession, Message, Document

router = APIRouter()


@router.post("/sessions/")
async def create_empty_session(db: AsyncSession = Depends(get_db)):
    """
    Called by the Next.js home page if a user starts typing without uploading a PDF.
    Returns a fresh session_id so the frontend can redirect to /session/{id}.
    """
    new_session = ChatSession()
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {"session_id": new_session.id}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single session by ID."""

    stmt = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "created_at": session.created_at,
        "metrics": session.metrics,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a session and its associated messages and documents."""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"status": "deleted"}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches the chronological chat history for the React message interface."""
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())  # Oldest to newest
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        # Check if session exists at all
        session = await db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    return {
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "metrics": msg.metrics,  # Expose metrics for UI badges (e.g., "Retrieved in 1.2s")
                "created_at": msg.created_at,
            }
            for msg in messages
        ]
    }


@router.get("/sessions/{session_id}/documents")
async def get_session_documents(session_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches the list of PDFs in this session for the UI sidebar."""
    stmt = select(Document).where(Document.session_id == session_id)
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "status": doc.status.value,
                "metrics": doc.metrics,
            }
            for doc in docs
        ]
    }

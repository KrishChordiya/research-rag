from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import ChatSession
from app.services.chat_service import stream_chat_response

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat/")
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if not request.session_id.strip():
        raise HTTPException(status_code=400, detail="Session ID is required.")

    # 1. STRICT VALIDATION: Check if session exists
    session = await db.get(ChatSession, request.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session ID '{request.session_id}' not found. Please upload a document first.",
        )

    return StreamingResponse(
        stream_chat_response(request.session_id, request.message),
        media_type="text/event-stream",
    )

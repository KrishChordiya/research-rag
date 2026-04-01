from typing import List, Optional
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ingestion_service import run_background_ingestion_task
from app.core.database import get_db
from app.models import Document, ChatSession
from app.core.logger import log
from app.core.config import settings
import os
import shutil

router = APIRouter()


async def process_uploads(
    session_id: Optional[str],
    files: List[UploadFile],
    db: AsyncSession,
    background_tasks: BackgroundTasks,
):
    # 1. Session Management: Get or create a session.
    if session_id:
        session = await db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session with id '{session_id}' not found."
            )
    else:
        session = ChatSession()
        db.add(session)
        await db.flush()  # Use flush to get the ID without committing the transaction
        session_id = str(session.id)

    if len(files) > settings.MAX_PDF_UPLOADS:
        raise HTTPException(
            status_code=400,
            detail=f"You can upload a maximum of {settings.MAX_PDF_UPLOADS} files.",
        )

    log.info(f"Processing upload for Session: {session_id}")

    doc_tasks = []
    response_data = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            log.warning(f"Skipping non-PDF file: {file.filename}")
            continue

        new_doc = Document(
            session_id=session_id, filename=file.filename, status="pending"
        )
        db.add(new_doc)
        await db.flush()

        doc_dir = os.path.join(settings.UPLOAD_DIR, session_id, str(new_doc.id))
        os.makedirs(doc_dir, exist_ok=True)

        file_path = os.path.join(doc_dir, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

        new_doc.file_path = file_path
        doc_tasks.append((new_doc.id, file_path, session_id))
        response_data.append({"filename": file.filename, "document_id": new_doc.id})

    if not doc_tasks:
        raise HTTPException(status_code=400, detail="No valid PDF files were uploaded.")

    await db.commit()

    background_tasks.add_task(run_background_ingestion_task, doc_tasks)

    return {"status": "accepted", "session_id": session_id, "documents": response_data}


@router.post("/upload/")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    return await process_uploads(session_id, files, db, background_tasks)

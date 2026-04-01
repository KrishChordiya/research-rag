import asyncio
import os
import json
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.chunking import HierarchicalChunker

from app.models import Document, DocumentChunk, DocumentStatus
from app.core.logger import log
from app.core.database import AsyncSessionLocal
from app.core.config import settings


# --- Embedding Logic (from embedder.py) ---


async def _get_embeddings_openrouter(texts: list[str]) -> list[list[float]]:
    """Fetches embeddings for a list of texts from OpenRouter."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.EMBEDDING_MODEL, "input": texts}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]


async def _embed_and_store_chunks(document_id: int, data_path: str, db: AsyncSession):
    """Reads parsed data, generates embeddings, and stores document chunks."""
    start_time = time.time()
    with open(data_path, "r", encoding="utf-8") as f:
        parsed_data = json.load(f)

    chunks = parsed_data.get("chunks", [])
    if not chunks:
        return {"embedding_time_seconds": 0, "total_vectors_stored": 0}

    batch_size = 20  # Process chunks in batches to avoid overwhelming the API
    total_vectors = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]

        try:
            embeddings = await _get_embeddings_openrouter(texts)
            db_chunks = [
                DocumentChunk(
                    document_id=document_id,
                    text=chunk_data["text"],
                    payload=chunk_data.get("metadata", {}),
                    embedding=embeddings[j],
                )
                for j, chunk_data in enumerate(batch)
            ]
            db.add_all(db_chunks)
            await db.commit()
            total_vectors += len(db_chunks)
        except Exception as e:
            log.error(
                f"Failed to process batch {i//batch_size} for doc {document_id}: {e}"
            )
            raise  # Re-raise to be caught by the background task runner

    return {
        "embedding_time_seconds": round(time.time() - start_time, 2),
        "total_vectors_stored": total_vectors,
        "embedding_model_used": settings.EMBEDDING_MODEL,
    }


# --- Parsing Logic (from parser.py) ---


def _flatten_metadata(raw_meta: dict, document_id: int, session_id: str) -> dict:
    """Extracts and cleans metadata from Docling's raw output."""
    pages = set()
    for item in raw_meta.get("doc_items", []):
        for prov in item.get("prov", []):
            if "page_no" in prov:
                pages.add(prov["page_no"])
    
    clean_name = (
        raw_meta.get("origin", {})
        .get("filename", f"doc_{document_id}")
    )

    return {
        "session_id": session_id,
        "document_id": document_id,
        "filename": clean_name,
        "headings": " | ".join(raw_meta.get("headings", [])),
        "pages": ", ".join(map(str, sorted(pages))) if pages else "unknown",
        "page_no": list(pages)[0] if pages else "unknown"  # Single page reference for citation
    }


def _parse_and_chunk_document(
    file_path: str, document_id: int, session_id: str
) -> tuple[str, dict]:
    """
    Synchronous function to parse a PDF, extract images, chunk content,
    and save the structured data to a JSON file. Designed to be run in a
    separate process to avoid blocking the asyncio event loop.
    """
    start = time.perf_counter()
    try:
        # 1. Setup Docling for parsing and image extraction
        pipeline_options = PdfPipelineOptions(
            generate_picture_images=settings.EXTRACT_CHUNK_IMAGES,
            do_ocr=settings.ENABLE_OCR,
            accelerator_options=AcceleratorOptions(
                device=AcceleratorDevice(settings.ACCELERATOR_DEVICE), 
                num_threads=settings.DOCLING_THREADS
            ),
        )
        converter = DocumentConverter(
            format_options={"pdf": PdfFormatOption(pipeline_options=pipeline_options)}
        )
        docling_doc = converter.convert(file_path).document

        # 2. Extract and save images to a dedicated directory
        image_map = {}  # Maps Docling's internal cref to a local file path
        image_records = []
        img_dir = os.path.join(
            settings.UPLOAD_DIR, session_id, str(document_id), "images"
        )
        os.makedirs(img_dir, exist_ok=True)

        for i, picture in enumerate(docling_doc.pictures):
            pil_image = picture.get_image(docling_doc)
            if pil_image:
                img_path = os.path.join(img_dir, f"pic_{i}.png")
                pil_image.save(img_path, "PNG")
                image_map[picture.self_ref] = img_path
                image_records.append({"path": img_path, "ref": picture.self_ref})

        # 3. Chunk the document and associate images with chunks
        chunker = HierarchicalChunker()
        chunks = list(chunker.chunk(docling_doc))
        serialized_chunks = []
        for chunk in chunks:
            chunk_image_paths = []
            for item in chunk.meta.doc_items:
                if item.parent and hasattr(item.parent, "cref") and item.parent.cref:
                    if (
                        img_path := image_map.get(item.parent.cref)
                    ) and img_path not in chunk_image_paths:
                        chunk_image_paths.append(img_path)

            meta = _flatten_metadata(
                chunk.meta.export_json_dict(), document_id, session_id
            )
            meta["has_image"] = bool(chunk_image_paths)
            meta["image_paths"] = chunk_image_paths
            serialized_chunks.append({"text": chunk.text, "metadata": meta})

        # 4. Save structured data to JSON
        data_path = file_path.replace(".pdf", "_parsed_data.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(
                {"chunks": serialized_chunks, "images": image_records}, f, indent=2
            )

        metrics = {
            "parsing_time_seconds": round(time.perf_counter() - start, 2),
            "total_chunks_yielded": len(serialized_chunks),
            "total_images_extracted": len(image_records),
        }
        return data_path, metrics
    except Exception as e:
        log.error(f"Docling processing failed for doc {document_id}: {e}")
        raise


# --- Background Task Orchestration ---


async def run_background_ingestion_task(doc_tasks: list[tuple[int, str, str]]):
    """
    The main background task that orchestrates the parsing and embedding for a batch of documents.
    """
    log.info(f"Starting background ingestion for {len(doc_tasks)} documents.")

    async with AsyncSessionLocal() as db:
        for doc_id, _, _ in doc_tasks:
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status=DocumentStatus.PARSING)
            )
        await db.commit()

    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=settings.MAX_CPU_WORKERS) as pool:
        futures = [
            loop.run_in_executor(
                pool, _parse_and_chunk_document, file_path, doc_id, session_id
            )
            for doc_id, file_path, session_id in doc_tasks
        ]
        parse_results = await asyncio.gather(*futures, return_exceptions=True)

    async with AsyncSessionLocal() as db:
        for (doc_id, file_path, _), result in zip(doc_tasks, parse_results):
            doc = await db.get(Document, doc_id)
            if not doc:
                log.warning(f"Document {doc_id} not found after parsing, skipping.")
                continue

            if isinstance(result, Exception):
                log.error(f"Parsing failed for document {doc_id}: {result}")
                doc.status = DocumentStatus.FAILED
                doc.metrics = {"error": str(result)}
                await db.commit()
                continue

            data_path, parse_metrics = result
            log.info(f"Parsing complete for doc {doc_id}. Starting embedding.")

            try:
                doc.status = DocumentStatus.EMBEDDING
                await db.commit()

                embed_metrics = await _embed_and_store_chunks(doc_id, data_path, db)

                doc.status = DocumentStatus.COMPLETED
                doc.extracted_data_path = data_path
                doc.metrics = {**parse_metrics, **(embed_metrics or {})}

                # Clean up the original PDF file after successful processing
                if os.path.exists(file_path):
                    os.remove(file_path)

                await db.commit()
                log.info(f"Success: Document {doc_id} is ready for Chat.")
            except Exception as e:
                log.error(f"Embedding failed for document {doc_id}: {e}")
                doc.status = DocumentStatus.FAILED
                doc.metrics = {
                    **parse_metrics,
                    "error": f"Embedding Phase Error: {str(e)}",
                }
                await db.commit()

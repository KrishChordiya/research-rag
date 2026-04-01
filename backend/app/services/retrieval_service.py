import asyncio
import json
import time
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import DocumentChunk, Document
from app.core.config import settings
from app.core.logger import log
from flashrank import Ranker, RerankRequest

# Conditional initialization of the Ranker model
ranker = None
if settings.USE_RERANKER:
    try:
        ranker = Ranker(model_name=settings.RANKER_MODEL, cache_dir="uploads/models")
    except Exception as e:
        log.error(f"Failed to initialize Ranker: {e}. Reranking will be disabled.")

async def _get_embeddings_for_queries(texts: list[str]) -> list[list[float]]:
    """Fetches embeddings for a list of query texts from an external API."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": settings.EMBEDDING_MODEL, "input": texts}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            return [item["embedding"] for item in response.json()["data"]]
        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error fetching embeddings: {e.response.text}")
            raise
        except Exception as e:
            log.error(f"An unexpected error occurred fetching embeddings: {e}")
            raise


async def _expand_query(user_query: str, client: httpx.AsyncClient) -> list[str]:
    """
    Calls an LLM to generate alternative, expanded queries based on the user's input.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    system_prompt = (
        f"You are a search query optimizer. Generate exactly {settings.IMPROVED_QUERIES_COUNT} "
        "alternative variations of the user's query to help retrieve documents from a vector database. "
        "Include synonyms, broader concepts, and narrower concepts. "
        "Return ONLY a JSON object with a 'queries' array."
    )
    payload = {
        "model": settings.QUERY_IMPROVER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        response = await client.post(url, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        # The 'content' field is a JSON string that needs to be parsed.
        content_str = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content_str:
            log.warning("Query Improver returned empty content.")
            return []
            
        content_json = json.loads(content_str)
        return content_json.get("queries", [])
        
    except json.JSONDecodeError as e:
        log.warning(f"Failed to decode JSON from query improver: {e}")
        return []
    except Exception as e:
        log.warning(f"Query Improver failed: {e}. Falling back to original query only.")
        return []


def _rerank_chunks_sync(user_query: str, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """
    Synchronous function to rerank document chunks using FlashRank.
    Designed to be run in a thread pool to avoid blocking the event loop.
    """
    if not chunks:
        return []

    passages = [{"id": chunk.id, "text": chunk.text, "meta": chunk.payload} for chunk in chunks]
    request = RerankRequest(query=user_query, passages=passages)
    reranked_results = ranker.rerank(request)

    chunk_map = {chunk.id: chunk for chunk in chunks}
    return [chunk_map[res["id"]] for res in reranked_results if res["id"] in chunk_map]


async def retrieve_and_rerank(
    session_id: str, user_query: str, db: AsyncSession
) -> tuple[list[DocumentChunk], dict]:
    """
    The main retrieval pipeline:
    1. Expands the user query into multiple variations.
    2. Fetches embeddings for all queries.
    3. Performs a multi-query vector search to find initial candidate chunks.
    4. Reranks the candidates to find the most relevant final chunks.
    """
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        improved_queries = await _expand_query(user_query, client)
    
    all_queries = [user_query] + improved_queries
    log.info(f"Expanded to {len(all_queries)} queries.")

    query_vectors = await _get_embeddings_for_queries(all_queries)

    # --- Vector Search ---
    unique_chunks_map = {}
    for vector in query_vectors:
        stmt = (
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.session_id == session_id)
            .order_by(DocumentChunk.embedding.cosine_distance(vector))
            .limit(settings.TOP_K_INITIAL)
        )
        result = await db.execute(stmt)
        for chunk in result.scalars().all():
            unique_chunks_map[chunk.id] = chunk

    initial_chunks = list(unique_chunks_map.values())
    if not initial_chunks:
        metrics = {
            "retrieval_time": round(time.time() - start_time, 2),
            "queries_generated": len(improved_queries),
            "initial_chunks_found": 0,
            "final_chunks_used": 0,
        }
        return [], metrics

    log.info(f"Retrieved {len(initial_chunks)} unique chunks.")

    # --- Reranking (Conditional) ---
    if ranker:
        reranked_chunks = await asyncio.to_thread(_rerank_chunks_sync, user_query, initial_chunks)
        final_chunks = reranked_chunks[:settings.TOP_K_RERANK]
    else:
        log.info("Reranking is disabled; returning initial chunks.")
        final_chunks = initial_chunks[:settings.TOP_K_RERANK]
    
    metrics = {
        "retrieval_time": round(time.time() - start_time, 2),
        "queries_generated": len(improved_queries),
        "initial_chunks_found": len(initial_chunks),
        "final_chunks_used": len(final_chunks),
        "reranker_used": bool(ranker),
    }

    return final_chunks, metrics

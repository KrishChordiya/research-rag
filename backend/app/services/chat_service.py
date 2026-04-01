import asyncio
import json
import time
import httpx
import base64
import os

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import ChatSession, Message, MessageRole
from app.core.config import settings
from app.core.logger import log
from app.services.retrieval_service import retrieve_and_rerank


# --- Chat History Management ---


async def _get_chat_history(db: AsyncSession, session_id: str) -> list[dict]:
    """
    Fetches the last N messages for a session and formats them for the LLM prompt.
    """
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(desc(Message.created_at))
        .limit(settings.MAX_CHAT_HISTORY)
    )
    result = await db.execute(stmt)
    # Reverse to get chronological order for the prompt
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in reversed(result.scalars().all())
    ]


# --- SSE Streaming Utilities ---


def _format_sse_event(event: str, data: dict) -> str:
    """Formats a dictionary into a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _encode_image_to_base64(image_path: str) -> str:
    """Reads a local file and returns a base64 encoded string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# --- Main Chat Service ---


async def stream_chat_response(session_id: str, user_query: str):
    """
    Main service to stream a chat response:
    1. Retrieves and reranks documents.
    2. Constructs a multimodal context with text and images.
    3. Streams the response to the client using Server-Sent Events (SSE).
    4. Persists the user and assistant messages to the database.
    """
    async with AsyncSessionLocal() as db:
        # Immediately save the user's message
        user_msg = Message(
            session_id=session_id, role=MessageRole.USER, content=user_query
        )
        db.add(user_msg)
        await db.commit()

        # 1. Retrieve Context
        final_chunks, retrieval_metrics = await retrieve_and_rerank(
            session_id, user_query, db
        )

        # 2. Build Context String and Identify Images
        context_string = ""
        source_documents = []
        final_images = []

        for chunk in final_chunks:
            meta = chunk.payload
            filename = meta.get("filename", "Unknown")
            page_val = meta.get("page_no") or meta.get("pages", "N/A")

            source = {"filename": filename, "page": page_val}
            if source not in source_documents:
                source_documents.append(source)

            citation = f"[Source: {filename}, Page: {page_val}]"
            context_string += f"\n{citation}\n{chunk.text}\n"

            if meta.get("has_image"):
                for path in meta.get("image_paths", []):
                    if os.path.exists(path) and path not in final_images:
                        final_images.append(path)

        # Yield the context immediately for the frontend
        yield _format_sse_event("context", {"sources": source_documents})

        # 3. Fetch History & Build Multimodal Payload
        chat_history = await _get_chat_history(db, session_id)

        content_payload = [{"type": "text", "text": user_query}]
        for img_path in final_images[:3]:  # Cap images to save tokens
            img_b64 = _encode_image_to_base64(img_path)
            content_payload.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )

        # Overwrite the user message content with the multimodal payload
        if chat_history and chat_history[-1]["role"] == "user":
            chat_history[-1]["content"] = content_payload

        # 4. Prepare and Stream LLM Request
        system_prompt = (
            "You are an advanced AI assistant with vision capabilities. "
            "Use the provided context to answer the user's question accurately. "
            "IMPORTANT: For every piece of information you provide that comes from the context, "
            "you MUST include a citation in the format [Source: filename, Page: page_number]. "
            "If you use multiple sources, list them all. If no relevant information is found, "
            "state that clearly.\n\n"
            f"CONTEXT:{context_string if context_string else 'No documents found for this query.'}"
        )
        messages_payload = [{"role": "system", "content": system_prompt}] + chat_history

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.GENERATION_MODEL,
            "messages": messages_payload,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        gen_start_time = time.time()
        assistant_full_response = ""
        prompt_tokens, completion_tokens = 0, 0

        try:
            async with (
                httpx.AsyncClient() as client,
                client.stream(
                    "POST", url, headers=headers, json=payload, timeout=60.0
                ) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)

                            # 1. Safely extract token (delta content)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if token := delta.get("content"):
                                    assistant_full_response += token
                                    yield _format_sse_event("token", {"token": token})

                            # 2. Extract usage (standard in last chunk with stream_options)
                            if usage := data.get("usage"):
                                # Support OpenAI standard and common fallbacks
                                prompt_tokens = (
                                    usage.get("prompt_tokens")
                                    or usage.get("input_tokens")
                                    or prompt_tokens
                                )
                                completion_tokens = (
                                    usage.get("completion_tokens")
                                    or usage.get("output_tokens")
                                    or completion_tokens
                                )
                                log.info(
                                    f"Usage captured: prompt={prompt_tokens}, completion={completion_tokens}"
                                )

                        except (json.JSONDecodeError, KeyError, IndexError) as e:
                            log.warning(f"Error parsing stream chunk: {e}")
                            continue
        except Exception as e:
            log.error(f"Streaming error: {e}")
            yield _format_sse_event("error", {"detail": str(e)})

        # 5. Finalize and Persist Metrics
        generation_time = round(time.time() - gen_start_time, 2)

        # Include retrieved chunks for evaluation
        chunk_data = [{"id": c.id, "text": c.text} for c in final_chunks]

        final_metrics = {
            "generation_time_seconds": generation_time,
            "response_model_used": settings.GENERATION_MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "retrieved_chunks": chunk_data,
            **retrieval_metrics,
        }

        assistant_msg = Message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=assistant_full_response,
            metrics=final_metrics,
        )
        db.add(assistant_msg)

        # Update overall session metrics
        session_obj = await db.get(ChatSession, session_id)
        if session_obj:
            session_metrics = dict(session_obj.metrics) if session_obj.metrics else {}
            session_metrics["total_tokens"] = (
                session_metrics.get("total_tokens", 0)
                + prompt_tokens
                + completion_tokens
            )
            session_metrics["total_messages"] = (
                session_metrics.get("total_messages", 0) + 2
            )
            session_obj.metrics = session_metrics

        await db.commit()
        log.info(f"Session {session_id} updated with new messages and metrics.")

        yield _format_sse_event("end", {"metrics": final_metrics})

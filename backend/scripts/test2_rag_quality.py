import asyncio
import json
import time
import httpx
import os
import argparse
from app.core.config import settings

# Setup
OPENROUTER_API_KEY = settings.OPENROUTER_API_KEY
API_URL = "http://127.0.0.1:8000/api/v1"
JUDGE_MODEL = "arcee-ai/trinity-large-preview:free"

BENCHMARK_QUERIES = [
    {
        "q": "What is the key mechanism for parallelization in Transformers?",
        "gt": "Self-attention mechanism.",
    },
    {
        "q": "How does the Transformer handle long-range dependencies?",
        "gt": "Through the self-attention mechanism that relates different positions of a single sequence.",
    },
    {
        "q": "What is the role of positional encodings in the Transformer architecture?",
        "gt": "To provide information about the relative or absolute position of the tokens in the sequence.",
    },
    {
        "q": "What is the pre-training objective of BERT?",
        "gt": "Masked Language Model (MLM) and Next Sentence Prediction (NSP).",
    },
    {"q": "Is BERT unidirectional or bidirectional?", "gt": "Deeply bidirectional."},
    {
        "q": "How does BERT represent a pair of sentences in the input?",
        "gt": "Using a [SEP] token and learned segment embeddings.",
    },
    {"q": "What is the context length of LLaMA 2?", "gt": "4096 tokens."},
    {
        "q": "How was LLaMA 2 fine-tuned for safety?",
        "gt": "Using RLHF (Reinforcement Learning from Human Feedback).",
    },
    {
        "q": "What architectural change did LLaMA 2 adopt to improve inference scalability?",
        "gt": "Grouped-Query Attention (GQA).",
    },
    {
        "q": "What are the two components of a RAG system?",
        "gt": "A retriever and a generator.",
    },
    {
        "q": "What is the benefit of RAG over standard LLMs?",
        "gt": "Reduces hallucinations by providing external grounded knowledge.",
    },
    {
        "q": "Does RAG use a dense or sparse retriever in the original paper?",
        "gt": "A dense retriever (DPR).",
    },
    {
        "q": "What is Chain-of-Thought prompting?",
        "gt": "Providing a sequence of intermediate reasoning steps.",
    },
    {
        "q": "In what tasks does Chain-of-Thought provide the most gain?",
        "gt": "Complex arithmetic, commonsense, and symbolic reasoning tasks.",
    },
    {
        "q": "Does Chain-of-Thought prompting benefit smaller models?",
        "gt": "The paper finds it primarily benefits large language models (e.g., 100B+ parameters).",
    },
]


async def llm_judge_structured(query, ground_truth, response, retrieved_chunks):
    """
    Calls the judge with a strict JSON schema to ensure perfect results.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    # Format retrieved chunks for the judge
    chunks_text = "\n---\n".join([c["text"] for c in retrieved_chunks])

    prompt = f"""
    ### TASK: RAG Performance Evaluation
    As an expert judge, evaluate the performance of a RAG system.

    ### INPUT DATA:
    - User Query: {query}
    - Ground Truth Answer: {ground_truth}
    - AI Generated Response: {response}
    - Retrieved Chunks (the context):
    {chunks_text}

    ### EVALUATION METRICS:
    1. RECALL: Does any of the retrieved context contain the information needed to answer the query correctly? (1 if yes, 0 if no).
    2. PRECISION: Out of the retrieved chunks, how many are actually relevant to answering the query? (Fraction 0-1).
    3. FAITHFULNESS: Is the AI response derived ONLY from the retrieved context without making things up? (1 if yes, 0 if no).
    4. RELEVANCE: How well does the generated response address the user's specific query? (0-1).
    5. MRR (Reciprocal Rank): At what rank (1 to 10) was the first truly relevant chunk? (1/rank, or 0 if none relevant).

    Return the evaluation as a structured JSON.
    """

    schema = {
        "type": "object",
        "properties": {
            "recall": {"type": "number"},
            "precision": {"type": "number"},
            "faithfulness": {"type": "number"},
            "relevance": {"type": "number"},
            "mrr": {"type": "number"},
        },
        "required": ["recall", "precision", "faithfulness", "relevance", "mrr"],
    }

    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "rag_eval", "schema": schema},
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, headers=headers, json=payload, timeout=60.0)
            res.raise_for_status()
            data = res.json()
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"Judge failed: {e}")
            return {
                "recall": 0,
                "precision": 0,
                "faithfulness": 0,
                "relevance": 0,
                "mrr": 0,
            }


async def run_quality_test(session_id: str, count: int):
    print(f"--- RAG Quality Test: {count} PDF(s) ---")
    results = []

    # Determine which questions to ask
    num_queries = count * 3
    queries = BENCHMARK_QUERIES[:num_queries]

    async with httpx.AsyncClient() as client:
        for item in queries:
            print(f"Query: {item['q']}")
            start_time = time.time()

            # 1. Execute Chat (SSE)
            response_text = ""
            async with client.stream(
                "POST",
                f"{API_URL}/chat/",
                json={"session_id": session_id, "message": item["q"]},
                timeout=60.0,
            ) as stream:
                async for line in stream.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "token" in data:
                            response_text += data["token"]

            latency = round(time.time() - start_time, 2)

            # 2. Fetch history to get the retrieved chunks from metrics
            hist_res = await client.get(f"{API_URL}/sessions/{session_id}/history")
            last_msg = hist_res.json()["messages"][-1]
            metrics = last_msg.get("metrics", {})
            retrieved_chunks = metrics.get("retrieved_chunks", [])

            # 3. Judge the result
            scores = await llm_judge_structured(
                item["q"], item["gt"], response_text, retrieved_chunks
            )
            results.append({"latency": latency, **scores})
            print(f"   Done (Lat: {latency}s)")

    # Print Final Report
    print("\n" + "=" * 80)
    print(f"FINAL RAG QUALITY REPORT ({count} PDFs)")
    print("=" * 80)

    avg = lambda key: sum(r[key] for r in results) / len(results)

    print(f"RETRIEVAL METRICS:")
    print(f"  Avg Recall @ K:      {avg('recall'):.2f}")
    print(f"  Avg Precision @ K:   {avg('precision'):.2f}")
    print(f"  Avg MRR:             {avg('mrr'):.2f}")
    print(f"\nGENERATION METRICS:")
    print(f"  Avg Faithfulness:    {avg('faithfulness'):.2f}")
    print(f"  Avg Answer Relevance:{avg('relevance'):.2f}")
    print(f"\nLATENCY:")
    print(f"  Avg E2E Latency:     {avg('latency'):.2f}s")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_id", type=str, required=True)
    parser.add_argument("--count", type=int, choices=[1, 3, 5], required=True)
    args = parser.parse_args()
    asyncio.run(run_quality_test(args.session_id, args.count))

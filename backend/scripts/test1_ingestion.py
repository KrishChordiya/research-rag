import asyncio
import time
import httpx
import os
import argparse

# Selected arXiv research papers
PAPERS = [
    {"name": "attention.pdf", "url": "https://arxiv.org/pdf/1706.03762.pdf"},
    {"name": "bert.pdf", "url": "https://arxiv.org/pdf/1810.04805.pdf"},
    {"name": "llama2.pdf", "url": "https://arxiv.org/pdf/2307.09288.pdf"},
    {"name": "rag.pdf", "url": "https://arxiv.org/pdf/2005.11401.pdf"},
    {"name": "cot.pdf", "url": "https://arxiv.org/pdf/2201.11903.pdf"},
]

API_URL = "http://127.0.0.1:8000/api/v1"

async def test_ingestion(count: int):
    print(f"--- Ingestion Test: {count} PDF(s) ---")
    
    files_to_upload = []
    for i in range(count):
        paper = PAPERS[i]
        path = os.path.join("benchmark_docs", paper["name"])
        if not os.path.exists(path):
            print(f"Error: {path} not found. Please download it first.")
            return
        files_to_upload.append(("files", (paper["name"], open(path, "rb"), "application/pdf")))

    start_time = time.time()
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/upload/", files=files_to_upload, timeout=None)
        response_data = response.json()
        session_id = response_data["session_id"]
        
        print(f"Upload initiated. Session ID: {session_id}")
        
        while True:
            status_response = await client.get(f"{API_URL}/sessions/{session_id}/documents")
            docs = status_response.json()["documents"]
            all_completed = all(d["status"] == "completed" for d in docs)
            any_failed = any(d["status"] == "failed" for d in docs)
            
            if all_completed:
                duration = round(time.time() - start_time, 2)
                print(f"\nSUCCESS: Ingestion for {count} file(s) completed in {duration}s.")
                print(f"Session ID for Quality Test: {session_id}")
                return
            if any_failed:
                print(f"\nFAILED: One or more documents failed processing.")
                return
            
            print(".", end="", flush=True)
            await asyncio.sleep(2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, choices=[1, 3, 5], required=True)
    args = parser.parse_args()
    asyncio.run(test_ingestion(args.count))

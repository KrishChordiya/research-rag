# Advanced Multimodal RAG Chatbot

### Introduction
A high-performance RAG backend built with FastAPI and PostgreSQL (pgvector) that supports multimodal document processing and sophisticated retrieval. The system implements advanced pipelines for parallelized document ingestion, multi-query expansion, and cross-encoder reranking to ensure precise and context-aware responses. It provides a frontend-ready experience with structured Server-Sent Events (SSE) for real-time streaming of answers, sources, and performance metrics.

*(**Note:** This project is currently not deployed due to the heavy libraries required by Docling, which exceed the limitations of free-tier hosting environments. As a result, you may need to run it locally for full functionality.)*

### Architecture
![Backend Architecture](rag-architecture-detailed.drawio(6).png)

### Benchmark
The following benchmarks were conducted on an **Arch Linux system (16-core CPU, CUDA-enabled GPU)** using a suite of 5 technical arXiv research papers and 15 ground-truth questions.

#### Benchmark Dataset
The system was evaluated using the following foundational AI research papers:
- **Attention Is All You Need**: [arXiv:1706.03762](https://arxiv.org/pdf/1706.03762.pdf)
- **BERT: Pre-training of Deep Bidirectional Transformers**: [arXiv:1810.04805](https://arxiv.org/pdf/1810.04805.pdf)
- **LLaMA 2: Open Foundation and Fine-Tuned Chat Models**: [arXiv:2307.09288](https://arxiv.org/pdf/2307.09288.pdf)
- **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**: [arXiv:2005.11401](https://arxiv.org/pdf/2005.11401.pdf)
- **Chain-of-Thought Prompting Elicits Reasoning in LLMs**: [arXiv:2201.11903](https://arxiv.org/pdf/2201.11903.pdf)

#### 1. Ingestion Performance
| # of PDFs | Total Ingestion Time | Avg Time per PDF | Hardware Utilization |
| :--- | :--- | :--- | :--- |
| **1 PDF** | 24.2s | 24.2s | Single Worker |
| **5 PDFs** | **38.1s** | **7.6s** | **Parallel Throughput Optimized** |

**Observation:** The system demonstrates significant horizontal scaling, achieving a **3.2x increase in efficiency per document** when processing 5 PDFs simultaneously compared to a single upload.

#### 2. Retrieval & Generation Quality
| Metric | 1 PDF | 3 PDFs | 5 PDFs |
| :--- | :--- | :--- | :--- |
| **Recall @ K** | **1.00** | 0.89 | 0.73 |
| **MRR (Mean Reciprocal Rank)** | **0.73** | 0.58 | 0.41 |
| **Avg E2E Latency** | 9.26s* | 2.03s | **2.02s** |

**Observation:** The system achieves perfect recall on single-document sessions. While precision naturally decreases as the vector space grows ("search noise"), the **End-to-End latency remains constant at ~2s**, proving the efficiency of the retrieval-rerank-generation pipeline even as data volume increases.

### Features
-   **Advanced Ingestion Pipeline**: Utilizes `Docling` for high-fidelity PDF parsing and image extraction, offloading CPU-bound tasks to a `ProcessPoolExecutor` utilizing 16 cores.
-   **Multi-Query Expansion**: Combats retrieval limitations by using an LLM to generate alternative versions of the user's query, significantly improving recall in complex vector spaces.
-   **Hybrid Reranking**: Implements a two-stage retrieval process where initial candidate chunks from `pgvector` are re-scored using `FlashRank` (Cross-Encoder) for maximum relevance.
-   **Multimodal Reasoning**: Automatically extracts, stores, and injects relevant images from the document into the LLM context, enabling the assistant to "see" and explain charts, tables, and figures.
-   **Professional Streaming (SSE)**: Streams responses via Server-Sent Events, providing structured data packets for tokens, citations (filename/page), and real-time performance metrics.

### Libraries/Framework
-   **Backend Framework**: FastAPI (Asynchronous Python)
-   **Database & Vector Store**: PostgreSQL with `pgvector`
-   **ORM**: SQLAlchemy 2.0 (Async)
-   **Parsing & OCR**: Docling
-   **Reranker**: FlashRank
-   **LLM Provider**: OpenRouter API (Vision-capable models)
-   **Validation**: Pydantic v2
-   **Package Manager**: `uv`

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    ALLOW_CORS: str = "*"  # Default to allow all for development

    UPLOAD_DIR: str = "uploads"
    IMAGE_DIR: str = "uploads/images"

    EMBEDDING_MODEL: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    EMBEDDING_DIM: int = 2048

    GENERATION_MODEL: str = "arcee-ai/trinity-large-preview:free"
    RANKER_MODEL: str = "ms-marco-MiniLM-L-12-v2"

    MAX_PDF_UPLOADS: int = 3
    MAX_CPU_WORKERS: int = 16
    EXTRACT_CHUNK_IMAGES: bool = True

    USE_RERANKER: bool = True
    ENABLE_OCR: bool = False
    ACCELERATOR_DEVICE: str = "cuda"
    DOCLING_THREADS: int = 1

    MAX_CHAT_HISTORY: int = 5

    QUERY_IMPROVER_MODEL: str = "arcee-ai/trinity-large-preview:free"
    IMPROVED_QUERIES_COUNT: int = 5

    TOP_K_INITIAL: int = 5
    TOP_K_RERANK: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # pyright:ignore

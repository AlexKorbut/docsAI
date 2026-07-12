from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    reasoner_model: str = "claude-opus-4-8"
    verifier_model: str = "claude-opus-4-8"
    planner_model: str = "claude-sonnet-5"
    extraction_model: str = "claude-haiku-4-5"
    # Photo transcription is the primary ingestion path — accuracy first.
    vision_model: str = "claude-opus-4-8"

    # Embeddings / reranking
    voyage_api_key: str = ""
    embedding_model: str = "voyage-3"
    embedding_dim: int = 1024
    rerank_model: str = "rerank-2"

    # Storage
    database_url: str = "postgresql+psycopg://docsai:docsai@localhost:5432/docsai"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "docsai-neo4j"

    # Optional integrations
    llamaparse_api_key: str = ""

    # Original uploaded files are kept here (volume in docker-compose)
    upload_dir: str = "data/uploads"

    # API
    cors_origins: str = "http://localhost:5173"
    min_confidence: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

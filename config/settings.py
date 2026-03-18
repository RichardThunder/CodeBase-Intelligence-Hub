from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    openai_api_base: str | None = None

    # LLM configuration
    llm_model: str = "GLM-4.7"
    embedding_model: str = "embedding-3"

    # ChromaDB configuration
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "codebase_v1"
    chroma_host: str | None = None
    chroma_port: int = 8001

    # Feature flags
    enable_rerank: bool = False

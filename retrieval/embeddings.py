"""Embeddings configuration for ChromaDB integration."""

from langchain_openai import OpenAIEmbeddings
from config.settings import Settings


def get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    """Create OpenAI embeddings using GLM-compatible endpoint.

    Args:
        settings: Configuration with API key and base URL

    Returns:
        OpenAIEmbeddings instance configured for GLM or compatible provider
    """
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
    )

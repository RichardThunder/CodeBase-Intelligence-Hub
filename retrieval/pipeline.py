"""Hybrid retrieval pipeline combining vector search and BM25."""

from typing import Optional
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever, MultiQueryRetriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLanguageModel
from config.settings import Settings


def build_vector_retriever(vectorstore: Chroma, k: int = 20) -> BaseRetriever:
    """Create vector similarity retriever with MMR scoring.

    Args:
        vectorstore: Chroma instance
        k: Number of documents to retrieve

    Returns:
        Retriever using MMR (Max Marginal Relevance) scoring
    """
    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": k * 4},
    )


def build_bm25_retriever(docs: list[Document], k: int = 20) -> BM25Retriever:
    """Create BM25 lexical retriever.

    Args:
        docs: Documents to index
        k: Number of documents to retrieve

    Returns:
        BM25Retriever instance
    """
    retriever = BM25Retriever.from_documents(docs, k=k)
    return retriever


def build_ensemble_retriever(
    vectorstore: Chroma,
    docs: list[Document],
    vector_weight: float = 0.6,
    bm25_weight: float = 0.4,
    k: int = 20,
) -> BaseRetriever:
    """Build hybrid retriever combining vector and BM25 using RRF.

    Args:
        vectorstore: Chroma vector store
        docs: Documents for BM25 indexing
        vector_weight: Weight for vector retriever (0-1)
        bm25_weight: Weight for BM25 retriever (0-1)
        k: Total documents to return

    Returns:
        EnsembleRetriever using Reciprocal Rank Fusion
    """
    vector_retriever = build_vector_retriever(vectorstore, k=k)
    bm25_retriever = build_bm25_retriever(docs, k=k)

    ensemble = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[vector_weight, bm25_weight],
    )
    return ensemble


def build_multiquery_retriever(
    base_retriever: BaseRetriever,
    llm: BaseLanguageModel,
) -> MultiQueryRetriever:
    """Wrap retriever with multi-query expansion.

    Generates multiple variations of the query and retrieves for each,
    deduplicating results before returning.

    Args:
        base_retriever: Ensemble or single retriever to wrap
        llm: Language model for query generation

    Returns:
        MultiQueryRetriever with LLM-based query expansion
    """
    return MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )


def build_retrieval_pipeline(
    vectorstore: Chroma,
    docs: list[Document],
    llm: BaseLanguageModel,
    settings: Settings,
) -> BaseRetriever:
    """Build complete retrieval pipeline with optional reranking.

    Pipeline flow:
    1. Ensemble (vector MMR + BM25)
    2. MultiQuery expansion
    3. Optional CrossEncoderReranker

    Args:
        vectorstore: Chroma instance
        docs: Documents for BM25
        llm: Language model for query expansion
        settings: Configuration with reranker settings

    Returns:
        Final retriever ready for use in RAG chains
    """
    # Build ensemble
    ensemble = build_ensemble_retriever(vectorstore, docs)

    # Add multi-query expansion
    retriever = build_multiquery_retriever(ensemble, llm)

    # Optional reranking
    if settings.enable_rerank:
        try:
            from langchain_community.retrievers.document_compressors import (
                CrossEncoderReranker,
            )
            from langchain_community.cross_encoders import HuggingFaceCrossEncoder
            from langchain_classic.retrievers.contextual_compression import (
                ContextualCompressionRetriever,
            )

            model = HuggingFaceCrossEncoder(
                model_name="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
            )
            compressor = CrossEncoderReranker(model=model, top_n=5)

            retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=retriever,
            )
        except ImportError:
            # Fall back to ensemble without reranking
            pass

    return retriever

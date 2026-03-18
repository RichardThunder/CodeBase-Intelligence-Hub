"""RAG chain combining retriever and LLM with proper context formatting."""

from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    Runnable,
    RunnablePassthrough,
    RunnableParallel,
)
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever


def format_docs(docs: list[Any]) -> str:
    """Format retrieved documents with file path annotations.

    Args:
        docs: List of Document objects from retriever

    Returns:
        Formatted string with document content and source paths
    """
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("file_path", doc.metadata.get("source", "unknown"))
        content = doc.page_content
        formatted.append(f"【文档 {i}】来自: {source}\n{content}")

    return "\n\n".join(formatted) if formatted else "(未检索到相关文档)"


def build_rag_chain(retriever: BaseRetriever, llm: BaseLanguageModel) -> Runnable:
    """Build RAG chain with retrieval and generation.

    Input: {"question": "user query", ...}
    Output: str (final answer)

    Args:
        retriever: Retriever for fetching relevant documents
        llm: Language model for generation

    Returns:
        LCEL chain ready for invocation
    """
    rag_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个代码库问答助手。请根据以下检索到的代码片段和文档，
准确回答用户的问题。

如果检索结果中有相关信息，请基于这些信息构建答案。
如果没有找到相关信息，请明确说明。

检索到的代码片段和文档：
{context}""",
        ),
        ("human", "{question}"),
    ])

    # Pipeline: question → retriever → format → merge with question → prompt → llm → str
    chain = (
        RunnableParallel(
            context=retriever | format_docs,
            question=RunnablePassthrough(),
        )
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    return chain


def build_rag_chain_with_source(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
) -> Runnable:
    """Build RAG chain that also returns source documents.

    Input: {"question": "user query", ...}
    Output: {"answer": str, "sources": list[dict]}

    Args:
        retriever: Retriever for fetching relevant documents
        llm: Language model for generation

    Returns:
        LCEL chain that returns answer and sources
    """
    rag_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个代码库问答助手。请根据以下检索到的代码片段和文档，
准确回答用户的问题。

检索到的代码片段和文档：
{context}""",
        ),
        ("human", "{question}"),
    ])

    def extract_sources(docs):
        """Extract source information from retrieved documents."""
        sources = []
        for doc in docs:
            source = {
                "file_path": doc.metadata.get("file_path", doc.metadata.get("source", "unknown")),
                "content_preview": doc.page_content[:200],
                "metadata": doc.metadata,
            }
            sources.append(source)
        return sources

    # Retrieve and extract sources
    retrieval_chain = RunnableParallel(
        docs=retriever,
        question=RunnablePassthrough(),
    ) | (lambda x: {
        "context": format_docs(x["docs"]),
        "question": x["question"],
        "sources": extract_sources(x["docs"]),
    })

    # Generate answer
    answer_chain = (
        retrieval_chain
        | RunnableParallel(
            answer=(rag_prompt | llm | StrOutputParser()),
            sources=lambda x: x["sources"],
        )
        | (lambda x: {
            "answer": x["answer"],
            "sources": x["sources"],
        })
    )

    return answer_chain

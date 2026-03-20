"""Gold-standard QA dataset for benchmarking RAG systems.

50 QA pairs sourced from the project's own codebase (self-referential corpus).
Expected answers verified against actual source files.
"""

from dataclasses import dataclass, field


@dataclass
class QAPair:
    id: str
    category: str  # code_lookup | explanation | bug_analysis | general_qa | git_history
    question: str
    expected_answer: str  # gold standard for faithfulness judge
    relevant_files: list[str]  # relative paths for Recall/Precision matching
    difficulty: str  # easy | medium | hard
    requires_git: bool = False


DATASET: list[QAPair] = [
    # ── code_lookup (12) ─────────────────────────────────────────────────────
    QAPair(
        id="code_lookup_001",
        category="code_lookup",
        question="Where is the BM25 retriever built, and what function creates it?",
        expected_answer="The BM25 retriever is built in retrieval/pipeline.py by the function build_bm25_retriever, which calls BM25Retriever.from_documents(docs, k=k).",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_002",
        category="code_lookup",
        question="What function handles intent classification in the orchestrator node?",
        expected_answer="The orchestrator_node function in graph/nodes.py handles intent classification. It uses a ChatPromptTemplate with the ORCHESTRATOR_SYSTEM_PROMPT and an IntentClassification Pydantic model to classify the user query into one of: code_lookup, explanation, bug_analysis, or general_qa.",
        relevant_files=["graph/nodes.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_003",
        category="code_lookup",
        question="What file contains the AgentState definition and what fields does it track?",
        expected_answer="AgentState is defined in graph/state.py as a TypedDict. It tracks: user_query, session_id, history, intent, intent_confidence, next_agent, retrieved_chunks, analysis_results, code_outputs, search_results, final_answer, requires_human_approval, human_approval_given, error_message, iteration_count, and timestamps.",
        relevant_files=["graph/state.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_004",
        category="code_lookup",
        question="What function builds the LCEL RAG chain that also returns source documents?",
        expected_answer="build_rag_chain_with_source in chains/rag.py builds the RAG chain that returns both the answer and source documents. It returns a dict with 'answer' and 'sources' keys.",
        relevant_files=["chains/rag.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_005",
        category="code_lookup",
        question="What function loads the existing ChromaDB vector store from disk?",
        expected_answer="load_vectorstore in retrieval/vectorstore.py loads the existing Chroma vector store. It checks for chroma_host in settings to decide between HTTP client and local persist directory.",
        relevant_files=["retrieval/vectorstore.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_006",
        category="code_lookup",
        question="What function creates the EnsembleRetriever combining vector search and BM25?",
        expected_answer="build_ensemble_retriever in retrieval/pipeline.py creates the EnsembleRetriever. It combines a vector MMR retriever and BM25 retriever with configurable weights (default 0.6 vector, 0.4 BM25) using Reciprocal Rank Fusion.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_007",
        category="code_lookup",
        question="Which file defines the Settings class and what configuration does it expose?",
        expected_answer="Settings is defined in config/settings.py using pydantic-settings BaseSettings. It exposes: openai_api_key, openai_api_base, llm_model (default GLM-4.7), embedding_model (default embedding-3), chroma_persist_dir, chroma_collection, chroma_host, chroma_port, and enable_rerank.",
        relevant_files=["config/settings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_008",
        category="code_lookup",
        question="Where is the synthesizer_node defined and what does it do?",
        expected_answer="synthesizer_node is defined in graph/nodes.py. It aggregates results from all agents (retrieved_chunks, analysis_results, code_outputs, search_results) into a formatted context string, then uses the SYNTHESIZER_SYSTEM_PROMPT with the LLM to generate the final_answer.",
        relevant_files=["graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="code_lookup_009",
        category="code_lookup",
        question="What function builds the complete LangGraph workflow?",
        expected_answer="build_graph in graph/builder.py builds the complete LangGraph workflow. It creates a StateGraph with AgentState, registers nodes (orchestrator, retrieval, analysis, code, search, synthesizer, human_approval), sets up conditional edges for routing, and compiles with MemorySaver checkpointer.",
        relevant_files=["graph/builder.py"],
        difficulty="medium",
    ),
    QAPair(
        id="code_lookup_010",
        category="code_lookup",
        question="Where is the get_embeddings function and what does it return?",
        expected_answer="get_embeddings is in retrieval/embeddings.py. It returns an OpenAIEmbeddings instance configured with the embedding_model from settings, the API key, and the base_url (defaulting to https://api.openai.com/v1).",
        relevant_files=["retrieval/embeddings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="code_lookup_011",
        category="code_lookup",
        question="What function wraps a retriever with multi-query expansion?",
        expected_answer="build_multiquery_retriever in retrieval/pipeline.py wraps a base retriever with MultiQueryRetriever.from_llm(), which generates multiple query variations using the LLM and deduplicates results before returning.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
    ),
    QAPair(
        id="code_lookup_012",
        category="code_lookup",
        question="Where is format_docs defined and what format does it produce?",
        expected_answer="format_docs is defined in chains/rag.py. It formats retrieved documents with the pattern '【文档 N】来自: {source}\\n{content}', joined by double newlines. If no docs are retrieved, it returns '(未检索到相关文档)'.",
        relevant_files=["chains/rag.py"],
        difficulty="easy",
    ),

    # ── explanation (12) ─────────────────────────────────────────────────────
    QAPair(
        id="explanation_001",
        category="explanation",
        question="Explain how Reciprocal Rank Fusion (RRF) is applied in the retrieval pipeline.",
        expected_answer="RRF is applied through the EnsembleRetriever in retrieval/pipeline.py. It combines a vector MMR retriever and a BM25 retriever. Each retriever returns ranked document lists, and EnsembleRetriever fuses them using RRF with configurable weights (0.6 for vector, 0.4 for BM25), re-ranking documents based on their reciprocal ranks across both lists.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_002",
        category="explanation",
        question="What does operator.add do in the AgentState TypedDict, and why is it used?",
        expected_answer="operator.add is used as an Annotated reducer for list fields like retrieved_chunks, analysis_results, code_outputs, search_results, and timestamps in AgentState. In LangGraph, when a node returns a partial state update, these fields are merged by concatenating lists (operator.add) rather than replacing, allowing multiple agents to accumulate results across graph nodes.",
        relevant_files=["graph/state.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_003",
        category="explanation",
        question="How does the orchestrator route queries to different agents?",
        expected_answer="The orchestrator_node classifies the user query intent into code_lookup, explanation, bug_analysis, or general_qa. It uses a routing_map: code_lookup → retrieval, explanation → analysis, bug_analysis → analysis, general_qa → retrieval. The next_agent field is set in the state, and the graph's conditional edge function route_by_intent reads this field to select the next node.",
        relevant_files=["graph/nodes.py", "graph/builder.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_004",
        category="explanation",
        question="What is the purpose of the synthesizer node and what inputs does it use?",
        expected_answer="The synthesizer node aggregates outputs from all specialist agents into a coherent final answer. It reads up to 5 retrieved_chunks, analysis_results, code_outputs, and search_results from state, formats them into a context string, then invokes the LLM with SYNTHESIZER_SYSTEM_PROMPT to produce final_answer. It also increments iteration_count.",
        relevant_files=["graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_005",
        category="explanation",
        question="How does build_rag_chain_with_source differ from build_rag_chain?",
        expected_answer="build_rag_chain returns only the answer string (str output). build_rag_chain_with_source returns a dict with 'answer' (str) and 'sources' (list of dicts with file_path, content_preview, metadata). It adds an extract_sources step that captures document metadata before formatting, and uses RunnableParallel to generate both the answer and source list simultaneously.",
        relevant_files=["chains/rag.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_006",
        category="explanation",
        question="What search type does the vector retriever use in the advanced pipeline, and why?",
        expected_answer="The advanced pipeline uses MMR (Max Marginal Relevance) search type via build_vector_retriever in retrieval/pipeline.py, with fetch_k = k * 4 candidates. MMR balances relevance and diversity, reducing redundant results compared to pure cosine similarity search.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_007",
        category="explanation",
        question="How does the graph handle the 'explanation' intent after retrieval?",
        expected_answer="When intent is 'explanation', the graph routes to the analysis node after retrieval. This is implemented by route_after_retrieval conditional edge in graph/builder.py: if state intent is 'explanation', it routes to 'analysis'; otherwise to 'synthesizer'. The analysis node then performs deeper code analysis before the synthesizer produces the final answer.",
        relevant_files=["graph/builder.py", "graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_008",
        category="explanation",
        question="What is the purpose of the clean_json_output function in graph/nodes.py?",
        expected_answer="clean_json_output removes markdown code block wrappers (```json\\n...\\n``` or ```\\n...\\n```) from LLM outputs before JSON parsing. GLM and other LLMs often wrap JSON responses in markdown code fences, which would cause json.loads to fail. The function strips these using regex substitution.",
        relevant_files=["graph/nodes.py"],
        difficulty="easy",
    ),
    QAPair(
        id="explanation_009",
        category="explanation",
        question="How does MultiQueryRetriever improve retrieval recall?",
        expected_answer="MultiQueryRetriever wraps a base retriever and uses the LLM to generate multiple reformulations of the original query. It then retrieves documents for each reformulated query and deduplicates the combined results. This improves recall because different phrasings capture different relevant documents that a single query might miss.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
    ),
    QAPair(
        id="explanation_010",
        category="explanation",
        question="What happens when enable_rerank is True in the retrieval pipeline?",
        expected_answer="When enable_rerank is True, build_retrieval_pipeline wraps the MultiQueryRetriever with a CrossEncoderReranker using the HuggingFace model 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'. This is wrapped in a ContextualCompressionRetriever that reranks the retrieved documents and returns only the top_n=5. If the import fails, it silently falls back to the ensemble without reranking.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="hard",
    ),
    QAPair(
        id="explanation_011",
        category="explanation",
        question="How does format_docs annotate retrieved documents?",
        expected_answer="format_docs in chains/rag.py wraps each document with a header '【文档 N】来自: {source}' where N is the 1-based index and source is from doc.metadata['file_path'] or doc.metadata['source']. Each annotated document is joined with double newlines. If the docs list is empty, it returns '(未检索到相关文档)'.",
        relevant_files=["chains/rag.py"],
        difficulty="easy",
    ),
    QAPair(
        id="explanation_012",
        category="explanation",
        question="Describe the complete data flow from user query to final answer in the multi-agent graph.",
        expected_answer="The flow is: user_query → orchestrator_node (classifies intent, sets next_agent) → routed agent (retrieval_node fetches chunks, or analysis_node for explanation/bug intents, or code_node for code generation) → synthesizer_node (aggregates all results into final_answer). The graph compiles with MemorySaver for state persistence across invocations.",
        relevant_files=["graph/builder.py", "graph/nodes.py", "graph/state.py"],
        difficulty="hard",
    ),

    # ── bug_analysis (8) ─────────────────────────────────────────────────────
    QAPair(
        id="bug_analysis_001",
        category="bug_analysis",
        question="Why does orchestrator_node have a fallback to with_structured_output?",
        expected_answer="The primary parsing path uses a custom chain: LLM output → StrOutputParser → clean_json_output (strips markdown) → json.loads → IntentClassification. This can fail if the LLM output is malformed. The fallback uses llm.with_structured_output(IntentClassification) which uses the provider's native structured output capability, which is more robust but may not be available on all providers.",
        relevant_files=["graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="bug_analysis_002",
        category="bug_analysis",
        question="What specific error does build_vectorstore catch, and how does it recover?",
        expected_answer="build_vectorstore catches ValueError with 'non-empty list' in the message string, which occurs when Chroma.from_documents fails with certain batch sizes. Recovery: creates an empty Chroma store first, then adds documents in batches of 10, continuing on batch failures. This handles GLM API limitations with large embedding batches.",
        relevant_files=["retrieval/vectorstore.py"],
        difficulty="medium",
    ),
    QAPair(
        id="bug_analysis_003",
        category="bug_analysis",
        question="Why does analysis_node escape curly braces in the code content?",
        expected_answer="analysis_node escapes curly braces with .replace('{', '{{').replace('}', '}}') before inserting code content into the f-string that creates the ChatPromptTemplate human message. LangChain's template parser treats single curly braces as variable placeholders and would raise an error if code content contains them (e.g., Python dicts, f-strings, or format strings).",
        relevant_files=["graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="bug_analysis_004",
        category="bug_analysis",
        question="What happens when retrieval_node encounters an exception during document retrieval?",
        expected_answer="retrieval_node wraps retriever.invoke() in a try/except block. On exception, it returns an error state: {'error_message': f'Retrieval error: {str(e)}', 'next_agent': 'synthesizer', 'timestamps': [...]}. The graph continues to the synthesizer, which will generate an answer with no retrieved context, gracefully degrading rather than crashing.",
        relevant_files=["graph/nodes.py"],
        difficulty="medium",
    ),
    QAPair(
        id="bug_analysis_005",
        category="bug_analysis",
        question="Why do retrieval_node, analysis_node, and synthesizer_node check if their output fields already exist in state?",
        expected_answer="These nodes check if their output fields already exist (e.g., 'if state.get(\"retrieved_chunks\"): return {}') to prevent redundant re-execution. In LangGraph, nodes can be revisited in certain graph configurations. The early return prevents duplicate API calls and ensures idempotency within a single graph invocation.",
        relevant_files=["graph/nodes.py"],
        difficulty="hard",
    ),
    QAPair(
        id="bug_analysis_006",
        category="bug_analysis",
        question="What edge case does load_vectorstore handle with the chroma_host setting?",
        expected_answer="When chroma_host is set, load_vectorstore creates a Chroma instance with client_type='http', using the host and port from settings. This routes to a remote ChromaDB server (e.g., a Docker container). When chroma_host is None, it uses the local persist directory. This allows the same code to work with both local and remote ChromaDB deployments without code changes.",
        relevant_files=["retrieval/vectorstore.py"],
        difficulty="medium",
    ),
    QAPair(
        id="bug_analysis_007",
        category="bug_analysis",
        question="Why does build_rag_chain use RunnableParallel at the start of the chain?",
        expected_answer="RunnableParallel runs the retriever and passthrough concurrently: it passes the question to the retriever (for document fetch) and simultaneously passes it through unchanged (RunnablePassthrough). This produces {'context': formatted_docs, 'question': original_question} which the rag_prompt needs. Without RunnableParallel, the question would be consumed by the retriever and lost.",
        relevant_files=["chains/rag.py"],
        difficulty="hard",
    ),
    QAPair(
        id="bug_analysis_008",
        category="bug_analysis",
        question="Why does the ingestion pipeline use a MAX_API_BATCH of 32 for sub-batching?",
        expected_answer="GLM API (Zhipu AI) has a limit of 64 items per embedding request. The code uses 32 (half the limit) as a safe margin. The main batch_size parameter (default 64) splits the total document set for ThreadPoolExecutor parallelism, while the inner MAX_API_BATCH=32 ensures each embedding API call stays under the provider's rate limit.",
        relevant_files=["retrieval/ingestion.py"],
        difficulty="hard",
    ),

    # ── general_qa (8) ───────────────────────────────────────────────────────
    QAPair(
        id="general_qa_001",
        category="general_qa",
        question="What LLM provider does this project use by default, and how is it configured?",
        expected_answer="By default the project uses GLM-4.7 from Zhipu AI (bigmodel.cn) via an OpenAI-compatible API. It is configured through the Settings class: llm_model='GLM-4.7', with openai_api_key and openai_api_base pointing to https://open.bigmodel.cn/api/paas/v4. ChatOpenAI from langchain_openai is used with a custom base_url.",
        relevant_files=["config/settings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_002",
        category="general_qa",
        question="What is the default ChromaDB collection name and persist directory?",
        expected_answer="The default collection name is 'codebase_v1' and the default persist directory is './chroma_db', both defined in config/settings.py.",
        relevant_files=["config/settings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_003",
        category="general_qa",
        question="What are the weights used in the EnsembleRetriever and what algorithm combines them?",
        expected_answer="The EnsembleRetriever uses weights of 0.6 for the vector (MMR) retriever and 0.4 for the BM25 retriever. These are combined using Reciprocal Rank Fusion (RRF), which scores each document based on its inverse rank position in each retriever's result list.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_004",
        category="general_qa",
        question="What embedding model is used by default and which API does it call?",
        expected_answer="The default embedding model is 'embedding-3', configured in Settings.embedding_model. It is called via the OpenAIEmbeddings class from langchain_openai, using the same openai_api_base as the LLM (GLM-compatible endpoint).",
        relevant_files=["config/settings.py", "retrieval/embeddings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_005",
        category="general_qa",
        question="What state field tracks how many times the graph has synthesized a response?",
        expected_answer="The iteration_count field in AgentState tracks the number of synthesizer invocations. It is incremented by 1 in synthesizer_node: 'iteration_count': state.get('iteration_count', 0) + 1.",
        relevant_files=["graph/state.py", "graph/nodes.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_006",
        category="general_qa",
        question="What default k value does the vector retriever use in the advanced pipeline, and how many fetch candidates does it use for MMR?",
        expected_answer="build_vector_retriever in retrieval/pipeline.py uses k=20 by default for the number of documents to return. For MMR, it fetches fetch_k = k * 4 = 80 candidates from the vector store before applying the MMR reranking to select the final k=20.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
    ),
    QAPair(
        id="general_qa_007",
        category="general_qa",
        question="What is the default LLM model name used throughout the system?",
        expected_answer="The default LLM model is 'GLM-4.7', set as the llm_model field default in the Settings class in config/settings.py.",
        relevant_files=["config/settings.py"],
        difficulty="easy",
    ),
    QAPair(
        id="general_qa_008",
        category="general_qa",
        question="How many retrieved chunks does the synthesizer node use when generating the final answer?",
        expected_answer="The synthesizer_node uses at most 5 chunks from retrieved_chunks (via slice [:5]). Each chunk's content is also truncated to 500 characters to limit total context length when building the aggregated_context for the LLM prompt.",
        relevant_files=["graph/nodes.py"],
        difficulty="easy",
    ),

    # ── git_history (10) ─────────────────────────────────────────────────────
    QAPair(
        id="git_history_001",
        category="git_history",
        question="What changed in commit b89548b?",
        expected_answer="Commit b89548b moved the Document import to the top of retrieval/splitters.py. This was a fix to resolve an import ordering issue where Document was used before being imported.",
        relevant_files=["retrieval/splitters.py"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_002",
        category="git_history",
        question="What major feature did commit 4e5e611 introduce?",
        expected_answer="Commit 4e5e611 introduced on-demand ingestion: the API server can now start without automatically indexing the codebase. Instead, ingestion is triggered explicitly via a POST /api/ingest endpoint, separating server startup from data ingestion.",
        relevant_files=["api/"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_003",
        category="git_history",
        question="What import was fixed in commit 87c7cf4?",
        expected_answer="Commit 87c7cf4 updated the BaseLanguageModel import to use the correct path langchain_core.language_models (plural), fixing an import that was using the wrong module path.",
        relevant_files=["graph/"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_004",
        category="git_history",
        question="What does commit bff46a3 describe about module migration?",
        expected_answer="Commit bff46a3 migrated the project to LangChain 1.0+ module structure, specifically moving to langchain-classic as the package for retrievers like EnsembleRetriever and MultiQueryRetriever that were previously in different locations.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="medium",
        requires_git=True,
    ),
    QAPair(
        id="git_history_005",
        category="git_history",
        question="What dependency and import were fixed in commit 9f0c25c?",
        expected_answer="Commit 9f0c25c added langchain to the project dependencies and corrected retriever imports that were failing due to missing or misplaced package references.",
        relevant_files=["pyproject.toml", "retrieval/"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_006",
        category="git_history",
        question="What three areas were fixed in commit edc2a42?",
        expected_answer="Commit edc2a42 (v1.0.1) fixed three areas: Logging (improved log output), Markdown Rendering (fixed rendering in the UI), and Data Flow (fixed issues in how data passes through the pipeline).",
        relevant_files=["api/", "main.py"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_007",
        category="git_history",
        question="What was delivered in commit 709d01c (Release v1.0)?",
        expected_answer="Commit 709d01c delivered the complete CodeBase Intelligence Hub v1.0, including: a UI, multi-threaded ingestion (for faster indexing), and various bug fixes that brought the system to production-ready state.",
        relevant_files=[],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_008",
        category="git_history",
        question="What retriever imports were fixed in commit 6c700d2?",
        expected_answer="Commit 6c700d2 fixed the imports of EnsembleRetriever and MultiQueryRetriever to come from langchain-community, resolving import errors from an earlier incorrect module path.",
        relevant_files=["retrieval/pipeline.py"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_009",
        category="git_history",
        question="What was added in commit ad43515?",
        expected_answer="Commit ad43515 added a comprehensive README for the CodeBase Intelligence Hub project, documenting the project overview, setup instructions, architecture, and usage.",
        relevant_files=["README.md"],
        difficulty="easy",
        requires_git=True,
    ),
    QAPair(
        id="git_history_010",
        category="git_history",
        question="What was the purpose of commit d5111f4?",
        expected_answer="Commit d5111f4 was a refactoring commit to improve code structure for better readability and maintainability, without adding new features.",
        relevant_files=[],
        difficulty="easy",
        requires_git=True,
    ),
]


def get_dataset_by_category(category: str) -> list[QAPair]:
    return [qa for qa in DATASET if qa.category == category]


def get_dataset_subset(categories: list[str]) -> list[QAPair]:
    return [qa for qa in DATASET if qa.category in categories]

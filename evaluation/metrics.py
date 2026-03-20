"""Evaluation metrics for RAG system benchmarking.

Retrieval metrics: Recall@k, Precision@k (deterministic, no LLM)
Answer quality metrics: Faithfulness, Relevance, Resolution (LLM-as-judge)
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config.settings import Settings


# ── Retrieval metrics (deterministic) ────────────────────────────────────────

def _path_matches(retrieved_path: str, relevant_file: str) -> bool:
    """Check if a retrieved path contains the relevant file as a substring.

    Handles absolute vs. relative path differences:
      "retrieval/pipeline.py" in "/abs/path/.../retrieval/pipeline.py" → True
    """
    return relevant_file in retrieved_path


def retrieval_recall_at_k(
    retrieved_file_paths: list[str],
    relevant_files: list[str],
    k: int = 5,
) -> float:
    """Fraction of relevant files found in the top-k retrieved paths.

    Args:
        retrieved_file_paths: Ordered list of retrieved file paths
        relevant_files: Gold-standard relevant file paths (relative)
        k: Cutoff rank

    Returns:
        Recall@k ∈ [0, 1], or 1.0 if relevant_files is empty
    """
    if not relevant_files:
        return 1.0
    top_k = retrieved_file_paths[:k]
    hits = sum(
        1 for f in relevant_files
        if any(_path_matches(p, f) for p in top_k)
    )
    return hits / len(relevant_files)


def retrieval_precision_at_k(
    retrieved_file_paths: list[str],
    relevant_files: list[str],
    k: int = 5,
) -> float:
    """Fraction of top-k retrieved paths that are relevant.

    Args:
        retrieved_file_paths: Ordered list of retrieved file paths
        relevant_files: Gold-standard relevant file paths (relative)
        k: Cutoff rank

    Returns:
        Precision@k ∈ [0, 1], or 0.0 if top-k is empty
    """
    if not relevant_files:
        return 1.0
    top_k = retrieved_file_paths[:k]
    if not top_k:
        return 0.0
    hits = sum(
        1 for p in top_k
        if any(_path_matches(p, f) for f in relevant_files)
    )
    return hits / len(top_k)


# ── LLM-as-judge metrics ─────────────────────────────────────────────────────

FAITHFULNESS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an impartial evaluator. Score the system answer for faithfulness
to the reference answer on a scale of 0-5.

5 = Completely faithful: all key facts match the reference
4 = Mostly faithful: minor omissions or imprecision
3 = Partially faithful: some correct facts but missing important details
2 = Mostly unfaithful: contains relevant info but misses most key points
1 = Largely wrong: answers the question but contradicts the reference
0 = Completely wrong or irrelevant

Respond with JSON only: {{"score": <int 0-5>, "reasoning": "<one sentence>"}}""",
    ),
    (
        "human",
        """Question: {question}

Reference answer: {reference_answer}

System answer: {system_answer}

Score:""",
    ),
])

RELEVANCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an impartial evaluator. Score the system answer for relevance
to the question on a scale of 0-5.

5 = Perfectly relevant: directly addresses the question
4 = Mostly relevant: answers the question with minor tangents
3 = Partially relevant: touches the topic but misses focus
2 = Weakly relevant: vaguely related to the question
1 = Mostly irrelevant: barely addresses the question
0 = Completely irrelevant

Respond with JSON only: {{"score": <int 0-5>, "reasoning": "<one sentence>"}}""",
    ),
    (
        "human",
        """Question: {question}

System answer: {system_answer}

Score:""",
    ),
])

RESOLUTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an impartial evaluator. Determine whether the system answer
successfully resolves the user's question.

Respond with JSON only: {{"score": <int 0 or 1>, "reasoning": "<one sentence>"}}
score=1 means the question is resolved, score=0 means it is not.""",
    ),
    (
        "human",
        """Question: {question}

System answer: {system_answer}

Resolution:""",
    ),
])


def _build_judge_llm(settings: Settings) -> ChatOpenAI:
    """LLM judge: same model, temperature=0 for reproducibility."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
        temperature=0,
    )


def _call_judge(prompt: ChatPromptTemplate, variables: dict, llm: ChatOpenAI) -> dict:
    """Invoke judge prompt and parse JSON response.

    Returns:
        dict with 'score' (int) and 'reasoning' (str), or error fallback
    """
    chain = prompt | llm | StrOutputParser()
    try:
        raw = chain.invoke(variables)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        return {"score": 0, "reasoning": f"Judge error: {e}"}


def judge_faithfulness(
    question: str,
    reference_answer: str,
    system_answer: str,
    settings: Settings,
) -> dict:
    """Score system answer faithfulness against reference (0–5).

    Returns:
        {"score": int, "normalized": float, "reasoning": str}
    """
    llm = _build_judge_llm(settings)
    result = _call_judge(
        FAITHFULNESS_PROMPT,
        {
            "question": question,
            "reference_answer": reference_answer,
            "system_answer": system_answer,
        },
        llm,
    )
    result["normalized"] = result.get("score", 0) / 5.0
    return result


def judge_relevance(
    question: str,
    system_answer: str,
    settings: Settings,
) -> dict:
    """Score system answer relevance to the question (0–5).

    Returns:
        {"score": int, "normalized": float, "reasoning": str}
    """
    llm = _build_judge_llm(settings)
    result = _call_judge(
        RELEVANCE_PROMPT,
        {"question": question, "system_answer": system_answer},
        llm,
    )
    result["normalized"] = result.get("score", 0) / 5.0
    return result


def judge_resolution(
    question: str,
    system_answer: str,
    settings: Settings,
) -> dict:
    """Determine if the system answer resolves the question (0 or 1).

    Returns:
        {"score": int, "reasoning": str}
    """
    llm = _build_judge_llm(settings)
    return _call_judge(
        RESOLUTION_PROMPT,
        {"question": question, "system_answer": system_answer},
        llm,
    )


def evaluate_answer(
    question: str,
    reference_answer: str,
    system_answer: str,
    settings: Settings,
    skip_llm_eval: bool = False,
) -> dict:
    """Run all three LLM judge metrics for a single answer.

    Args:
        question: User question
        reference_answer: Gold-standard expected answer
        system_answer: Answer from the system under test
        settings: LLM config
        skip_llm_eval: If True, return zeroed metrics without calling LLM

    Returns:
        dict with faithfulness, relevance, resolution sub-dicts
    """
    if skip_llm_eval:
        empty = {"score": 0, "normalized": 0.0, "reasoning": "skipped"}
        return {
            "faithfulness": empty,
            "relevance": empty,
            "resolution": {"score": 0, "reasoning": "skipped"},
        }

    return {
        "faithfulness": judge_faithfulness(question, reference_answer, system_answer, settings),
        "relevance": judge_relevance(question, system_answer, settings),
        "resolution": judge_resolution(question, system_answer, settings),
    }

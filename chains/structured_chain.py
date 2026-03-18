from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class IntentResult(BaseModel):
    intent: str = Field(description="如：code_lookup, explanation, bug_analysis")
    confidence: float = Field(ge=0, le=1, description="置信度0-1")
    reason: str = Field(description="简短理由")


def build_intent_chain(llm):
    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """对用户问题意图进行分类。返回一个 JSON 对象，包含以下字段：
- intent: 字符串，取值：code_lookup, explanation, bug_analysis
- confidence: 0-1 之间的数字，表示置信度
- reason: 字符串，简短的分类理由

只返回 JSON，不要包含任何其他文本或 markdown 代码块。""",
            ),
            ("human", "{query}"),
        ]
    )
    # structed_llm = llm.with_structured_output(IntentResult)
    structed_llm = llm.with_structured_output(IntentResult)

    return prompt | structed_llm


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    llm = ChatOpenAI(
        model="GLM-4.7",
        temperature=0,
        # model_kwargs={"response_format": {"type": "json_object"}},
    )
    chain = build_intent_chain(llm)

    result: IntentResult = chain.invoke(
        {"query": "UserService 的 login 方法在哪定义的？"}
    )
    print(result.intent, result.confidence, result.reason)


"""
普通链的 LLM 返回裸字符串，调用方需要自己解析。这条链的核心问题是：如何让 LLM 返回可直接使用的 Python
  对象，而不是字符串？

  答案是 with_structured_output。

  ---
  数据流

  输入: {"query": "UserService 的 login 方法在哪定义的？"}
           │
           ▼
        prompt                    ← 拼成消息列表交给 LLM
           │
           ▼
     structured_llm               ← LLM 返回 JSON → 自动解析为 IntentResult
           │
           ▼
  输出: IntentResult(
          intent="code_lookup",
          confidence=0.95,
          reason="..."
        )

  ---
  逐行注释

  from pydantic import BaseModel, Field
  # BaseModel: Pydantic 模型基类，定义数据结构 + 自动校验
  # Field: 为字段附加元信息（描述、约束）

  from langchain_core.prompts import ChatPromptTemplate
  # 构造多角色消息模板（system / human / ai）

  from langchain_openai import ChatOpenAI
  # OpenAI 兼容的 LLM 客户端，支持自定义 base_url


  class IntentResult(BaseModel):
      intent: str = Field(description="如：code_lookup, explanation, bug_analysis")
      # description 会被注入到 LLM 的 JSON Schema 中，引导 LLM 填什么值

      confidence: float = Field(ge=0, le=1, description="置信度0-1")
      # ge=0, le=1 是 Pydantic 约束：0 ≤ confidence ≤ 1，越界直接报错

      reason: str = Field(description="简短理由")


  def build_intent_chain(llm):
      prompt = ChatPromptTemplate.from_messages([
          ("system", "对用户问题意图进行分类, 返回 json"),
          ("human", "{query}"),   # {query} 是占位符，invoke 时填入
      ])

      structured_llm = llm.with_structured_output(IntentResult)
      # with_structured_output: 把 IntentResult 的 JSON Schema 发给 LLM
      # LLM 被约束只能返回符合该结构的 JSON
      # LangChain 自动把 JSON 字符串 → IntentResult 实例

      return prompt | structured_llm
      # 注意：这里没有 StrOutputParser()
      # 因为输出已经是 IntentResult 对象，不需要再解析字符串

  ---
  为什么这样设计

  ┌──────────────────────────────────────┬─────────────────────────────────┐
  │                普通链                │        structured_chain         │
  ├──────────────────────────────────────┼─────────────────────────────────┤
  │ 输出 str                             │ 输出 IntentResult 对象          │
  ├──────────────────────────────────────┼─────────────────────────────────┤
  │ 调用方需要 json.loads() + 手动取字段 │ 直接 result.intent              │
  ├──────────────────────────────────────┼─────────────────────────────────┤
  │ LLM 返回格式随意，可能解析失败       │ Schema 约束 + Pydantic 校验兜底 │
  └──────────────────────────────────────┴─────────────────────────────────┘

  在本项目的 RAG 系统中，这条链的作用是意图识别——判断用户是要查代码位置、要解释说明、还是要分析 bug，下游
   Agent 根据 intent 字段路由到不同处理分支。
"""

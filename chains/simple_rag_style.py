from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import (
    Runnable,
    RunnablePassthrough,
    RunnableParallel,
)
from langchain_openai import ChatOpenAI


def build_simple_rag_chain(llm) -> Runnable[dict, str]:
    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你根据以下上下文回答用户问题。如果上下文中没有相关信息，请说明。
上下文：
{context}
""",
            ),
            ("human", "{question}"),
        ]
    )

    return (
        RunnablePassthrough.assign(
            context=lambda x: x.get("context", "(无)"),
        )
        | prompt
        | llm
        | StrOutputParser()
    )


def build_parallel_chain(llm) -> Runnable[dict, str]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "上下文：{context}\n额外信息：{extra}"),
            ("human", "{question}"),
        ]
    )

    setup: RunnableParallel = RunnableParallel(
        context=RunnablePassthrough.assign(
            context=lambda x: x.get("context", ""),
        )
        | (lambda x: x["context"]),
        question=RunnablePassthrough().pick("question"),
        extra=lambda x: x.get("extra", "无"),
    )

    def merge(inputs):
        return {
            "context": inputs["context"]
            if isinstance(inputs["context"], str)
            else inputs.get("context", ""),
            "question": inputs["question"],
            "extra": inputs.get("extra", "无"),
        }

    return setup | merge | prompt | llm | StrOutputParser()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    llm = ChatOpenAI(model="GLM-4.7", temperature=0)
    # chain = build_simple_rag_chain(llm)
    chain = build_parallel_chain(llm)
    out = chain.invoke(
        {
            "context": "本项目使用 Langchain 和 langgraph 构建代码库问答",
            "question": "这个项目使用了什么技术?",
        }
    )
    print(out)


"""
解释build_parallel_chain 是如何设计的

⏺ 结合代码逐层解释：

  输入 dict: { context, question, extra }
           │
           ▼
  ┌─────────────────────────────────────────┐
  │           RunnableParallel (setup)      │  ← 三路并行，同时处理同一份输入
  │                                         │
  │  context  = assign + lambda 取出字符串  │
  │  question = passthrough.pick("question")│
  │  extra    = lambda 取 extra 字段        │
  └──────────────┬──────────────────────────┘
                 │ 输出新 dict: { context, question, extra }
                 ▼
             merge()                         ← 纯函数，规范化字段、填默认值
                 │
                 ▼
             prompt                          ← 填入三个占位符
                 │
                 ▼
              llm
                 │
                 ▼
         StrOutputParser()                   ← 输出 str

  ---
  各部分的作用：

  RunnableParallel — 对同一个输入并行跑三条支路，结果合并成一个新 dict：

  - context 支路：用 assign 补默认值 → lambda 把整个 dict 降维成单个字符串
  - question 支路：pick("question") 只保留 question 字段，丢弃其他
  - extra 支路：lambda 直接取 extra，缺失时返回 "无"

  merge() — 因为 context
  支路经过了两次变换，类型可能不确定，这里做一次防御性规范化，确保三个字段都是
  str，格式正确再交给 prompt。

  为什么这样设计（vs build_simple_rag_chain）：

  ┌──────────┬─────────────┬──────────────┐
  │          │   simple    │   parallel   │
  ├──────────┼─────────────┼──────────────┤
  │ 输入处理 │ 串行 assign │ 三路并行     │
  ├──────────┼─────────────┼──────────────┤
  │ 额外字段 │ 无          │ 支持 extra   │
  ├──────────┼─────────────┼──────────────┤
  │ 适用场景 │ 单一上下文  │ 多源信息聚合 │
  └──────────┴─────────────┴──────────────┘

  RunnableParallel 的价值在实际 RAG
  场景中更明显——比如同时从向量库、数据库、工具调用三路并发取数据，再合并送给
  LLM，避免串行等待。
"""

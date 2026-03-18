from config.settings import Settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI


def main() -> None:
    settings: Settings = Settings()
    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(  # type: ignore[assignment]
        [
            ("system", "你是一个代码库助手, 用简洁的中文回答"),
            ("human", "{question}"),
        ]
    )
    llm: ChatOpenAI = ChatOpenAI(
        model="GLM-4.7",
        temperature=0,
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
    )

    parser: StrOutputParser = StrOutputParser()

    chain: RunnableSerializable[dict, str] = prompt | llm | parser

    answer: str = chain.invoke({"question": "什么是 RAG? 用一句话说明."})
    print(answer)


if __name__ == "__main__":
    main()

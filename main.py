import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv()


def main():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一个代码库助手, 用简洁的中文回答"),
            ("human", "{question}"),
        ]
    )
    llm = ChatOpenAI(
        model="GLM-4.7",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )

    parser = StrOutputParser()

    chain = prompt | llm | parser

    answer = chain.invoke({"question": "什么是 RAG? 用一句话说明."})
    print(answer)


if __name__ == "__main__":
    main()

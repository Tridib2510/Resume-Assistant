from langchain.tools import tool
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_classic.prompts import ChatPromptTemplate

load_dotenv()


def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", api_key=os.environ['GROQ_API_KEY'])


@tool
def resume_parser(user_id: str, question: str) -> dict:
    """
    Parses the resume and answers questions about the candidate.
    """
    from langchain_astradb import AstraDBVectorStore
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_store = AstraDBVectorStore(
        collection_name="langchain_integration_demo",
        embedding=embeddings,
        token=os.environ['ASTRA_DB_APPLICATION_TOKEN'],
        api_endpoint=os.environ['ASTRA_DB_API_ENDPOINT'],
        namespace=os.environ['ASTRA_DB_KEYSPACE'],
    )

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"filter": {"user_id": user_id}}
    )

    llm = get_llm()

    SYSTEM_PROMPT = """
    You are a resume assistant.
    Use the following pieces of retrieved context to answer the question.
    If you don't know the answer just say that you don't know, don't fabricate anything.
    {context}
    """

    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{input}")])

    rag_chain = (
        {
            "context": RunnableLambda(lambda x: x["input"]) | retriever,
            "input": RunnablePassthrough()
        }
        | prompt
        | llm
    )

    res = rag_chain.invoke({"input": question})

    return {
        "answer": res.content if hasattr(res, 'content') else str(res)
    }


tools = [resume_parser]
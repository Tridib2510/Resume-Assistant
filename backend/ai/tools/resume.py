from langchain.tools import tool
from langchain_groq import ChatGroq
from ai.state import AgentState
from pydantic import BaseModel,Field
from typing import List
import os
from dotenv import load_dotenv
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_classic.prompts import ChatPromptTemplate

class Answer(BaseModel):
    name:str=Field(...,description="Name of the candidate")
    email:str=Field(...,description="Email of the candidate")
    phone:str=Field(...,description="Phone number of the candidate")
    skills:str=Field(...,description="Give the Technical skills that the candidate has")
    projects:List[str]=[Field(...,description="List of projects that the candidate has worked on")]
    links:List[str]=[Field(...,description="List of links that the candidate has provided")]


def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile",api_key=os.environ['GROQ_API_KEY'])

@tool
def resume_parser(state:AgentState):
    """
    Parses the resume using structured output
    """
    docs=state['documents']
    llm=get_llm()
    retriever=state['retriever']

    SYSTEM_PROMPT="""
    You are a resume assistant .
    Use the following pieces of retrieved context to answer the question. If you don't know the answer just say that you don't know don't fabricate anything
    {context}
    """

    llm_with_structure=llm.with_structured_output(Answer)
    prompt=ChatPromptTemplate.from_messages([("system",SYSTEM_PROMPT),("human","{input}")])

    rag_chain = (
    {
        "context":  RunnableLambda(lambda x: x["question"]) | retriever, ## before sending to retriver expects text not dictionary so before sending to retriver we only extract the text first through RunnableLambda(lambda x: x["input"])
        "input": RunnablePassthrough()
    }
    | prompt
    | llm_with_structure
    )

    res=rag_chain.invoke({"input":"Tell me about the applicant"})

    return {
        "answer":res
    }

tools=[
    resume_parser
]
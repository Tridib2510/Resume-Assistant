from ai.state import AgentState
from ai.router import llm_with_structure
from langchain_classic.document_loaders import PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_classic.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode,tools_condition
from ai.tools.resume import tools


def route_question(state:AgentState):
    """Route question to wiki extract_resume_data or chat 
    Args:
    state(dict): The current graph state
    Returns:
    str=Next node to call
    
    """
    question=state.question

    next_node:str=llm_with_structure.invoke({"question":question})

    return next_node.datasource

def extract_resume_data(state:AgentState):
    """Extract the data from the resume
    Args:
    state(dict):The current graph state
    Returns:
    State(dict): New key added to state 
    """
    file_path=state.file_path
    loader=PyPDFLoader(file_path=file_path)
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
    docs=loader.load_and_split(text_splitter=text_splitter)
    embeddings=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb=FAISS.from_documents(documents=docs,embeddings=embeddings)
    
    retriever=vectordb.as_retriever(
        search_type="similarity"
    )

    return {
        "documents":docs,
        "retriever":retriever
    }
    

def chat(state:AgentState):
    """
    Get answers to the question regarding the applicant
    Args:
    state(dict): The current graph state

    Returns:
    State(dict): New key added to state 
    """
    question=state.question
    retriever=state.retriever

    SYSTEM_PROMPT="""
    You are a gmail assistant please answer queries based on this

    """
    prompt=ChatPromptTemplate.from_messages([("system",SYSTEM_PROMPT),("human","{input}")])

    rag_chain = (
    {
        "context":  RunnableLambda(lambda x: x["input"]) | retriever, ## before sending to retriver expects text not dictionary so before sending to retriver we only extract the text first through RunnableLambda(lambda x: x["input"])
        "input": RunnablePassthrough()
    }
    | prompt
    | llm_with_structure
    )

    res=rag_chain.invoke({"question":question})

    return {
        "answer":res
    }

def build_graph():
    workflow=StateGraph(AgentState)
    tool_node=ToolNode(tools=tools)
    workflow.add_node('extract_resume_data',extract_resume_data)
    workflow.add_node('chat',chat)
    workflow.add_node('tools',tool_node)

    workflow.add_conditional_edges(
        START,
        route_question,
        {
            'extract_resume_data':'extract_resume_data',
            'chat':'chat'
        }
    )

    workflow.add_conditional_edges(
        'extract_resume_data',
        tools_condition
        )
    workflow.add_edge('tools','extract_resume_data')
    workflow.add_edge('extract_resume_data','chat')
    workflow.add_edge('chat',END)

    graph=workflow.compile()

    return graph

graph=build_graph()

for output in graph.stream({"question":"Tell me about this person","file_path":"resume.pdf"}):
    for key,value in output.values():
        print(value)
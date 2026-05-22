from ai.state import AgentState
from ai.router import llm, llm_with_structure, question_router
from langchain_classic.document_loaders import PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_classic.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from langchain_astradb import AstraDBVectorStore
from langchain.messages import AIMessage,HumanMessage


from langgraph.prebuilt import ToolNode,tools_condition
from langchain_classic.indexes.vectorstore import VectorStoreIndexWrapper
from ai.tools.resume import tools
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
load_dotenv()
groq_api_key=os.environ['GROQ_API_KEY']

chat_history=[]

def get_vectorstore():
    embeddings=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    astra_vector_store = AstraDBVectorStore(
    collection_name="langchain_integration_demo",
    embedding=embeddings,
    token=os.environ['ASTRA_DB_APPLICATION_TOKEN'],
    api_endpoint=os.environ['ASTRA_DB_API_ENDPOINT'],
    namespace=os.environ['ASTRA_DB_KEYSPACE'],
    )
    return astra_vector_store

astra_vector_store =get_vectorstore()
retriever=astra_vector_store.as_retriever(
 search_type="similarity"
)

def route_question(state:AgentState):
    """Route question to wiki extract_resume_data or chat 
    Args:
    state(dict): The current graph state
    Returns:
    str=Next node to call
    
    """
    question=state['messages'][-1].content

    next_node:str=question_router.invoke({"question":question})

    return next_node.datasource

def extract_resume_data(state:AgentState):
    """Extract the data from the resume
    Args:
    state(dict):The current graph state
    Returns:
    State(dict): New key added to state
    """
    file_path=state['file_path']
    loader=PyPDFLoader(file_path=file_path)
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
    docs=loader.load_and_split(text_splitter=text_splitter)


    astra_vector_store.add_documents(docs)


    llm=ChatGroq(api_key=groq_api_key,model="llama-3.3-70b-versatile")
    llm=llm.bind_tools(tools)

    

    return {
        "messages":llm.invoke(state['messages']),
        "documents": [doc.page_content for doc in docs],
        "retriever": retriever
    }
    

def chat(state:AgentState):
    print('chat node')
    """
    Get answers to the question regarding the applicant
    Args:
    state(dict): The current graph state

    Returns:
    State(dict): New key added to state
    """
    question=""
    

    last_msg = state['messages'][-1]
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        question = state['messages'][-2].content
    else:
        question = last_msg.content
    
    
    

    SYSTEM_PROMPT = """
You are an advanced resume analysis assistant.

Your task is to answer questions about a candidate using:
1. Resume context
2. Previous conversation history
3. The current user question

Instructions:
- Answer ONLY using information present in the resume context or previous conversation history.
- If the answer is not available in the resume context, clearly say:
  "The resume does not contain that information."
- Maintain conversational continuity using the chat history.
- If the user refers to something indirectly like:
  "that project"
  "his last internship"
  "the previous company"
  use the chat history to resolve the reference.
- Be concise, professional, and factual.
- Highlight:
  - projects
  - skills
  - technologies
  - internships
  - achievements
  - education
  when relevant.
- Do NOT invent information.
- Prefer bullet points for lists.
- If multiple relevant items exist, summarize them clearly.

==============================
Resume Context:
{context}
==============================

==============================
Chat History:
{chat_history}
==============================
"""

    prompt=ChatPromptTemplate.from_messages([("system",SYSTEM_PROMPT),("human","{input}")])

    rag_chain = (
    {
        "context": RunnableLambda(lambda x: x["input"]) | retriever,
        "chat_history":RunnableLambda(lambda x: x["chat_history"]),
        "input": RunnablePassthrough()
    }
    | prompt
    | llm
    )
    # print('question-->',(state['messages'][-1]))
    res=rag_chain.invoke({"input":question, "chat_history":chat_history})

    return {
        "answer":res,
        
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
    workflow.add_edge('tools', 'extract_resume_data')
    workflow.add_edge('extract_resume_data', 'chat')
    workflow.add_edge('chat',END)

    graph=workflow.compile()

    return graph

graph=build_graph()

user_input="Tell me about the projects done by the applicant"
chat_history.append(HumanMessage(user_input))

for event in graph.stream({
    "messages": [("user", user_input)],
    "file_path": "resume.pdf"
}):

    for node_name, state in event.items():

        
      if node_name == "chat":
        # Final answer
        if "answer" in state and state["answer"]:
            
            answer = state["answer"]

            # AIMessage -> text
            if hasattr(answer, "content"):
                print(answer.content)
                chat_history.append(AIMessage("answer.content"))
            else:
                print(answer)

        # Retrieved docs
        if "documents" in state and state["documents"]:
            print("\nRetrieved Documents:")
            for doc in state["documents"][:2]:
                print(doc[:300])
                print()
print('-------------------------------------------------')

user_input="Tell me about the last question asked"
chat_history.append(HumanMessage(user_input))


for event in graph.stream({
    "messages": [("user", user_input)]
}):

    for node_name, state in event.items():

        
      if node_name == "chat":
        # Final answer
        if "answer" in state and state["answer"]:
            
            answer = state["answer"]

            # AIMessage -> text
            if hasattr(answer, "content"):
                print(answer.content)
                chat_history.append(AIMessage(answer.content))
            else:
                print(answer)

        # Retrieved docs
        if "documents" in state and state["documents"]:
            print("\nRetrieved Documents:")
            for doc in state["documents"][:2]:
                print(doc[:300])
                print()
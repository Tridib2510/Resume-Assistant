from pydantic import BaseModel, Field
from typing import Literal
from langchain_groq import ChatGroq
from langchain_classic.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

groq_api_key=os.environ['GROQ_API_KEY']

class Router(BaseModel):
    datasource :Literal['chat','extract_resume_data']=Field(...,description="Given a user question choose to route it to wikipedia or a vectorstore")


llm=ChatGroq(api_key=groq_api_key,model="llama-3.3-70b-versatile")

llm_with_structure=llm.with_structured_output(Router)


SYSTEM_PROMPT="""
You are an expert routing assistant for a resume analysis system.

Given a user question, choose the appropriate route:

1. "extract_resume_data" - When the user provides a resume file and wants information extracted from it (e.g., skills, experience, projects, achievements)

2. "chat" - When the user asks a general question that doesn't require resume data extraction

Return one of these two values based on what the user is asking for.
"""

router_prompt=ChatPromptTemplate(
    [("system",SYSTEM_PROMPT),
     ("user","{question}")\
    ])

question_router=router_prompt | llm_with_structure 
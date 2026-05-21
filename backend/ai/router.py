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
You are an expert at routing a user question to a chat or extract_resume_data 
If the user just asks a question then direct it to chat and if the user also sends this resume then send it to extract_resume_data

"""

router_prompt=ChatPromptTemplate(
    [("system",SYSTEM_PROMPT),
     ("user","{question}")\
    ])

question_router=router_prompt | llm_with_structure 






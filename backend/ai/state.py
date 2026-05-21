from pydantic import BaseModel,Field
from typing import List,Any,Optional

class AgentState(BaseModel):
    question:str
    file_path:str
    answer:str
    documents:List[str]
    retriever:Any
from pydantic import BaseModel,Field
from typing import List,Any,Optional

class AgentState(BaseModel):
    question:str
    file_path:str
    answer:Optional[str]=None
    documents:Optional[List[str]]=Field(default_factory=list)
    retriever:Optional[Any]=None
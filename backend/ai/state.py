from pydantic import BaseModel,Field
from typing import List,Any,Optional,Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class AgentState(TypedDict):
    user_id:str
    messages: Annotated[list,add_messages]
    question:str
    file_path:str
    answer:Optional[str]=None
    documents:Optional[List[str]]=Field(default_factory=list)
    
    
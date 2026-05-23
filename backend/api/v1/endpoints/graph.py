from fastapi import APIRouter, Body, File, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ai.graph import graph
import tempfile
import os
import uuid

router = APIRouter()


async def event_generator(user_id: str, query: str, file_path: str):
    config = {"configurable": {"thread_id": user_id}}
    async for event in graph.astream({
        "messages": [("user", query)],
        "file_path": file_path,
        "user_id": user_id
    }, config=config):
        for node_name, state in event.items():
            if node_name == "chat":
                if "answer" in state and state["answer"]:
                    # LLMResponseStructure has applicant (Answer object) and generation (text)
                    result = state["answer"]
                    yield f"data: {result}"
                   
                if "documents" in state and state["documents"]:
                    for doc in state["documents"][:2]:
                        yield f"data: [DOC] {doc[:300]}\n\n"


@router.post("/upload_resume")
async def upload_resume(
    user_id: str = Body(...),
    query: str = Body(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    tmp_dir = os.path.realpath(tempfile.gettempdir())
    tmp_name = f"{uuid.uuid4().hex}.pdf"
    tmp_path = os.path.join(tmp_dir, tmp_name)

    with open(tmp_path, "wb") as f:
        f.write(await file.read())

    return StreamingResponse(
        event_generator(user_id, query, tmp_path),
        media_type="text/event-stream"
    )


class ChatRequest(BaseModel):
    user_id: str = Body(...)
    query: str = Body(...)


async def chat_event_generator(user_id: str, query: str):
    config = {"configurable": {"thread_id": user_id}}
    for event in graph.stream({
        "messages": [("user", query)],
        "user_id": user_id
    }, config=config):
        for node_name, state in event.items():
            if node_name == "chat":
                if "answer" in state and state["answer"]:
                    # For chat, use the generation field (text response) not applicant
                    result = state["answer"]
                    yield f"data: {result}"

                if "documents" in state and state["documents"]:
                    for doc in state["documents"][:2]:
                        yield f"data: [DOC] {doc[:300]}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        chat_event_generator(request.user_id, request.query),
        media_type="application/json"
    )
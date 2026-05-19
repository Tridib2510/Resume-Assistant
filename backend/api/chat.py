"""Chat API routes for the Resume Assistant."""

import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai.agent import ResumeAssistant, create_assistant
from ai.tools.resume_tools import parse_resume_file

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("truresume.chat")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    session_id: str | None = None
    user_id: str | None = None
    conversation_type: Literal["resume_build", "interview_prep", "feedback", "general"] = "general"


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    session_id: str
    status: str
    error: str | None = None


class ResumeParseResponse(BaseModel):
    """Response model for resume file parsing."""

    status: str
    file_type: str
    extracted_data: dict
    raw_length: int
    parsed_at: str
    error: str | None = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message and return the agent's response.

    Args:
        request: Chat request containing message and metadata

    Returns:
        ChatResponse: Agent response with session info
    """
    logger.info(f"Chat request | session_id={request.session_id} | conversation_type={request.conversation_type} | msg_len={len(request.message)}")

    try:
        assistant = create_assistant(
            session_id=request.session_id,
            user_id=request.user_id,
            conversation_type=request.conversation_type,
        )

        logger.debug(f"Assistant created | session_id={assistant.session_id}")
        result = assistant.invoke(request.message)

        logger.info(f"Chat response | session_id={assistant.session_id} | status={result['status']} | resp_len={len(result.get('response', ''))}")

        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            status=result["status"],
            error=result.get("error"),
        )
    except Exception as e:
        logger.error(f"Chat error | session_id={request.session_id} | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response for real-time display.

    Args:
        request: Chat request containing message and metadata

    Yields:
        str: Response chunks as they are generated
    """
    logger.info(f"Stream request | session_id={request.session_id} | conversation_type={request.conversation_type} | msg_len={len(request.message)}")

    try:
        assistant = create_assistant(
            session_id=request.session_id,
            user_id=request.user_id,
            conversation_type=request.conversation_type,
        )

        logger.debug(f"Stream assistant created | session_id={assistant.session_id}")
        return assistant.stream(request.message)
    except Exception as e:
        logger.error(f"Stream error | session_id={request.session_id} | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume/upload", response_model=ResumeParseResponse)
async def upload_resume(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ResumeParseResponse:
    """Parse a resume file (PDF or TXT) and extract structured data via the chatbot.

    Args:
        file: Resume file (PDF or TXT)
        session_id: Optional session identifier
        user_id: Optional user identifier

    Returns:
        ResumeParseResponse: Extracted resume data
    """
    logger.info(f"Resume upload | session_id={session_id} | filename={file.filename}")

    try:
        file_type = None

        if file.filename:
            if file.filename.lower().endswith(".pdf"):
                file_type = "pdf"
            elif file.filename.lower().endswith(".txt"):
                file_type = "txt"
            else:
                logger.warning(f"Unsupported file type | filename={file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Please upload a .pdf or .txt file.",
                )

        content = await file.read()
        content_size = len(content)
        logger.debug(f"File read | filename={file.filename} | size={content_size} bytes")

        # Create assistant and pass resume content for parsing via agent
        assistant = create_assistant(
            session_id=session_id,
            user_id=user_id,
            conversation_type="resume_build",
        )

        logger.debug(f"Resume assistant created | session_id={assistant.session_id}")

        # Use parse_resume_file tool directly to extract structured data
        # For PDF: pass raw bytes; for TXT: pass as decoded string
        if file_type == "pdf":
            file_content_param = content  # raw bytes for PDF
        else:
            try:
                file_content_param = content.decode("utf-8")
            except UnicodeDecodeError:
                file_content_param = content.decode("latin-1")

        tool_result = parse_resume_file.invoke({
            "file_content": file_content_param,
            "file_type": file_type,
        })

        logger.info(f"Resume parsed via tool | session_id={assistant.session_id} | status={tool_result.get('status')}")

        # Return parsed response
        return ResumeParseResponse(
            status=tool_result.get("status", "success"),
            file_type=file_type,
            extracted_data=tool_result.get("extracted_data", {}),
            raw_length=content_size,
            parsed_at=datetime.utcnow().isoformat(),
            error=tool_result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload error | session_id={session_id} | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
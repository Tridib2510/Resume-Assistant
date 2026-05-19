"""Router module for the Resume Assistant chatbot using LLM-based structured routing."""

import os
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from state import ResumeAssistantState


class RouteToNode(BaseModel):
    """Structured output for LLM-based routing decision."""

    next_node: Literal[
        "extract_resume",
        "generate_feedback",
        "interview_prep",
        "finalize_resume",
        "END",
    ] = Field(
        description="The next node in the graph to route to. Use 'END' if the conversation should terminate."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this routing decision (0.0 to 1.0)"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation for why this routing decision was made"
    )


class Router:
    """LLM-powered router that uses ChatGroq with structured output to determine next node.

    This router analyzes the conversation state and user input to intelligently route
    the conversation to the appropriate graph node.
    """

    def __init__(self):
        """Initialize the Router with ChatGroq and structured output schema."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=0.3,
        )

        self.system_prompt = """You are a routing assistant for a Resume Assistant chatbot.
Your job is to analyze the conversation and determine the appropriate next node.

Available nodes:
- extract_resume: Route here when user wants to build, create, or share resume content
- generate_feedback: Route here when user wants feedback, review, or critique of their resume
- interview_prep: Route here when user wants interview preparation or practice questions
- finalize_resume: Route here when resume is complete and ready to be finalized
- END: Route here to end the conversation gracefully

Be decisive and provide clear reasoning for your routing decision."""

        self.structured_llm = self.llm.with_structured_output(RouteToNode)

    def route(self, state: ResumeAssistantState) -> str:
        """Determine the next node based on conversation state.

        Args:
            state: Current LangGraph state containing messages and context

        Returns:
            str: Name of the next node to route to
        """
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else ""

        user_context = f"Last user message: {last_message}"

        resume_info = state.get("resume_info")
        if resume_info and hasattr(resume_info, "model_dump"):
            resume_fields = resume_info.model_dump()
            if any(resume_fields.values()):
                user_context += f"\n\nResume info already has data: {[k for k, v in resume_fields.items() if v]}"

        is_interview_mode = state.get("is_interview_mode", False)
        if is_interview_mode:
            user_context += "\n\nUser is currently in interview preparation mode."

        prompt = f"""{self.system_prompt}

{user_context}

Determine the next routing decision:"""

        try:
            result = self.structured_llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ])
            return result.next_node
        except Exception:
            return "extract_resume"


def create_router() -> Router:
    """Factory function to create a Router instance.

    Returns:
        Router: Configured router instance
    """
    return Router()
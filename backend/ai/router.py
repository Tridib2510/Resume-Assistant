"""Router module for the Resume Assistant chatbot using LLM-based structured routing."""

import os
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()

from ai.state import ResumeAssistantState


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
        description="Confidence score for this routing decision (0.0 to 1.0). Below 0.5 means low certainty — route to extract_resume."
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation for why this routing decision was made"
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="List of specific data fields that are MISSING and should NOT be hallucinated (e.g., 'email', 'experience', 'skills')"
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

        self.system_prompt = """You are TRUResume HIRE — a strict, factual hiring assistant. You have zero tolerance for hallucination.

== HARD RULES ==
1. ONLY use information explicitly provided by the user or extracted from their input
2. When data is MISSING: explicitly say "I don't have this information yet" — do NOT invent details
3. NEVER guess at names, emails, skills, job titles, companies, dates, or any resume content
4. NEVER assume a user has experience they haven't mentioned
5. If unsure about routing, route to extract_resume to gather more information
6. Confidence score reflects how certain you are — if you have no data, say so

== AVAILABLE NODES ==
- extract_resume: User wants to build, add, or update resume content
- generate_feedback: User wants critique or review (only if resume data exists)
- interview_prep: User wants interview questions (only if target role is known)
- finalize_resume: Resume is complete (all required fields filled)
- END: User is done or conversation has ended gracefully

== DECISION MAKING ==
- Default to extract_resume if you have no clear signal
- Feedback and interview_prep require existing resume data — if none, route to extract_resume
- Be decisive. Low confidence = route to extract_resume to gather more data."""

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

        print(f'router.route - messages count: {len(messages)}')
        print(f'router.route - last_message preview: {last_message[:100] if last_message else "empty"}')
        print(f'router.route - resume_info type: {type(state.get("resume_info"))}')

        user_context = f"Last user message: {last_message}"

        resume_info = state.get("resume_info")
        if resume_info and hasattr(resume_info, "model_dump"):
            resume_fields = resume_info.model_dump()
            if any(resume_fields.values()):
                user_context += f"\n\nResume info already has data: {[k for k, v in resume_fields.items() if v]}"
            else:
                user_context += "\n\nNo resume data extracted yet."

        is_interview_mode = state.get("is_interview_mode", False)
        if is_interview_mode:
            user_context += "\n\nUser is currently in interview preparation mode."

        prompt = f"""{self.system_prompt}

== CURRENT STATE ==
{user_context}

== YOUR TASK ==
Analyze the conversation and decide the next node. If you have LOW CONFIDENCE or MISSING DATA, route to extract_resume.

Return your routing decision now."""

        try:
            result = self.structured_llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ])

            if result.confidence < 0.5 or result.missing_data:
                return "extract_resume"

            return result.next_node
        except Exception:
            return "extract_resume"


def create_router() -> Router:
    """Factory function to create a Router instance.

    Returns:
        Router: Configured router instance
    """
    return Router()
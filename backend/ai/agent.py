"""Resume Assistant Agent using LangGraph.

This module provides a production-ready chatbot that assists users with:
- Resume building and editing
- Interview preparation
- Resume feedback and scoring
"""

import os
from datetime import datetime
from typing import Literal

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from ai.graph import get_resume_assistant_graph
from ai.state import (
    ConversationMetadata,
    InterviewContext,
    ResumeAssistantState,
    ResumeInfo,
)
from ai.tools import (
    calculate_resume_score,
    extract_resume_info,
    generate_resume_feedback,
    suggest_interview_questions,
    validate_resume_completeness,
)

LLM_MODEL = "llama-3.3-70b-versatile"


def get_llm(temperature: float = 0.7) -> ChatGroq:
    """Create and configure the LLM instance.

    Args:
        temperature: Sampling temperature (0 = deterministic, 1 = creative)

    Returns:
        ChatGroq: Configured LLM instance
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    return ChatGroq(
        model=LLM_MODEL,
        api_key=api_key,
        temperature=temperature,
    )


def create_system_prompt(conversation_type: Literal["resume_build", "interview_prep", "feedback", "general"] = "general") -> str:
    """Create a context-aware system prompt based on conversation type.

    Args:
        conversation_type: Type of conversation being conducted

    Returns:
        str: System prompt for the agent
    """
    base_prompt = """You are a professional resume assistant helping users with:
- Building and polishing resumes
- Interview preparation
- Career advice and feedback

Be conversational but professional. Ask clarifying questions when needed.
Focus on actionable advice and specific improvements.
When extracting information, be thorough but empathetic about sensitive topics."""

    type_specific = {
        "resume_build": """
You are helping the user build their resume. Extract information naturally through conversation.
Ask about: contact details, work history, education, skills, and certifications.
Ensure all critical resume sections are complete before finalizing.""",
        "interview_prep": """
You are helping the user prepare for interviews. Ask about their target role, company, and experience level.
Generate relevant practice questions and provide tips for answering.""",
        "feedback": """
You are reviewing the user's existing resume or CV content. Provide specific, actionable feedback.
Focus on: clarity, impact, completeness, and ATS optimization.""",
        "general": """
You are having a general career assistance conversation. Be helpful and adaptive.""",
    }

    return base_prompt + "\n\n" + type_specific.get(conversation_type, type_specific["general"])


class ResumeAssistant:
    """Production Resume Assistant chatbot using LangGraph."""

    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        conversation_type: Literal["resume_build", "interview_prep", "feedback", "general"] = "general",
    ):
        """Initialize the Resume Assistant.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            conversation_type: Type of conversation
        """
        self.session_id = session_id or self._generate_session_id()
        self.user_id = user_id
        self.conversation_type = conversation_type

        self.llm = get_llm()
        self.system_prompt = create_system_prompt(conversation_type)
        self._initial_state: ResumeAssistantState = self._create_initial_state()
        self.graph = get_resume_assistant_graph()

        self.agent = create_react_agent(
            model=self.llm,
            tools=[
                extract_resume_info,
                calculate_resume_score,
                suggest_interview_questions,
                generate_resume_feedback,
                validate_resume_completeness,
            ],
            state_modifier=self.system_prompt,
        )

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def _create_initial_state(self) -> ResumeAssistantState:
        """Create the initial state for a new conversation."""
        return ResumeAssistantState(
            messages=[],
            resume_info=ResumeInfo(),
            interview_context=InterviewContext(),
            metadata=ConversationMetadata(
                session_id=self.session_id,
                created_at=datetime.utcnow().isoformat(),
                user_id=self.user_id,
                conversation_type=self.conversation_type,
            ),
            needs_resume_review=False,
            is_interview_mode=False,
            resume_complete=False,
            error=None,
            retry_count=0,
            context_window_used=0,
        )

    def invoke(self, user_input: str) -> dict:
        """Process user input and return agent response.

        Args:
            user_input: User's message

        Returns:
            dict: Response containing message, state updates, and metadata
        """
        self._initial_state["messages"] = self._initial_state["messages"] + [HumanMessage(content=user_input)]

        try:
            result = self.agent.invoke(self._initial_state)

            ai_message = result.get("messages", [])[-1].content if result.get("messages") else "No response generated"

            return {
                "response": ai_message,
                "session_id": self.session_id,
                "state": result,
                "status": "success",
            }
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}. Please try again.",
                "session_id": self.session_id,
                "status": "error",
                "error": str(e),
            }

    def stream(self, user_input: str):
        """Stream agent response for real-time display.

        Args:
            user_input: User's message

        Yields:
            str: Response chunks as they are generated
        """
        self._initial_state["messages"] = self._initial_state["messages"] + [HumanMessage(content=user_input)]

        try:
            for event in self.agent.stream(self._initial_state):
                if "messages" in event:
                    for message in event["messages"]:
                        if hasattr(message, "content") and message.content:
                            yield message.content
        except Exception as e:
            yield f"Error: {str(e)}"

    def reset(self) -> None:
        """Reset the conversation state for a new session."""
        self._initial_state = self._create_initial_state()


def create_assistant(
    session_id: str | None = None,
    user_id: str | None = None,
    conversation_type: Literal["resume_build", "interview_prep", "feedback", "general"] = "general",
) -> ResumeAssistant:
    """Factory function to create a Resume Assistant instance.

    Args:
        session_id: Optional session identifier
        user_id: Optional user identifier
        conversation_type: Type of conversation

    Returns:
        ResumeAssistant: Configured assistant instance
    """
    return ResumeAssistant(
        session_id=session_id,
        user_id=user_id,
        conversation_type=conversation_type,
    )
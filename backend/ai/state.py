"""Production-level state definitions for the Resume Assistant chatbot."""

from typing import Annotated, Literal, TypedDict
from langgraph.graph import add_messages
from langgraph.graph.message import Messages
from pydantic import BaseModel, Field


class ResumeInfo(BaseModel):
    """Structured resume information extracted from user input."""
    name: str | None = Field(default=None, description="Candidate's full name")
    email: str | None = Field(default=None, description="Candidate's email address")
    phone: str | None = Field(default=None, description="Candidate's phone number")
    location: str | None = Field(default=None, description="Candidate's location/city")
    summary: str | None = Field(default=None, description="Professional summary")
    skills: list[str] = Field(default_factory=list, description="Technical and soft skills")
    experience: list[dict] = Field(default_factory=list, description="Work experience entries")
    education: list[dict] = Field(default_factory=list, description="Education entries")
    certifications: list[str] = Field(default_factory=list, description="Professional certifications")


class InterviewContext(BaseModel):
    """Context about the interview conversation."""
    role_target: str | None = Field(default=None, description="Target job role/position")
    company: str | None = Field(default=None, description="Target company")
    experience_level: Literal["entry", "mid", "senior", "lead", "executive"] | None = Field(default=None)
    industry: str | None = Field(default=None, description="Target industry")
    questions_answered: int = Field(default=0, description="Number of questions answered in interview")


class ConversationMetadata(BaseModel):
    """Metadata about the conversation session."""
    session_id: str | None = Field(default=None, description="Unique session identifier")
    created_at: str | None = Field(default=None, description="Session creation timestamp")
    user_id: str | None = Field(default=None, description="User identifier")
    conversation_type: Literal["resume_build", "interview_prep", "feedback", "general"] = Field(
        default="general", description="Type of conversation"
    )


class ResumeAssistantState(TypedDict):
    """Main state for the Resume Assistant chatbot.

    This state is designed for production use with:
    - Structured message history (using add_messages for proper message handling)
    - Extracted resume information
    - Interview context
    - Conversation metadata
    - Configurable flags for workflow control
    - Error handling support
    """

    # Message handling with proper LangGraph add_messages reducer
    # This handles deduplication and proper message sequence management
    messages: Annotated[Messages, add_messages]

    # Structured data extracted from conversation
    resume_info: ResumeInfo
    interview_context: InterviewContext

    # Session metadata
    metadata: ConversationMetadata

    # Workflow control flags
    needs_resume_review: bool = False
    is_interview_mode: bool = False
    resume_complete: bool = False

    # Error tracking for production resilience
    error: str | None = None
    retry_count: int = 0

    # Context window management
    context_window_used: int = 0


class StateConfig:
    """Configuration constants for state management."""

    MAX_RETRIES = 3
    MAX_CONTEXT_WINDOW = 128_000  # Tokens (approximate)
    DEFAULT_TEMPERATURE = 0.7
    RESUME_COMPLETION_THRESHOLD = 0.8  # 80% of fields filled


def validate_state_transition(current_state: ResumeAssistantState, new_data: dict) -> bool:
    """Validate that a state transition is allowed.

    Args:
        current_state: The current state snapshot
        new_data: New data being added to the state

    Returns:
        bool: Whether the transition is valid
    """
    # Prevent invalid state mutations
    if current_state.get("resume_complete") and not new_data.get("resume_complete", True):
        return False
    return True


def calculate_resume_completion(state: ResumeAssistantState) -> float:
    """Calculate the completion percentage of the resume.

    Args:
        state: Current state with resume info

    Returns:
        float: Completion percentage between 0.0 and 1.0
    """
    resume = state.get("resume_info", ResumeInfo())
    fields = {
        "name": resume.name is not None,
        "email": resume.email is not None,
        "summary": resume.summary is not None,
        "skills": len(resume.skills) > 0,
        "experience": len(resume.experience) > 0,
        "education": len(resume.education) > 0,
    }
    completed = sum(1 for v in fields.values() if v)
    return completed / len(fields)
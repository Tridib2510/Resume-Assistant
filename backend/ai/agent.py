"""Resume Assistant Agent using LangGraph.

This module provides a production-ready chatbot that assists users with:
- Resume building and editing
- Interview preparation
- Resume feedback and scoring
"""

import logging
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
from ai.tools.resume_tools import (
    calculate_resume_score,
    extract_resume_info,
    generate_resume_feedback,
    parse_resume_file,
    suggest_interview_questions,
    validate_resume_completeness,
)

logger = logging.getLogger("truresume.agent")

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
        logger.error("GROQ_API_KEY environment variable not set")
        raise ValueError("GROQ_API_KEY environment variable not set")

    logger.debug(f"Creating LLM instance | model={LLM_MODEL} | temperature={temperature}")

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
    base_prompt = """You are TRUResume HIRE — a strict, factual hiring assistant with zero tolerance for hallucination.

== HARD RULES ==
1. ONLY use information explicitly provided by the user
2. When data is MISSING: say "I don't have this information yet" — do NOT invent it
3. NEVER guess names, emails, phone numbers, addresses, dates, companies, job titles, or skills
4. NEVER assume a user has experience, education, or certifications they haven't mentioned
5. If you need information to answer, ask a specific question — do not fill gaps with assumptions
6. Be direct and professional. Hiring managers value accuracy over enthusiasm.

== BEHAVIOR BY MODE ==

RESUME BUILD MODE:
- Ask one question at a time, starting with contact information
- Confirm each piece of data before moving to the next section
- When you have enough for a section, summarize what you've gathered and ask "Anything to add?"
- Never proceed to "finalize" until all required fields are confirmed by the user

INTERVIEW PREP MODE:
- Only generate questions when the target role is confirmed
- If role is unknown, ask: "What position are you interviewing for?"
- Questions must match the stated experience level and industry

FEEDBACK MODE:
- Only provide feedback when resume data exists
- If no data: "I'd need to see your resume first to give you feedback. Would you like to share it?"
- Be specific: reference actual content they've shared, not hypothetical perfect resumes

== SAMPLE PHRASES ==
- Missing data: "I don't have your email yet — what email should I use for your contact section?"
- Unknown info: "I haven't seen your work history. Could you share your most recent role?"
- Uncertainty: "I don't have enough information about that yet. Could you tell me more?" """

    type_specific = {
        "resume_build": """
You are in RESUME BUILD MODE. Extract and confirm information section by section.
Order: contact info → summary → experience → education → skills → certifications.
Always confirm before storing data. Say "I've noted [X]. Does that sound right?" """,
        "interview_prep": """
You are in INTERVIEW PREP MODE. Ask for the target role and experience level first.
Generate practice questions only after confirming these details. """,
        "feedback": """
You are in FEEDBACK MODE. Wait for the user to share resume content.
Provide structured feedback: strengths, gaps, and specific improvements. """,
        "general": """
You are in general assistance mode. If the user wants to build a resume, start resume_build.
If they ask for interview prep, start interview_prep. If they share resume content, start feedback. """,
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

        logger.info(f"Creating ResumeAssistant | session_id={self.session_id} | user_id={self.user_id} | type={self.conversation_type}")

        self.llm = get_llm()
        self.system_prompt = create_system_prompt(conversation_type)
        self._initial_state: ResumeAssistantState = self._create_initial_state()
        self.graph = get_resume_assistant_graph()

        self.agent = create_react_agent(
            model=self.llm,
            tools=[
                extract_resume_info,
                parse_resume_file,
                calculate_resume_score,
                suggest_interview_questions,
                generate_resume_feedback,
                validate_resume_completeness,
            ],
            state_modifier=self.system_prompt,
        )

        logger.debug(f"ResumeAssistant initialized | session_id={self.session_id}")

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
        logger.info(f"Invoke | session_id={self.session_id} | input_len={len(user_input)}")

        self._initial_state["messages"] = self._initial_state["messages"] + [HumanMessage(content=user_input)]

        try:
            logger.debug(f"Agent invoking | session_id={self.session_id}")
            result = self.agent.invoke(self._initial_state)

            ai_message = result.get("messages", [])[-1].content if result.get("messages") else "No response generated"

            logger.info(f"Invoke completed | session_id={self.session_id} | resp_len={len(ai_message)}")

            return {
                "response": ai_message,
                "session_id": self.session_id,
                "state": result,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Invoke error | session_id={self.session_id} | error={str(e)}", exc_info=True)
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
        logger.info(f"Stream | session_id={self.session_id} | input_len={len(user_input)}")

        self._initial_state["messages"] = self._initial_state["messages"] + [HumanMessage(content=user_input)]

        try:
            logger.debug(f"Agent streaming | session_id={self.session_id}")
            for event in self.agent.stream(self._initial_state):
                if "messages" in event:
                    for message in event["messages"]:
                        if hasattr(message, "content") and message.content:
                            logger.debug(f"Stream chunk | session_id={self.session_id} | chunk_len={len(message.content)}")
                            yield message.content
        except Exception as e:
            logger.error(f"Stream error | session_id={self.session_id} | error={str(e)}", exc_info=True)
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

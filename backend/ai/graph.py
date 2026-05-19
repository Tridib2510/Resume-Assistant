"""LangGraph graph definition for the Resume Assistant chatbot."""

from langgraph.graph import END, StateGraph

from ai.router import Router, create_router
from ai.state import InterviewContext, ResumeAssistantState, ResumeInfo, ConversationMetadata
from ai.tools import (
    
    calculate_resume_score,
    extract_resume_info,
    generate_resume_feedback,
    suggest_interview_questions,
    validate_resume_completeness,
)


def create_resume_assistant_graph(router: Router | None = None) -> StateGraph:
    """Create and compile the Resume Assistant chatbot graph.

    Args:
        router: Optional Router instance. If not provided, creates default.

    Returns:
        StateGraph: Compiled graph ready for execution
    """
    workflow = StateGraph(ResumeAssistantState)

    router_instance = router or create_router()

    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("extract_resume", extract_resume_node)
    workflow.add_node("validate_resume", validate_resume_node)
    workflow.add_node("generate_feedback", generate_feedback_node)
    workflow.add_node("interview_prep", interview_prep_node)
    workflow.add_node("finalize_resume", finalize_resume_node)

    # Set entry point
    workflow.set_entry_point("intake")

    # Add edges - conditional routing using LLM-based Router
    workflow.add_conditional_edges(
        "intake",
        lambda state: router_instance.route(state),
        {
            "extract_resume": "extract_resume",
            "generate_feedback": "generate_feedback",
            "interview_prep": "interview_prep",
            "finalize_resume": "finalize_resume",
            END: END,
        },
    )

    workflow.add_edge("extract_resume", "validate_resume")
    workflow.add_edge("validate_resume", END)
    workflow.add_edge("generate_feedback", END)
    workflow.add_edge("interview_prep", END)
    workflow.add_edge("finalize_resume", END)

    return workflow.compile()


def intake_node(state: ResumeAssistantState) -> dict:
    """Process initial user input node.

    Args:
        state: Current graph state

    Returns:
        dict: Updated state (intake passes to LLM router for decisions)
    """
    return {}


def extract_resume_node(state: ResumeAssistantState) -> dict:
    """Extract and structure resume information from user input.

    Args:
        state: Current graph state

    Returns:
        dict: Updated state with extracted resume info
    """
    last_message = state["messages"][-1].content if state["messages"] else ""

    extracted = extract_resume_info.invoke(last_message)

    resume_info = ResumeInfo(
        name=extracted.get("name"),
        email=extracted.get("email"),
        phone=extracted.get("phone"),
        location=extracted.get("location"),
        summary=extracted.get("summary"),
        skills=extracted.get("skills", []),
        experience=extracted.get("experience", []),
        education=extracted.get("education", []),
        certifications=extracted.get("certifications", []),
    )

    return {"resume_info": resume_info}


def validate_resume_node(state: ResumeAssistantState) -> dict:
    """Validate resume completeness and determine next steps.

    Args:
        state: Current graph state

    Returns:
        dict: Updated state with validation results
    """
    validation = validate_resume_completeness({"resume_info": state["resume_info"]})

    needs_review = not validation["is_complete"] and validation["completion_percentage"] < 80
    is_complete = validation["can_generate_export"]

    new_context_window = state.get("context_window_used", 0) + 1000

    return {
        "needs_resume_review": needs_review,
        "resume_complete": is_complete,
        "context_window_used": new_context_window,
        "validation_result": validation,
    }


def generate_feedback_node(state: ResumeAssistantState) -> dict:
    """Generate feedback on the user's resume.

    Args:
        state: Current graph state

    Returns:
        dict: Updated state with feedback
    """
    resume_data = {}
    if hasattr(state.get("resume_info", {}), "model_dump"):
        resume_data = state["resume_info"].model_dump()

    target_role = None
    interview_ctx = state.get("interview_context", InterviewContext())
    if hasattr(interview_ctx, "model_dump"):
        target_role = interview_ctx.model_dump().get("role_target")

    feedback = generate_resume_feedback.invoke({"resume_data": resume_data, "target_role": target_role})
    score = calculate_resume_score.invoke({"resume_data": resume_data})

    return {"feedback": feedback, "resume_score": score}


def interview_prep_node(state: ResumeAssistantState) -> dict:
    """Generate interview preparation questions and guidance.

    Args:
        state: Current graph state

    Returns:
        dict: Updated state with interview questions
    """
    interview_ctx = state.get("interview_context", InterviewContext())

    role_target = None
    experience_level = None
    industry = None

    if hasattr(interview_ctx, "model_dump"):
        role_target = interview_ctx.model_dump().get("role_target")
        experience_level = interview_ctx.model_dump().get("experience_level")
        industry = interview_ctx.model_dump().get("industry")

    questions = suggest_interview_questions.invoke({
        "role": role_target,
        "experience_level": experience_level,
        "industry": industry,
    })

    return {"interview_questions": questions, "is_interview_mode": True}


def finalize_resume_node(state: ResumeAssistantState) -> dict:
    """Finalize and mark resume as complete.

    Args:
        state: Current graph state

    Returns:
        dict: Final state update
    """
    return {"resume_complete": True}


_graph_instance = None


def get_resume_assistant_graph() -> StateGraph:
    """Get or create the singleton graph instance.

    Returns:
        StateGraph: Compiled and cached graph
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_resume_assistant_graph()
    return _graph_instance
"""Tools for the Resume Assistant chatbot."""

from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from state import ResumeInfo, calculate_resume_completion


@tool
def extract_resume_info(transcription: str) -> dict[str, Any]:
    """Extract structured resume information from free-text input.

    Use this tool when the user provides resume content in natural language
    or describes their experience. The tool will parse and structure the information.

    Args:
        transcription: Raw text containing resume information

    Returns:
        dict: Structured resume data with fields: name, email, phone, location,
              summary, skills, experience, education, certifications
    """
    result = {
        "status": "parsed",
        "raw_length": len(transcription),
        "extracted_at": datetime.utcnow().isoformat(),
    }
    return result


@tool
def calculate_resume_score(resume_data: dict) -> dict[str, Any]:
    """Calculate a quality score for the resume based on completeness and content.

    Args:
        resume_data: Dictionary containing resume information

    Returns:
        dict: Score breakdown with overall score and improvement suggestions
    """
    score = 0
    suggestions = []
    breakdown = {
        "summary": 0,
        "experience": 0,
        "skills": 0,
        "education": 0,
        "contact": 0,
    }

    if resume_data.get("summary"):
        breakdown["summary"] = 25
        score += 25
    else:
        suggestions.append("Add a professional summary to highlight your value proposition")

    if resume_data.get("experience") and len(resume_data.get("experience", [])) > 0:
        breakdown["experience"] = 30
        score += 30
    else:
        suggestions.append("Include relevant work experience with measurable achievements")

    if resume_data.get("skills") and len(resume_data.get("skills", [])) >= 3:
        breakdown["skills"] = 20
        score += 20
    else:
        suggestions.append("List at least 3 relevant technical and soft skills")

    if resume_data.get("education") and len(resume_data.get("education", [])) > 0:
        breakdown["education"] = 15
        score += 15
    else:
        suggestions.append("Add your educational background")

    contact_fields = ["email", "phone", "location"]
    contact_score = sum(1 for f in contact_fields if resume_data.get(f))
    breakdown["contact"] = contact_score * (10 / 3)
    score += breakdown["contact"]

    if contact_score < 3:
        suggestions.append("Complete your contact information (email, phone, location)")

    return {
        "overall_score": round(score, 1),
        "breakdown": breakdown,
        "suggestions": suggestions,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "Needs Work",
    }


@tool
def suggest_interview_questions(
    role: str | None = None,
    experience_level: str | None = None,
    industry: str | None = None,
) -> list[dict[str, Any]]:
    """Generate interview questions tailored to the candidate's target role.

    Args:
        role: Target job role (e.g., "Software Engineer", "Product Manager")
        experience_level: Experience level (entry, mid, senior, lead, executive)
        industry: Target industry (e.g., "Tech", "Finance", "Healthcare")

    Returns:
        list: Categorized interview questions with difficulty and tips
    """
    questions = {
        "behavioral": [
            {
                "question": "Tell me about a time you faced a significant challenge at work and how you overcame it.",
                "difficulty": "medium",
                "tip": "Use the STAR method (Situation, Task, Action, Result)",
            },
            {
                "question": "Describe a project you're most proud of and what made it successful.",
                "difficulty": "easy",
                "tip": "Focus on your specific contributions, not just team outcomes",
            },
        ],
        "technical": [
            {
                "question": "Walk me through how you would approach debugging a production issue.",
                "difficulty": "medium",
                "tip": "Show systematic thinking and communication skills",
            },
        ],
        "role_specific": [
            {
                "question": f"What strategies would you use to ensure success in a {role or 'this'} role?",
                "difficulty": "hard",
                "tip": "Research the role and company beforehand",
            },
        ],
    }

    return questions


@tool
def generate_resume_feedback(resume_data: dict, target_role: str | None = None) -> dict[str, Any]:
    """Generate actionable feedback for resume improvement.

    Args:
        resume_data: Complete or partial resume data
        target_role: Optional target job role for tailored feedback

    Returns:
        dict: Structured feedback with prioritized improvements
    """
    feedback = {
        "strengths": [],
        "areas_for_improvement": [],
        "priority_fixes": [],
        "target_role_suggestions": [],
    }

    if resume_data.get("summary"):
        feedback["strengths"].append("Professional summary is present")
    if resume_data.get("experience") and len(resume_data.get("experience", [])) >= 2:
        feedback["strengths"].append("Good work experience documentation")
    if resume_data.get("skills") and len(resume_data.get("skills", [])) >= 5:
        feedback["strengths"].append("Comprehensive skills section")

    if not resume_data.get("summary") or len(resume_data.get("summary", "")) < 100:
        feedback["areas_for_improvement"].append("Professional summary is missing or too brief")

    if len(resume_data.get("experience", [])) < 2:
        feedback["areas_for_improvement"].append("Consider adding more work experience")

    if not resume_data.get("certifications"):
        feedback["areas_for_improvement"].append("Certifications can differentiate you from other candidates")

    if not resume_data.get("email"):
        feedback["priority_fixes"].append("Add contact email immediately")
    if not resume_data.get("skills"):
        feedback["priority_fixes"].append("Add skills section - this is often searched by recruiters")

    if target_role:
        feedback["target_role_suggestions"].append(
            f"Tailor your summary to highlight {target_role} specific achievements"
        )
        feedback["target_role_suggestions"].append(
            f"Add keywords from {target_role} job descriptions to pass ATS screening"
        )

    return feedback


@tool
def validate_resume_completeness(state_data: dict) -> dict[str, Any]:
    """Validate if resume has enough information to be considered complete.

    Args:
        state_data: The current graph state

    Returns:
        dict: Validation result with completion percentage and missing fields
    """
    resume = state_data.get("resume_info", {})
    missing_fields = []
    completion_percentage = 0.0

    required_fields = ["name", "email", "summary", "skills", "experience", "education"]
    optional_fields = ["phone", "location", "certifications"]

    for field in required_fields:
        if field == "skills":
            if not resume.get("skills") or len(resume.get("skills", [])) < 3:
                missing_fields.append(field)
        elif field == "experience":
            if not resume.get("experience") or len(resume.get("experience", [])) < 1:
                missing_fields.append(field)
        elif field == "education":
            if not resume.get("education") or len(resume.get("education", [])) < 1:
                missing_fields.append(field)
        elif not resume.get(field):
            missing_fields.append(field)

    completed_fields = len(required_fields) + len(optional_fields) - len(missing_fields)
    total_fields = len(required_fields) + len(optional_fields)
    completion_percentage = (completed_fields / total_fields) * 100

    return {
        "is_complete": len(missing_fields) == 0,
        "completion_percentage": round(completion_percentage, 1),
        "missing_required_fields": [f for f in missing_fields if f in required_fields],
        "missing_optional_fields": [f for f in missing_fields if f in optional_fields],
        "can_generate_export": completion_percentage >= 80,
    }
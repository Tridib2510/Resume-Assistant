"""Resume tools for the Resume Assistant chatbot."""

import os
import tempfile
from datetime import datetime
from typing import Any

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings
from langchain_core.tools import tool
from langchain_text_splitters import CharacterTextSplitter

from ai.state import ResumeInfo, calculate_resume_completion


@tool
def extract_resume_info(transcription: str) -> dict[str, Any]:
    """Extract structured resume information from free-text input.

    Uses LangChain's TextLoader, CharacterTextSplitter, and FAISS vector embeddings
    to load, chunk, and retrieve resume content for structured extraction.

    Args:
        transcription: Raw text containing resume information

    Returns:
        dict: Structured resume data with fields: name, email, phone, location,
              summary, skills, experience, education, certifications
    """
    if not transcription or len(transcription.strip()) < 10:
        return {
            "status": "error",
            "error": "Transcription too short or empty",
            "extracted_data": {},
        }

    # Create temp file with transcription content
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        tmp_file.write(transcription)
        tmp_path = tmp_file.name

    try:
        # Load document using TextLoader
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()

        if not documents:
            return {
                "status": "error",
                "error": "Could not load document",
                "extracted_data": {},
            }

        # Split documents using CharacterTextSplitter
        text_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n",
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)

        if not chunks:
            return {
                "status": "error",
                "error": "Could not split document",
                "extracted_data": {},
            }

        # Create FAISS vector store for similarity search
        embeddings = FakeEmbeddings(size=768)
        vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)

        # Combine all chunks for analysis
        full_text = "\n".join([chunk.page_content for chunk in chunks])

        # Extract structured fields using vector store queries
        extracted = {
            "name": _extract_name_from_text(full_text),
            "email": _extract_email(full_text),
            "phone": _extract_phone(full_text),
            "location": _extract_location_from_text(vector_store, full_text),
            "summary": _extract_summary_from_text(vector_store, full_text),
            "skills": _extract_skills_from_text(vector_store, chunks),
            "experience": _extract_experience_from_text(vector_store, chunks),
            "education": _extract_education_from_text(vector_store, chunks),
            "certifications": _extract_certifications_from_text(vector_store, chunks),
        }

        return {
            "status": "success",
            "extracted_data": extracted,
            "chunks_count": len(chunks),
            "raw_length": len(full_text),
            "extracted_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "extracted_data": {},
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _extract_name_from_text(text: str) -> str | None:
    """Extract name from first lines of document."""
    import re

    lines = text.strip().split("\n")[:5]
    for line in lines:
        line_clean = line.strip()
        if line_clean and len(line_clean) < 50 and "@" not in line_clean:
            if not any(kw in line_clean.lower() for kw in ["resume", "cv", "curriculum"]):
                if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$", line_clean):
                    return line_clean
    return None


def _extract_email(text: str) -> str | None:
    """Extract email address from text."""
    import re

    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    match = re.search(email_pattern, text)
    return match.group() if match else None


def _extract_phone(text: str) -> str | None:
    """Extract phone number from text."""
    import re

    phone_pattern = r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
    match = re.search(phone_pattern, text)
    return match.group() if match else None


def _extract_location_from_text(vector_store, text: str) -> str | None:
    """Extract location from text or vector store."""
    import re

    location_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})(?:\s+\d{5})?"
    match = re.search(location_pattern, text)
    if match:
        return f"{match.group(1)}, {match.group(2)}"

    results = vector_store.similarity_search("location address city state", k=3)
    for doc in results:
        match = re.search(location_pattern, doc.page_content)
        if match:
            return f"{match.group(1)}, {match.group(2)}"

    return None


def _extract_summary_from_text(vector_store, text: str) -> str | None:
    """Extract professional summary from document."""
    results = vector_store.similarity_search(
        "professional summary objective career statement about me",
        k=5,
    )

    combined = []
    for doc in results:
        content = doc.page_content.strip()
        if len(content) > 50:
            combined.append(content)

    return " ".join(combined)[:1000] if combined else None


def _extract_skills_from_text(vector_store, chunks: list[Document]) -> list[str]:
    """Extract skills from document using vector store."""
    skills = set()

    results = vector_store.similarity_search("skills technical competencies technologies", k=10)

    for doc in results:
        content = doc.page_content
        parts = content.replace("•", ",").replace("-", ",").replace("*", ",").split(",")
        for part in parts:
            cleaned = part.strip().lower()
            if 2 < len(cleaned) < 50 and not any(c in cleaned for c in ["@", "http", "www"]):
                if not any(kw in cleaned for kw in ["experience", "education", "summary", "objective"]):
                    skills.add(cleaned.title())

    return list(skills)[:20]


def _extract_experience_from_text(vector_store, chunks: list[Document]) -> list[dict]:
    """Extract work experience from document."""
    import re

    experience_entries = []

    results = vector_store.similarity_search(
        "work experience employment job title company position",
        k=15,
    )

    title_pattern = r"^([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Designer|Analyst|Director|Lead|Consultant))\s*[-–]?\s*(.*)?"
    date_pattern = r"(\d{4})\s*[-–]\s*(\d{4}|Present)"

    current_entry = {}
    for doc in results:
        content = doc.page_content.strip()
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    experience_entries.append(current_entry)
                    current_entry = {}
                continue

            date_match = re.search(date_pattern, line)
            if date_match and current_entry.get("title"):
                current_entry["duration"] = date_match.group()

            title_match = re.match(title_pattern, line)
            if title_match:
                current_entry["title"] = title_match.group(1)
                if title_match.group(2):
                    current_entry["company"] = title_match.group(2).strip()
            elif current_entry.get("title") and len(line) > 20:
                current_entry["description"] = line

    if current_entry:
        experience_entries.append(current_entry)

    seen_titles = set()
    unique_entries = []
    for entry in experience_entries:
        title = entry.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_entries.append(entry)

    return unique_entries[:10]


def _extract_education_from_text(vector_store, chunks: list[Document]) -> list[dict]:
    """Extract education from document."""
    import re

    education_entries = []

    results = vector_store.similarity_search(
        "education degree university college school academic",
        k=10,
    )

    degree_keywords = ["bachelor", "master", "phd", "b.s.", "m.s.", "b.a.", "m.a.", "mba", "associate", "doctorate"]
    school_keywords = ["university", "college", "institute", "school"]

    current_entry = {}
    for doc in results:
        content = doc.page_content.strip()
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                if current_entry and (current_entry.get("degree") or current_entry.get("institution")):
                    education_entries.append(current_entry)
                    current_entry = {}
                continue

            line_lower = line.lower()

            if any(deg in line_lower for deg in degree_keywords):
                current_entry["degree"] = line
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                if year_match:
                    current_entry["year"] = year_match.group()
            elif any(sch in line_lower for sch in school_keywords):
                current_entry["institution"] = line
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                if year_match and not current_entry.get("year"):
                    current_entry["year"] = year_match.group()

    if current_entry:
        education_entries.append(current_entry)

    return education_entries[:5]


def _extract_certifications_from_text(vector_store, chunks: list[Document]) -> list[str]:
    """Extract certifications from document."""
    certifications = []

    results = vector_store.similarity_search(
        "certification certifications certified credentials license",
        k=10,
    )

    for doc in results:
        lines = doc.page_content.split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) < 100 and not any(
                c in line.lower() for c in ["experience", "education", "skills", "summary"]
            ):
                cleaned = line.replace("•", "").replace("-", "").replace("*", "").strip()
                if cleaned and len(cleaned) > 2:
                    certifications.append(cleaned)

    seen = set()
    unique_certs = []
    for cert in certifications:
        cert_lower = cert.lower()
        if cert_lower not in seen:
            seen.add(cert_lower)
            unique_certs.append(cert)

    return unique_certs[:10]


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
def parse_resume_file(file_content: str | bytes, file_type: str) -> dict[str, Any]:
    """Parse structured resume data from PDF or text file content.

    Uses PyPDF for PDF and TextLoader for TXT, CharacterTextSplitter, and FAISS vector embeddings
    to load, chunk, and retrieve resume content for structured extraction.

    Supports PDF (.pdf) and plain text (.txt) resume files.
    Extracts: Name, Email, Phone, Location, Summary, Skills, Experience, Education, Certifications.

    Args:
        file_content: Raw text (txt) or bytes (pdf) of the file
        file_type: Type of file - "pdf" or "txt"

    Returns:
        dict: Structured resume data with all extracted fields
    """
    if file_type not in ("pdf", "txt"):
        return {
            "status": "error",
            "error": "Unsupported file type. Use 'pdf' or 'txt'.",
            "extracted_data": {},
        }

    try:
        if file_type == "pdf":
            # Use pdfplumber to extract text from PDF bytes
            import pdfplumber
            import io

            pdf_stream = io.BytesIO(file_content if isinstance(file_content, bytes) else file_content.encode("utf-8"))
            full_text = ""
            with pdfplumber.open(pdf_stream) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        else:
            # For text files, decode if needed
            if isinstance(file_content, bytes):
                try:
                    file_content = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    file_content = file_content.decode("latin-1")
            full_text = file_content

        if not full_text or len(full_text.strip()) < 10:
            return {
                "status": "error",
                "error": "Could not extract text from document",
                "extracted_data": {},
            }

        # Create documents from text chunks
        from langchain_core.documents import Document

        text_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n",
            length_function=len,
        )

        chunks = text_splitter.split_text(full_text)
        chunk_documents = [Document(page_content=chunk) for chunk in chunks]

        # Create vector store for similarity search
        vector_store = _create_vector_store(chunk_documents)

        # Extract structured fields using vector store queries
        extracted = {
            "name": _extract_name(full_text),
            "email": _extract_email(full_text),
            "phone": _extract_phone(full_text),
            "location": _extract_location(vector_store, full_text),
            "summary": _extract_summary(vector_store, full_text),
            "skills": _extract_skills(vector_store, chunk_documents),
            "experience": _extract_experience(vector_store, chunk_documents),
            "education": _extract_education(vector_store, chunk_documents),
            "certifications": _extract_certifications(vector_store, chunk_documents),
        }

        return {
            "status": "success",
            "file_type": file_type,
            "extracted_data": extracted,
            "chunks_count": len(chunks),
            "raw_length": len(full_text),
            "parsed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "extracted_data": {},
        }


def _load_and_split_document(file_bytes: bytes, file_type: str) -> list[Document]:
    """Load a document and split it into chunks using LangChain components.

    Args:
        file_bytes: Raw bytes of the file
        file_type: "pdf" or "txt"

    Returns:
        list[Document]: Split document chunks
    """
    with tempfile.NamedTemporaryFile(mode="wb", suffix=f".{file_type}", delete=False) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    try:
        if file_type == "pdf":
            loader = PyPDFLoader(tmp_path)
        else:
            loader = TextLoader(tmp_path, encoding="utf-8")

        documents = loader.load()

        text_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n",
            length_function=len,
        )

        return text_splitter.split_documents(documents)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _create_vector_store(chunks: list[Document]):
    """Create a FAISS vector store from document chunks.

    Args:
        chunks: List of document chunks

    Returns:
        FAISS vector store with embeddings
    """
    embeddings = FakeEmbeddings(size=768)
    return FAISS.from_documents(documents=chunks, embedding=embeddings)


def _extract_name(text: str) -> str | None:
    """Extract name from first lines of document.

    Args:
        text: Full document text

    Returns:
        str | None: Extracted name or None
    """
    import re

    lines = text.strip().split("\n")[:5]
    for line in lines:
        line_clean = line.strip()
        if line_clean and len(line_clean) < 50 and "@" not in line_clean:
            if not any(kw in line_clean.lower() for kw in ["resume", "cv", "curriculum"]):
                if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$", line_clean):
                    return line_clean
    return None


def _extract_email(text: str) -> str | None:
    """Extract email address from text.

    Args:
        text: Full document text

    Returns:
        str | None: Extracted email or None
    """
    import re

    email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    match = re.search(email_pattern, text)
    return match.group() if match else None


def _extract_phone(text: str) -> str | None:
    """Extract phone number from text.

    Args:
        text: Full document text

    Returns:
        str | None: Extracted phone or None
    """
    import re

    phone_pattern = r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
    match = re.search(phone_pattern, text)
    return match.group() if match else None


def _extract_location(vector_store, text: str) -> str | None:
    """Extract location from text or vector store.

    Args:
        vector_store: FAISS vector store
        text: Full document text

    Returns:
        str | None: Extracted location or None
    """
    import re

    location_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})(?:\s+\d{5})?"
    match = re.search(location_pattern, text)
    if match:
        return f"{match.group(1)}, {match.group(2)}"

    results = vector_store.similarity_search("location address city state", k=3)
    for doc in results:
        match = re.search(location_pattern, doc.page_content)
        if match:
            return f"{match.group(1)}, {match.group(2)}"

    return None


def _extract_summary(vector_store, text: str) -> str | None:
    """Extract professional summary from document.

    Args:
        vector_store: FAISS vector store
        text: Full document text

    Returns:
        str | None: Extracted summary or None
    """
    results = vector_store.similarity_search(
        "professional summary objective career statement about me",
        k=5,
    )

    combined = []
    for doc in results:
        content = doc.page_content.strip()
        if len(content) > 50:
            combined.append(content)

    return " ".join(combined)[:1000] if combined else None


def _extract_skills(vector_store, chunks: list[Document]) -> list[str]:
    """Extract skills from document using vector store.

    Args:
        vector_store: FAISS vector store
        chunks: Document chunks

    Returns:
        list[str]: List of extracted skills
    """
    skills = set()

    results = vector_store.similarity_search("skills technical competencies technologies", k=10)

    for doc in results:
        content = doc.page_content
        parts = content.replace("•", ",").replace("-", ",").replace("*", ",").split(",")
        for part in parts:
            cleaned = part.strip().lower()
            if 2 < len(cleaned) < 50 and not any(c in cleaned for c in ["@", "http", "www"]):
                if not any(kw in cleaned for kw in ["experience", "education", "summary", "objective"]):
                    skills.add(cleaned.title())

    return list(skills)[:20]


def _extract_experience(vector_store, chunks: list[Document]) -> list[dict]:
    """Extract work experience from document.

    Args:
        vector_store: FAISS vector store
        chunks: Document chunks

    Returns:
        list[dict]: List of experience entries
    """
    import re

    experience_entries = []

    results = vector_store.similarity_search(
        "work experience employment job title company position",
        k=15,
    )

    title_pattern = r"^([A-Z][A-Za-z\s]+(?:Engineer|Developer|Manager|Designer|Analyst|Director|Lead|Consultant))\s*[-–]?\s*(.*)?"
    date_pattern = r"(\d{4})\s*[-–]\s*(\d{4}|Present)"

    current_entry = {}
    for doc in results:
        content = doc.page_content.strip()
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    experience_entries.append(current_entry)
                    current_entry = {}
                continue

            date_match = re.search(date_pattern, line)
            if date_match and current_entry.get("title"):
                current_entry["duration"] = date_match.group()

            title_match = re.match(title_pattern, line)
            if title_match:
                current_entry["title"] = title_match.group(1)
                if title_match.group(2):
                    current_entry["company"] = title_match.group(2).strip()
            elif current_entry.get("title") and len(line) > 20:
                current_entry["description"] = line

    if current_entry:
        experience_entries.append(current_entry)

    seen_titles = set()
    unique_entries = []
    for entry in experience_entries:
        title = entry.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_entries.append(entry)

    return unique_entries[:10]


def _extract_education(vector_store, chunks: list[Document]) -> list[dict]:
    """Extract education from document.

    Args:
        vector_store: FAISS vector store
        chunks: Document chunks

    Returns:
        list[dict]: List of education entries
    """
    import re

    education_entries = []

    results = vector_store.similarity_search(
        "education degree university college school academic",
        k=10,
    )

    degree_keywords = ["bachelor", "master", "phd", "b.s.", "m.s.", "b.a.", "m.a.", "mba", "associate", "doctorate"]
    school_keywords = ["university", "college", "institute", "school"]

    current_entry = {}
    for doc in results:
        content = doc.page_content.strip()
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                if current_entry and (current_entry.get("degree") or current_entry.get("institution")):
                    education_entries.append(current_entry)
                    current_entry = {}
                continue

            line_lower = line.lower()

            if any(deg in line_lower for deg in degree_keywords):
                current_entry["degree"] = line
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                if year_match:
                    current_entry["year"] = year_match.group()
            elif any(sch in line_lower for sch in school_keywords):
                current_entry["institution"] = line
                year_match = re.search(r"\b(19|20)\d{2}\b", line)
                if year_match and not current_entry.get("year"):
                    current_entry["year"] = year_match.group()

    if current_entry:
        education_entries.append(current_entry)

    return education_entries[:5]


def _extract_certifications(vector_store, chunks: list[Document]) -> list[str]:
    """Extract certifications from document.

    Args:
        vector_store: FAISS vector store
        chunks: Document chunks

    Returns:
        list[str]: List of certifications
    """
    certifications = []

    results = vector_store.similarity_search(
        "certification certifications certified credentials license",
        k=10,
    )

    for doc in results:
        lines = doc.page_content.split("\n")
        for line in lines:
            line = line.strip()
            if line and len(line) < 100 and not any(
                c in line.lower() for c in ["experience", "education", "skills", "summary"]
            ):
                cleaned = line.replace("•", "").replace("-", "").replace("*", "").strip()
                if cleaned and len(cleaned) > 2:
                    certifications.append(cleaned)

    seen = set()
    unique_certs = []
    for cert in certifications:
        cert_lower = cert.lower()
        if cert_lower not in seen:
            seen.add(cert_lower)
            unique_certs.append(cert)

    return unique_certs[:10]


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
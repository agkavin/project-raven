"""
Candidate API endpoints for joining interview rooms.
No auth required — candidates join via room code.
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from typing import Optional
from core.session_manager import manager
from api.models import (
    CandidateJoinRequest,
    CandidateJoinResponse,
    RoomValidateResponse,
)
from utils.room_code import normalize_room_code
from db.database import AsyncSessionLocal
from db import service as db_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["candidate"])


@router.post("/resume/analyze")
async def analyze_resume(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    """
    Extract interview-relevant skills from a candidate's resume.
    Accepts PDF file or pasted text.
    """
    resume_text: str = ""

    if file is not None:
        try:
            import io
            from PyPDF2 import PdfReader
            contents = await file.read()
            reader = PdfReader(io.BytesIO(contents))
            pages = [page.extract_text() or "" for page in reader.pages]
            resume_text = "\n".join(pages).strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")
    elif text:
        resume_text = text.strip()
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a PDF file (field: 'file') or raw text (field: 'text').",
        )

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume content is empty.")

    # TODO: Phase 4 — use ResumeSkillMatcher from tasks/resume_parser.py
    # For now, return basic extraction
    skills = []
    keywords = ["python", "javascript", "typescript", "react", "node", "sql", "postgresql",
                "fastapi", "django", "flask", "aws", "docker", "kubernetes", "git"]
    resume_lower = resume_text.lower()
    for kw in keywords:
        if kw in resume_lower:
            skills.append(kw.title())

    return {"skills": skills, "resume_text": resume_text}


@router.get("/rooms/{room_code}/validate", response_model=RoomValidateResponse)
async def validate_room(room_code: str):
    """Validate that a room exists and is accepting candidates."""
    try:
        normalized_code = normalize_room_code(room_code)
        room = manager.get_room(normalized_code)

        if not room:
            return RoomValidateResponse(
                valid=False,
                message="Room not found. Please check the room code."
            )

        if room.status != "active":
            return RoomValidateResponse(
                valid=False,
                room_status=room.status,
                message=f"Room is {room.status}. Cannot join at this time."
            )

        if len(room.candidate_sessions) >= room.max_candidates:
            return RoomValidateResponse(
                valid=False,
                room_status=room.status,
                message="Room is full. Maximum candidates reached."
            )

        return RoomValidateResponse(
            valid=True,
            room_status=room.status,
            timeout_minutes=room.timeout_minutes,
            interview_type=room.interview_type,
            message="Room is available"
        )

    except Exception as e:
        logger.error(f"Error validating room: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate room: {str(e)}")


@router.post("/rooms/{room_code}/join", response_model=CandidateJoinResponse)
async def join_room(
    room_code: str,
    request: CandidateJoinRequest,
    http_request: Request,
):
    """
    Join an interview room as a candidate.
    Creates a new session and returns WebSocket URL.
    """
    try:
        normalized_code = normalize_room_code(room_code)

        room = manager.get_room(normalized_code)
        if not room:
            raise HTTPException(status_code=404, detail=f"Room not found: {room_code}")

        if room.status != "active":
            raise HTTPException(status_code=400, detail=f"Room is {room.status}")

        # Create DB session first to get the canonical UUID
        db_session_id = None
        async with AsyncSessionLocal() as db:
            db_room = await db_service.get_room_by_code(db, normalized_code)
            if db_room:
                db_session = await db_service.create_session(
                    db,
                    room_id=db_room.id,
                    candidate_name=request.candidate_name,
                    candidate_email=request.candidate_email,
                    resume_text=request.resume_text,
                )
                db_session_id = str(db_session.id)

        # Add candidate to in-memory room using DB UUID
        candidate_session = manager.add_candidate_to_room(
            room_code=normalized_code,
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            skills_override=request.skills_override,
            session_id=db_session_id,
        )

        if not candidate_session:
            raise HTTPException(status_code=500, detail="Failed to create candidate session")

        # Build WebSocket URL from request host
        host = http_request.headers.get("host", "localhost:8000")
        forwarded_proto = http_request.headers.get("x-forwarded-proto", "")
        scheme = "wss" if forwarded_proto == "https" else "ws"
        ws_url = f"{scheme}://{host}/ws/voice/{normalized_code}/{candidate_session.session_id}"

        return CandidateJoinResponse(
            session_id=candidate_session.session_id,
            websocket_url=ws_url,
            room_code=normalized_code,
            candidate_name=candidate_session.candidate_name,
            timeout_minutes=room.timeout_minutes,
            interview_type=room.interview_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining room: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to join room: {str(e)}")

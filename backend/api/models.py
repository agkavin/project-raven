"""
Pydantic models for API request/response
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# Room Models
# ─────────────────────────────────────────────────────────────────────────────

class InterviewRoom(BaseModel):
    room_code: str
    created_by: str = "admin"
    created_at: datetime = Field(default_factory=datetime.now)
    interview_type: str = Field(default="voice", description="'voice' or 'text'")
    status: str = Field(default="active", description="'active' or 'closed'")
    max_candidates: int = Field(default=50)
    timeout_minutes: int = Field(default=30)
    stages: List[str] = Field(default=["INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"])
    jd_text: Optional[str] = None
    skills_override: Optional[List[str]] = None
    job_role_id: Optional[UUID] = None
    job_role_name: Optional[str] = None
    org_id: Optional[UUID] = None
    admin_user_id: Optional[UUID] = None
    candidate_sessions: List[str] = Field(default_factory=list)
    candidate_count: int = 0


class CandidateSession(BaseModel):
    session_id: str = Field(description="UUID session identifier")
    room_code: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = Field(default="in_progress", description="'in_progress', 'completed', 'timed_out'")


# ─────────────────────────────────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────────────────────────────────

class RoomCreateRequest(BaseModel):
    interview_type: str = Field(default="voice", description="'voice' or 'text'")
    timeout_minutes: int = Field(default=30, ge=5, le=180)
    max_candidates: int = Field(default=50, ge=1, le=500)
    jd_text: Optional[str] = None
    skills_override: Optional[List[str]] = None
    job_role_id: Optional[UUID] = None


class CandidateJoinRequest(BaseModel):
    candidate_name: Optional[str] = Field(None, max_length=100)
    candidate_email: Optional[str] = Field(None, max_length=255)
    skills_override: Optional[List[str]] = None
    resume_text: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────────────────────────────────────

class RoomValidateResponse(BaseModel):
    valid: bool
    room_status: Optional[str] = None
    timeout_minutes: Optional[int] = None
    interview_type: Optional[str] = None
    message: Optional[str] = None


class CandidateJoinResponse(BaseModel):
    session_id: str
    websocket_url: str
    room_code: str
    candidate_name: Optional[str] = None
    timeout_minutes: int
    interview_type: str


class RoomCreateResponse(BaseModel):
    room_code: str
    websocket_url: str
    created_at: datetime
    timeout_minutes: int
    max_candidates: int
    interview_type: str


class RoomListResponse(BaseModel):
    rooms: List[InterviewRoom]

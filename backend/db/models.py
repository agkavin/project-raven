"""
SQLAlchemy ORM models for AI Interview database tables.
Follows the Project Raven unified schema.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    JSON,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# Core Entities
# ─────────────────────────────────────────────────────────────────────────────

class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    users = relationship("User", back_populates="organisation", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False)   # 'super_admin' | 'admin'
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    organisation = relationship("Organisation", back_populates="users")

    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
        CheckConstraint("role IN ('super_admin', 'admin')", name='check_user_role'),
    )


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    skills = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    interview_rooms = relationship("InterviewRoom", back_populates="job_role")


# ─────────────────────────────────────────────────────────────────────────────
# Interview Core
# ─────────────────────────────────────────────────────────────────────────────

class InterviewRoom(Base):
    __tablename__ = "interview_rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    room_code = Column(String(20), nullable=False, unique=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    interview_type = Column(String(50), nullable=False, default='voice')  # 'voice', 'text', 'staged'
    stages = Column(JSON, nullable=False, default=lambda: ["INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"])
    timeout_minutes = Column(Integer, nullable=False, default=30)
    max_candidates = Column(Integer, nullable=False, default=50)
    
    jd_text = Column(Text, nullable=True)
    skills_override = Column(JSON, nullable=True)
    job_role_id = Column(UUID(as_uuid=True), ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    job_role = relationship("JobRole", back_populates="interview_rooms")
    sessions = relationship("InterviewSession", back_populates="room", cascade="all, delete-orphan")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("interview_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    
    candidate_name = Column(String(255), nullable=True)
    candidate_email = Column(String(255), nullable=True)
    resume_text = Column(Text, nullable=True)
    
    status = Column(String(20), nullable=False, default='pending')
    current_stage = Column(String(20), nullable=False, default='INTRO')
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint('room_id', 'candidate_email', name='uq_session_room_candidate'),
    )

    # Relationships
    room = relationship("InterviewRoom", back_populates="sessions")
    stage_summaries = relationship("StageSummary", back_populates="session", cascade="all, delete-orphan")
    code_submissions = relationship("CodeSubmission", back_populates="session", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="session", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────────────────────
# Stage Components (LangGraph Support)
# ─────────────────────────────────────────────────────────────────────────────

class StageSummary(Base):
    """Sliding Context Window mechanism"""
    __tablename__ = "stage_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(20), nullable=False)
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint('session_id', 'stage', name='uq_stage_summary'),
    )

    session = relationship("InterviewSession", back_populates="stage_summaries")


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(20), nullable=False)  # 'DSA' or 'SQL'
    code = Column(Text, nullable=False)
    language = Column(String(50), nullable=True)
    grade = Column(JSON, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint('session_id', 'stage', name='uq_code_submission'),
    )

    session = relationship("InterviewSession", back_populates="code_submissions")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    overall_score = Column(Float, nullable=True)
    stage_scores = Column(JSON, nullable=True)
    technical_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    
    recommendation = Column(String(20), nullable=True)
    feedback = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint('session_id', name='uq_evaluation_session'),
        CheckConstraint("recommendation IN ('strong_hire', 'hire', 'maybe', 'no_hire')", name='check_recommendation_value'),
    )

    session = relationship("InterviewSession", back_populates="evaluations")

"""
Database CRUD operations for Project Raven.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from .models import (
    Organisation,
    User,
    JobRole,
    InterviewRoom,
    InterviewSession,
    StageSummary,
    CodeSubmission,
    Evaluation
)

# ─────────────────────────────────────────────────────────────────────────────
# User / Org
# ─────────────────────────────────────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, email: str, role: str = "admin", full_name: str = None, org_id: UUID = None) -> User:
    import uuid
    user = User(id=uuid.uuid4(), email=email, role=role, full_name=full_name, org_id=org_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_or_create_user(db: AsyncSession, email: str, role: str = "admin") -> User:
    user = await get_user_by_email(db, email)
    if user:
        return user
    return await create_user(db, email=email, role=role)

# ─────────────────────────────────────────────────────────────────────────────
# Interview Rooms
# ─────────────────────────────────────────────────────────────────────────────

async def get_room_by_code(db: AsyncSession, room_code: str) -> Optional[InterviewRoom]:
    result = await db.execute(select(InterviewRoom).where(InterviewRoom.room_code == room_code))
    return result.scalar_one_or_none()

async def create_room(db: AsyncSession, room_code: str, **kwargs) -> InterviewRoom:
    room = InterviewRoom(room_code=room_code, **kwargs)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room

async def get_all_rooms(db: AsyncSession) -> List[InterviewRoom]:
    result = await db.execute(select(InterviewRoom).order_by(InterviewRoom.created_at.desc()))
    return list(result.scalars().all())

async def update_room_status(db: AsyncSession, room_code: str, status: str) -> Optional[InterviewRoom]:
    result = await db.execute(
        update(InterviewRoom)
        .where(InterviewRoom.room_code == room_code)
        .values(status=status)
        .returning(InterviewRoom)
    )
    room = result.scalar_one_or_none()
    if room:
        await db.commit()
    return room

# ─────────────────────────────────────────────────────────────────────────────
# Interview Sessions
# ─────────────────────────────────────────────────────────────────────────────

async def get_session(db: AsyncSession, session_id: UUID) -> Optional[InterviewSession]:
    result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    return result.scalar_one_or_none()

async def get_session_by_string_id(db: AsyncSession, session_id: str) -> Optional[InterviewSession]:
    result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    return result.scalar_one_or_none()

async def create_session(db: AsyncSession, room_id: UUID, candidate_name: str = None, candidate_email: str = None, resume_text: str = None) -> InterviewSession:
    session = InterviewSession(
        room_id=room_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        resume_text=resume_text,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_sessions_by_room(db: AsyncSession, room_id: UUID) -> List[InterviewSession]:
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.room_id == room_id)
        .order_by(InterviewSession.created_at.desc())
    )
    return list(result.scalars().all())

async def update_session_stage(db: AsyncSession, session_id: UUID, current_stage: str) -> Optional[InterviewSession]:
    result = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id)
        .values(current_stage=current_stage)
        .returning(InterviewSession)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.commit()
    return session

async def complete_session(db: AsyncSession, session_id: UUID) -> Optional[InterviewSession]:
    from datetime import datetime, timezone
    result = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
        .returning(InterviewSession)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.commit()
    return session

async def start_session(db: AsyncSession, session_id: UUID) -> Optional[InterviewSession]:
    from datetime import datetime, timezone
    result = await db.execute(
        update(InterviewSession)
        .where(InterviewSession.id == session_id)
        .values(status="in_progress", started_at=datetime.now(timezone.utc))
        .returning(InterviewSession)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.commit()
    return session

# ─────────────────────────────────────────────────────────────────────────────
# Stage Summaries
# ─────────────────────────────────────────────────────────────────────────────

async def save_stage_summary(db: AsyncSession, session_id: UUID, stage: str, summary_text: str) -> StageSummary:
    stmt = pg_insert(StageSummary).values(
        session_id=session_id, stage=stage, summary_text=summary_text
    ).on_conflict_do_update(
        constraint="uq_stage_summary",
        set_={"summary_text": summary_text},
    ).returning(StageSummary)
    result = await db.execute(stmt)
    await db.commit()
    summary = result.scalar_one()
    await db.refresh(summary)
    return summary

async def get_stage_summaries(db: AsyncSession, session_id: UUID) -> List[StageSummary]:
    result = await db.execute(
        select(StageSummary)
        .where(StageSummary.session_id == session_id)
        .order_by(StageSummary.created_at.asc())
    )
    return list(result.scalars().all())

# ─────────────────────────────────────────────────────────────────────────────
# Code Submissions
# ─────────────────────────────────────────────────────────────────────────────

async def save_code_submission(db: AsyncSession, session_id: UUID, stage: str, code: str, language: str = None) -> CodeSubmission:
    stmt = pg_insert(CodeSubmission).values(
        session_id=session_id, stage=stage, code=code, language=language
    ).on_conflict_do_update(
        constraint="uq_code_submission",
        set_={"code": code, "language": language},
    ).returning(CodeSubmission)
    result = await db.execute(stmt)
    await db.commit()
    submission = result.scalar_one()
    await db.refresh(submission)
    return submission

# ─────────────────────────────────────────────────────────────────────────────
# Evaluations
# ─────────────────────────────────────────────────────────────────────────────

async def save_evaluation(db: AsyncSession, session_id: UUID, **kwargs) -> Evaluation:
    evaluation = Evaluation(session_id=session_id, **kwargs)
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation

async def get_evaluations_by_room(db: AsyncSession, room_code: str = None) -> List[dict]:
    """Get evaluations with session and room info."""
    query = (
        select(
            Evaluation,
            InterviewSession.candidate_name,
            InterviewSession.candidate_email,
            InterviewRoom.room_code,
            InterviewRoom.jd_text,
        )
        .join(InterviewSession, Evaluation.session_id == InterviewSession.id)
        .join(InterviewRoom, InterviewSession.room_id == InterviewRoom.id)
    )
    if room_code:
        query = query.where(InterviewRoom.room_code == room_code)
    query = query.order_by(Evaluation.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(ev.id),
            "session_id": str(ev.session_id),
            "candidate_name": name,
            "candidate_email": email,
            "room_code": rc,
            "overall_score": ev.overall_score,
            "stage_scores": ev.stage_scores,
            "technical_score": ev.technical_score,
            "communication_score": ev.communication_score,
            "recommendation": ev.recommendation,
            "feedback": ev.feedback,
            "strengths": ev.strengths,
            "weaknesses": ev.weaknesses,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev, name, email, rc, jd in rows
    ]

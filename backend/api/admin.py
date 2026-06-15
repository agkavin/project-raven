"""
Admin API endpoints for managing interview rooms.
All endpoints require admin or super_admin role.
"""
from fastapi import APIRouter, HTTPException, Depends
from core.auth import require_admin, UserProfile
from core.session_manager import manager
from api.models import (
    RoomCreateRequest,
    RoomCreateResponse,
    RoomListResponse,
    InterviewRoom,
)
from db.database import AsyncSessionLocal
from db import service as db_service
import logging
import csv
import io
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/rooms/create", response_model=RoomCreateResponse)
async def create_room(
    request: RoomCreateRequest,
    current_user: UserProfile = Depends(require_admin),
):
    """Create a new interview room. Returns room code and WebSocket URL."""
    try:
        room = manager.create_room(
            interview_type=request.interview_type,
            timeout_minutes=request.timeout_minutes,
            max_candidates=request.max_candidates,
            jd_text=request.jd_text,
            skills_override=request.skills_override,
            job_role_id=request.job_role_id,
            org_id=current_user.org_id,
            admin_user_id=current_user.id,
        )

        # Persist to DB
        async with AsyncSessionLocal() as db:
            await db_service.create_room(
                db,
                room_code=room.room_code,
                interview_type=room.interview_type,
                timeout_minutes=room.timeout_minutes,
                max_candidates=room.max_candidates,
                jd_text=room.jd_text,
                skills_override=room.skills_override,
                job_role_id=room.job_role_id,
                created_by=str(current_user.id),
                org_id=current_user.org_id,
            )

        return RoomCreateResponse(
            room_code=room.room_code,
            websocket_url=f"ws://localhost:8000/ws/voice/{room.room_code}/{{session_id}}",
            created_at=room.created_at,
            timeout_minutes=room.timeout_minutes,
            max_candidates=room.max_candidates,
            interview_type=room.interview_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")


@router.get("/rooms", response_model=RoomListResponse)
async def list_rooms(current_user: UserProfile = Depends(require_admin)):
    """List all rooms with candidate count."""
    rooms = manager.get_all_rooms()
    result = []
    for room in rooms:
        candidates = manager.get_room_candidates(room.room_code)
        room.candidate_count = len(candidates)
        result.append(room)
    return RoomListResponse(rooms=result)


@router.get("/rooms/{room_code}")
async def get_room(room_code: str, current_user: UserProfile = Depends(require_admin)):
    """Get room details with candidates."""
    room = manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    candidates = manager.get_room_candidates(room_code)
    return {
        "room": room,
        "candidates": candidates,
    }


@router.post("/rooms/{room_code}/close")
async def close_room(room_code: str, current_user: UserProfile = Depends(require_admin)):
    """Close a room and disconnect all candidates."""
    success = manager.close_room(room_code)
    if not success:
        raise HTTPException(status_code=404, detail="Room not found")

    # Update DB status
    async with AsyncSessionLocal() as db:
        await db_service.update_room_status(db, room_code, "closed")

    return {"message": f"Room {room_code} closed"}


@router.get("/rooms/{room_code}/candidates")
async def get_room_candidates(room_code: str, current_user: UserProfile = Depends(require_admin)):
    """List all candidates in a room."""
    room = manager.get_room(room_code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    candidates = manager.get_room_candidates(room_code)
    return {"room_code": room_code, "candidates": candidates}


@router.get("/evaluations")
async def get_evaluations(
    room_code: Optional[str] = None,
    current_user: UserProfile = Depends(require_admin),
):
    """List all evaluations, optionally filtered by room."""
    async with AsyncSessionLocal() as db:
        evaluations = await db_service.get_evaluations_by_room(db, room_code)
    return {"evaluations": evaluations}


@router.get("/evaluations/export")
async def export_evaluations(
    room_code: Optional[str] = None,
    current_user: UserProfile = Depends(require_admin),
):
    """Export evaluations as CSV."""
    async with AsyncSessionLocal() as db:
        evaluations = await db_service.get_evaluations_by_room(db, room_code)

    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=evaluations[0].keys())
    writer.writeheader()
    writer.writerows(evaluations)

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluations.csv"},
    )


@router.get("/candidates/performance")
async def get_candidate_performance(
    room_code: Optional[str] = None,
    current_user: UserProfile = Depends(require_admin),
):
    """Get aggregated candidate performance metrics."""
    async with AsyncSessionLocal() as db:
        evaluations = await db_service.get_evaluations_by_room(db, room_code)

    if not evaluations:
        return {"candidates": [], "summary": {}}

    # Aggregate
    total = len(evaluations)
    avg_score = sum(e.get("overall_score", 0) for e in evaluations if e.get("overall_score")) / max(total, 1)
    recommendations = {}
    for ev in evaluations:
        rec = ev.get("recommendation", "unknown")
        recommendations[rec] = recommendations.get(rec, 0) + 1

    return {
        "total_evaluations": total,
        "average_score": round(avg_score, 2),
        "recommendation_breakdown": recommendations,
        "evaluations": evaluations,
    }

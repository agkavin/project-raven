"""
Session Manager for WebSocket connections.
Manages session state, WebSocket connections, and interview rooms.
In-memory storage for active sessions — rooms persisted in PostgreSQL.
"""
from typing import Dict, Optional, List
from fastapi import WebSocket
from api.models import InterviewRoom, CandidateSession
from utils.room_code import generate_room_code
import logging
import asyncio
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections, sessions, and interview rooms"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.admin_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, InterviewRoom] = {}
        self.candidate_sessions: Dict[str, CandidateSession] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.connection_health: Dict[str, datetime] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        logger.info("ConnectionManager initialized")

    # ── Room Management ──────────────────────────────────────────────────

    def create_room(
        self,
        interview_type: str = "voice",
        timeout_minutes: int = 30,
        max_candidates: int = 50,
        created_by: str = "admin",
        jd_text: str = None,
        skills_override: list = None,
        job_role_id: Optional[UUID] = None,
        job_role_name: Optional[str] = None,
        org_id: Optional[UUID] = None,
        admin_user_id: Optional[UUID] = None,
    ) -> InterviewRoom:
        existing_codes = set(self.rooms.keys())
        room_code = generate_room_code(length=8, existing_codes=existing_codes)

        room = InterviewRoom(
            room_code=room_code,
            created_by=created_by,
            interview_type=interview_type,
            timeout_minutes=timeout_minutes,
            max_candidates=max_candidates,
            jd_text=jd_text,
            skills_override=skills_override,
            job_role_id=job_role_id,
            job_role_name=job_role_name,
            org_id=org_id,
            admin_user_id=admin_user_id,
        )

        self.rooms[room_code] = room
        logger.info(f"Created room: {room_code} (type={interview_type})")
        return room

    def get_room(self, room_code: str) -> Optional[InterviewRoom]:
        return self.rooms.get(room_code)

    def get_all_rooms(self) -> List[InterviewRoom]:
        return list(self.rooms.values())

    def close_room(self, room_code: str) -> bool:
        room = self.rooms.get(room_code)
        if not room:
            return False
        room.status = "closed"
        for session_id in list(room.candidate_sessions):
            self.disconnect_session(session_id)
            if session_id in self.timeout_tasks:
                self.timeout_tasks[session_id].cancel()
                del self.timeout_tasks[session_id]
        logger.info(f"Closed room: {room_code}")
        return True

    # ── Candidate Session Management ─────────────────────────────────────

    def add_candidate_to_room(
        self,
        room_code: str,
        candidate_name: Optional[str] = None,
        candidate_email: Optional[str] = None,
        skills_override: Optional[list] = None,
        session_id: Optional[str] = None,
    ) -> Optional[CandidateSession]:
        room = self.rooms.get(room_code)
        if not room:
            logger.error(f"Room not found: {room_code}")
            return None
        if room.status != "active":
            logger.error(f"Room not active: {room_code}")
            return None
        if len(room.candidate_sessions) >= room.max_candidates:
            logger.error(f"Room full: {room_code}")
            return None

        if session_id is None:
            import uuid
            session_id = str(uuid.uuid4())  # This becomes candidate_id in InterviewState

        candidate_session = CandidateSession(
            session_id=session_id,
            room_code=room_code,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
        )

        room.candidate_sessions.append(session_id)
        self.candidate_sessions[session_id] = candidate_session

        timeout_task = asyncio.create_task(
            self._timeout_candidate(session_id, room.timeout_minutes)
        )
        self.timeout_tasks[session_id] = timeout_task

        logger.info(f"Added candidate to {room_code}: {session_id}")
        return candidate_session

    def get_candidate_session(self, session_id: str) -> Optional[CandidateSession]:
        return self.candidate_sessions.get(session_id)

    def get_room_candidates(self, room_code: str) -> List[CandidateSession]:
        room = self.rooms.get(room_code)
        if not room:
            return []
        return [
            self.candidate_sessions[sid]
            for sid in room.candidate_sessions
            if sid in self.candidate_sessions
        ]

    def complete_candidate_session(self, session_id: str):
        candidate_session = self.candidate_sessions.get(session_id)
        if candidate_session:
            candidate_session.status = "completed"
            candidate_session.completed_at = datetime.now()
            if session_id in self.timeout_tasks:
                self.timeout_tasks[session_id].cancel()
                del self.timeout_tasks[session_id]
            logger.info(f"Completed session: {session_id}")

    async def _timeout_candidate(self, session_id: str, minutes: int):
        try:
            warning_times = []
            if minutes > 10:
                warning_times.append(((minutes - 10) * 60, "10 minutes remaining"))
            if minutes > 5:
                warning_times.append(((minutes - 5) * 60, "5 minutes remaining"))
            warning_times.append(((minutes - 1) * 60, "1 minute remaining"))
            warning_times.append((minutes * 60, "Time expired"))

            for delay, message in warning_times:
                await asyncio.sleep(delay)
                ws = self.active_connections.get(session_id)
                if ws:
                    try:
                        await ws.send_json({"type": "timeout_warning", "message": message})
                    except Exception:
                        pass

            self.complete_candidate_session(session_id)
            ws = self.active_connections.get(session_id)
            if ws:
                try:
                    await ws.send_json({"type": "timed_out", "message": "Interview time expired"})
                    await ws.close()
                except Exception:
                    pass

        except asyncio.CancelledError:
            pass

    # ── WebSocket Connection Management ──────────────────────────────────

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_health[session_id] = datetime.now()
        self.heartbeat_tasks[session_id] = asyncio.create_task(
            self._heartbeat_loop(session_id)
        )
        logger.info(f"Connected: {session_id}")

    def disconnect_session(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.connection_health:
            del self.connection_health[session_id]
        if session_id in self.heartbeat_tasks:
            self.heartbeat_tasks[session_id].cancel()
            del self.heartbeat_tasks[session_id]
        logger.info(f"Disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect_session(session_id)

    def mark_healthy(self, session_id: str):
        self.connection_health[session_id] = datetime.now()

    def is_connection_healthy(self, session_id: str, max_age_seconds: int = 90) -> bool:
        last = self.connection_health.get(session_id)
        if not last:
            return False
        return (datetime.now() - last).total_seconds() < max_age_seconds

    async def _heartbeat_loop(self, session_id: str):
        try:
            while True:
                await asyncio.sleep(30)
                ws = self.active_connections.get(session_id)
                if not ws:
                    break
                if not self.is_connection_healthy(session_id):
                    logger.warning(f"Unhealthy connection: {session_id}")
                    await ws.close()
                    break
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    # ── Admin WebSocket ──────────────────────────────────────────────────

    async def connect_admin(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections[room_code] = websocket
        logger.info(f"Admin connected for room: {room_code}")

    def disconnect_admin(self, room_code: str):
        if room_code in self.admin_connections:
            del self.admin_connections[room_code]

    async def broadcast_to_admin(self, room_code: str, message: dict):
        ws = self.admin_connections.get(room_code)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect_admin(room_code)


manager = ConnectionManager()

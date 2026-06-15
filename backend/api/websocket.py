"""
WebSocket endpoint for live voice interviews.
Handles candidate ↔ Gemini Multimodal Live API communication.
Phase 5 will wire up the full Gemini Live session.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from core.session_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice/{room_code}/{session_id}")
async def voice_websocket(
    websocket: WebSocket,
    room_code: str,
    session_id: str,
):
    """
    WebSocket endpoint for live voice interviews.
    - Validates session exists in ConnectionManager
    - Manages connection lifecycle
    - Routes audio to Gemini Live (Phase 5)
    """
    logger.info(f"WebSocket connection request: room={room_code}, session={session_id}")

    # Validate session exists
    candidate_session = manager.get_candidate_session(session_id)
    if not candidate_session:
        logger.error(f"Session not found: {session_id}")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close(code=4401)
        return

    if candidate_session.room_code != room_code:
        logger.error(f"Session {session_id} does not belong to room {room_code}")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Session does not belong to this room"})
        await websocket.close(code=4403)
        return

    # Connect via ConnectionManager
    await manager.connect(session_id, websocket)
    logger.info(f"WebSocket connected: {session_id}")

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "room_code": room_code,
        })

        # Main message loop
        while True:
            message = await websocket.receive()
            manager.mark_healthy(session_id)

            if "bytes" in message:
                # Audio data — forward to Gemini Live (Phase 5)
                # For now, just log receipt
                logger.debug(f"Audio received: {len(message['bytes'])} bytes from {session_id}")

            elif "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "ui_ready":
                    logger.info(f"UI Ready for {session_id}: {data.get('node')}")

                elif msg_type == "submit_code":
                    # Code submission — will be wired to CodeGrader in Phase 5
                    logger.info(f"Code submitted from {session_id}: {len(data.get('code', ''))} chars")
                    await websocket.send_json({
                        "type": "code_received",
                        "message": "Code submission received",
                    })

                else:
                    logger.warning(f"Unknown message type from {session_id}: {msg_type}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
    finally:
        manager.disconnect_session(session_id)
        logger.info(f"WebSocket cleaned up: {session_id}")

from langgraph.graph import StateGraph, START, END
from agents.state import InterviewState, store
from db.database import AsyncSessionLocal
from db import service as db_service
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "INTRO": ["EXPERIENCE"],
    "EXPERIENCE": ["DSA"],
    "DSA": ["SQL"],
    "SQL": ["REPORT"],
    "REPORT": [END]
}


def validate_transition(current_stage: str, next_stage: str) -> str:
    valid_next = VALID_TRANSITIONS.get(current_stage, [])
    if next_stage in valid_next:
        return next_stage
    logger.warning(f"Invalid transition attempted: {current_stage} -> {next_stage}. Falling back to default.")
    return valid_next[0] if valid_next else current_stage


def create_interview_graph():
    workflow = StateGraph(InterviewState)

    def intro_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: INTRO")
        return {"current_stage": "INTRO", "ui_view": "avatar"}

    def experience_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: EXPERIENCE")
        return {"current_stage": "EXPERIENCE", "ui_view": "avatar"}

    def dsa_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: DSA")
        return {"current_stage": "DSA", "ui_view": "monaco"}

    def sql_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: SQL")
        return {"current_stage": "SQL", "ui_view": "monaco"}

    def report_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: REPORT")
        return {"current_stage": "REPORT", "ui_view": "report"}

    workflow.add_node("INTRO", intro_node)
    workflow.add_node("EXPERIENCE", experience_node)
    workflow.add_node("DSA", dsa_node)
    workflow.add_node("SQL", sql_node)
    workflow.add_node("REPORT", report_node)

    workflow.add_edge(START, "INTRO")
    workflow.add_edge("INTRO", "EXPERIENCE")
    workflow.add_edge("EXPERIENCE", "DSA")
    workflow.add_edge("DSA", "SQL")
    workflow.add_edge("SQL", "REPORT")
    workflow.add_edge("REPORT", END)

    return workflow.compile()


interview_graph = create_interview_graph()


async def advance_stage(candidate_id: str, next_node: str):
    state = store.get(candidate_id)
    if not state:
        raise ValueError(f"Candidate session {candidate_id} not found.")

    current = state.get("current_stage", "INTRO")
    target = validate_transition(current, next_node)

    from agents.nodes import summarize_stage
    summary = await summarize_stage(state)

    if summary:
        store.update(candidate_id, context_summary=summary)
        logger.info(f"Saved context_summary for stage {current}: {summary[:50]}...")

        # Persist summary to PostgreSQL (bridge in-memory → DB)
        try:
            async with AsyncSessionLocal() as db:
                await db_service.save_stage_summary(
                    db,
                    session_id=UUID(candidate_id),
                    stage=current,
                    summary_text=summary,
                )
                logger.info(f"Persisted stage summary to DB: {current}")
        except Exception as e:
            logger.error(f"Failed to persist stage summary to DB: {e}")

    # Update current_stage in PostgreSQL
    try:
        async with AsyncSessionLocal() as db:
            await db_service.update_session_stage(
                db,
                session_id=UUID(candidate_id),
                current_stage=target,
            )
    except Exception as e:
        logger.error(f"Failed to update session stage in DB: {e}")

    logger.info(f"Invoking LangGraph: {current} -> {target}")
    result = await interview_graph.ainvoke(state)

    store.update(candidate_id, **result)
    return result

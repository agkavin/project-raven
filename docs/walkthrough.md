# Project Raven — Development Walkthrough

A detailed account of what was built, why decisions were made, and what each component does — from Phase 1 through Phase 4.

---

## Table of Contents

- [Overview](#overview)
- [Phase 1: Project Setup](#phase-1-project-setup)
- [Phase 2: Database Layer](#phase-2-database-layer)
- [Phase 3: Auth & Room Management](#phase-3-auth--room-management)
- [Phase 4: LangGraph Core & Background Tasks](#phase-4-langgraph-core--background-tasks)
- [Bug Fixes & Audit](#bug-fixes--audit)
- [Architectural Decisions](#architectural-decisions)
- [What's Next](#whats-next)

---

## Overview

Project Raven is an AI-powered technical interviewer. A candidate joins a room via a room code, connects over WebSocket, and has a live voice conversation with an AI interviewer powered by Google Gemini's Multimodal Live API. The interview follows a 5-stage LangGraph orchestration flow: **Intro → Experience → DSA → SQL → Report**.

The codebase was built from scratch in a new repository (`project-raven-new/`), porting and improving from two earlier原型 codebases (`project-raven/backend/` v2 and `project-raven/interview-ai/` v3).

---

## Phase 1: Project Setup

**Commit:** `aa6ae1f` — 2026-06-15 18:03:14  
**Workload:** ~15% of total effort

### What was created

| File/Directory | Purpose |
|---|---|
| `backend/pyproject.toml` | Python project config with all dependencies |
| `backend/uv.lock` | Locked dependency versions (78 packages) |
| `docker-compose.yml` | PostgreSQL 16 on port 5433 |
| `.env` | Environment variables (DB URL, Gemini keys, CORS) |
| `frontend/` | Next.js 16 app with Monaco, Recharts, Zustand, Lucide |
| `docs/PROJECT_REQUIREMENTS.md` | 973-line PRD covering architecture, schema, API, action plan |

### Key decisions

- **Docker Compose for PostgreSQL** — Port 5433 to avoid conflicts with existing local Postgres instances. Container named `raven-postgres`.
- **`uv` for Python packaging** — Faster than pip, deterministic lockfile. All 78 backend dependencies locked.
- **Next.js 16** — App Router with TypeScript, Tailwind CSS, and the packages needed for the full UI: Monaco Editor (code editor), Recharts (radar charts), Zustand (state), Lucide (icons).
- **No Supabase** — The original v2/v3 used Supabase for auth. We stripped it entirely. Auth is local PostgreSQL with dev-mode tokens (token = user UUID).

### Dependencies installed

**Backend (78 packages):** fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, langgraph, instructor, google-genai, python-dotenv, pydantic, websockets, pymupdf, pypdf2, alembic, httpx, python-multipart, and 64 transitive dependencies.

**Frontend:** next, react, @monaco-editor/react, recharts, zustand, lucide-react, @supabase/supabase-js (unused, kept for future), class-variance-authority, clsx, tailwind-merge.

---

## Phase 2: Database Layer

**Commit:** `ce03dc0` — 2026-06-15 19:38:42  
**Workload:** ~20% of total effort

### What was created

| File | Lines | Purpose |
|---|---|---|
| `db/database.py` | 76 | Async SQLAlchemy engine, session factory, init/close lifecycle |
| `db/models.py` | 200 | 8 ORM models with relationships and constraints |
| `db/service.py` | 238 | Full CRUD operations for all tables |
| `test_db.py` | 26 | Quick DB connectivity test |

### Database schema — 8 tables

```
Organisation ──< User
                  │
JobRole ────────< InterviewRoom >──< InterviewSession
                                        │
                                   StageSummary
                                   CodeSubmission
                                   Evaluation
```

**Organisation** — Multi-tenant org container. Fields: `id`, `name`, `slug`, `created_at`.

**User** — Admin users. Fields: `id`, `email`, `full_name`, `role` (super_admin | admin), `org_id` FK.

**JobRole** — Predefined role templates with skill lists. Fields: `id`, `code`, `name`, `skills` (JSON), `is_active`.

**InterviewRoom** — A room that candidates join. Fields: `room_code` (unique 8-char), `interview_type`, `stages` (JSON), `timeout_minutes`, `max_candidates`, `jd_text`, `skills_override` (JSON), `job_role_id` FK, `org_id` FK, `admin_user_id` FK, `status`.

**InterviewSession** — One per candidate per room. Fields: `id`, `room_id` FK, `candidate_name`, `candidate_email`, `resume_text`, `status`, `current_stage`, `started_at`, `completed_at`.

**StageSummary** — Sliding context window summaries. Fields: `session_id` FK, `stage`, `summary_text`. Unique on `(session_id, stage)` with upsert support.

**CodeSubmission** — DSA/SQL code submissions. Fields: `session_id` FK, `stage`, `code`, `language`, `grade` (JSON), `feedback`. Unique on `(session_id, stage)` with upsert support.

**Evaluation** — Final interview evaluation. Fields: `session_id` FK (unique), `overall_score`, `stage_scores` (JSON), `technical_score`, `communication_score`, `recommendation` (strong_hire | hire | maybe | no_hire), `feedback`, `strengths` (JSON), `weaknesses` (JSON).

### Key decisions

- **`Base.metadata.create_all()`** — No Alembic migrations for now. Tables are created on startup. Fresh DB = drop + recreate.
- **`NullPool`** — Used with asyncpg to prevent connection reuse across event loops. Acceptable for dev/MVP.
- **Upsert for StageSummary and CodeSubmission** — PostgreSQL `ON CONFLICT DO UPDATE` prevents crashes on duplicate stage submissions (sliding context window requires updates, not just inserts).
- **Unique constraint on Evaluation.session_id** — Prevents duplicate evaluations per interview session.

### CRUD operations provided

`get_user_by_id`, `get_user_by_email`, `create_user`, `get_or_create_user`, `get_room_by_code`, `create_room`, `get_all_rooms`, `update_room_status`, `get_session`, `get_session_by_string_id`, `create_session`, `get_sessions_by_room`, `update_session_stage`, `complete_session`, `start_session`, `save_stage_summary` (upsert), `get_stage_summaries`, `save_code_submission` (upsert), `save_evaluation`, `get_evaluations_by_room`.

---

## Phase 3: Auth & Room Management

**Commit:** `043b514` — 2026-06-15 22:14:15  
**Workload:** ~35% of total effort

### What was created

| File | Lines | Purpose |
|---|---|---|
| `core/auth.py` | 118 | Local PostgreSQL auth, UserProfile, role guards |
| `core/session_manager.py` | 259 | ConnectionManager: rooms, sessions, WebSocket lifecycle |
| `api/admin.py` | 184 | 8 admin REST endpoints |
| `api/candidate.py` | 173 | 3 candidate REST endpoints |
| `api/websocket.py` | 94 | WebSocket endpoint for live interviews |
| `api/models.py` | 94 | Pydantic request/response models |
| `utils/room_code.py` | 47 | Room code generation and validation |

### Authentication

Dev-mode auth with no JWT. The flow:
1. Admin calls `POST /auth/login` with email
2. Server creates user in PostgreSQL if not exists
3. Returns `token` = user UUID
4. All protected endpoints use `HTTPBearer` header with this token
5. `get_current_user()` resolves user from DB via the token

**Role guards:**
- `require_admin` — Allows `admin` and `super_admin`
- `require_super_admin` — Allows only `super_admin`

### ConnectionManager

The heart of the real-time system. An in-memory manager that tracks:

- **`rooms: Dict[str, InterviewRoom]`** — Active rooms keyed by room code
- **`candidate_sessions: Dict[str, CandidateSession]`** — Active sessions keyed by session UUID
- **`active_connections: Dict[str, WebSocket]`** — WebSocket connections keyed by session ID
- **`admin_connections: Dict[str, WebSocket]`** — Admin monitoring connections keyed by room code
- **`timeout_tasks: Dict[str, asyncio.Task]`** — Per-candidate timeout countdown tasks
- **`connection_health: Dict[str, datetime]`** — Last heartbeat timestamp per connection
- **`heartbeat_tasks: Dict[str, asyncio.Task]`** — Per-connection heartbeat loops

**Lifecycle:**
1. Admin creates room → `create_room()` generates 8-char code, stores in memory
2. Candidate joins → `add_candidate_to_room()` creates session with DB UUID, starts timeout task
3. Candidate connects WebSocket → `connect()` accepts, starts heartbeat loop
4. During interview → `mark_healthy()` called on every message, heartbeat checks every 30s
5. On disconnect → `disconnect_session()` cleans up all tracked state
6. On room closure → `close_room()` disconnects all candidates, cancels timeouts

### Admin endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/admin/rooms` | Create room with JD, skills, timeout config |
| GET | `/admin/rooms` | List all rooms |
| GET | `/admin/rooms/{code}` | Get room details |
| POST | `/admin/rooms/{code}/close` | Close room, disconnect all candidates |
| GET | `/admin/rooms/{code}/candidates` | List candidates in room |
| GET | `/admin/evaluations` | List evaluations (filterable by room) |
| GET | `/admin/evaluations/export` | Export evaluations as CSV |
| GET | `/admin/candidates/performance` | Aggregate performance metrics |

### Candidate endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/resume/analyze` | Extract skills from PDF or text resume |
| GET | `/rooms/{code}/validate` | Check if room exists and is active |
| POST | `/rooms/{code}/join` | Join room, get session ID + WebSocket URL |

### WebSocket endpoint

`/ws/voice/{room_code}/{session_id}` — Handles:
- Session validation (checks room membership)
- Connection lifecycle via ConnectionManager
- Ping/pong heartbeat
- Audio data forwarding (placeholder for Gemini Live in Phase 5)
- Code submission messages
- Health tracking via `mark_healthy()` on every message

### Key decisions

- **Session ID unification** — The `session_id` generated by `ConnectionManager` is the same UUID used as `candidate_id` in `InterviewState` (LangGraph). This was a deliberate fix to prevent routing mismatches between WebSocket messages and the graph.
- **DB-first join flow** — `candidate.py` creates the DB session first to get the canonical UUID, then passes it to `add_candidate_to_room()`. This prevents the in-memory dict key mismatch bug that existed in v2.
- **No Supabase** — All auth is local PostgreSQL. Dev mode accepts any valid UUID token.

---

## Phase 4: LangGraph Core & Background Tasks

**Commit:** `a85b085` — 2026-06-16 00:01:57  
**Workload:** ~30% of total effort

### What was created

| File | Lines | Purpose |
|---|---|---|
| `agents/state.py` | 68 | InterviewState TypedDict + InterviewStore singleton |
| `agents/tools.py` | 47 | Gemini tool definitions (advance_stage, submit_code) |
| `agents/nodes.py` | 167 | Stage prompts + summarize_stage() via Instructor |
| `agents/graph.py` | 112 | LangGraph 5-stage flow + advance_stage() with DB persistence |
| `tasks/llm_client.py` | 45 | Instructor client factory for Google Gemini |
| `tasks/q_generator.py` | 247 | Technical/DSA/SQL question generation |
| `tasks/code_grader.py` | 82 | LLM-as-a-judge code grading |
| `tasks/resume_parser.py` | 100 | Skill extraction + JD matching |

### InterviewState

A TypedDict with 14 fields representing the full interview state:

```python
class InterviewState(TypedDict):
    candidate_id: str          # session_id from ConnectionManager
    current_stage: str         # INTRO | EXPERIENCE | DSA | SQL | REPORT
    status: str                # initializing | processing | ready | error
    resume_text: str
    jd_text: str
    matched_skills: List[dict] # [{"skill": "Python", "match_level": "high"}]
    technical_questions: List[dict]
    dsa_question: Optional[dict]
    sql_question: Optional[dict]
    current_question_index: int
    transcript: List[dict]     # [{"role": "user"|"model", "text": "...", "stage": "..."}]
    feedback: List[str]
    code_submission: Optional[str]
    code_grade: Optional[dict]
    ui_view: str               # avatar | skills | monaco | report
    error_message: Optional[str]
    context_summary: Optional[str]  # Sliding context window
```

### InterviewStore

In-memory singleton keyed by `candidate_id`. Methods: `get()`, `set()`, `update()`, `delete()`. Validates `current_stage` against `VALID_STAGES` and `status` against `VALID_STATUSES` on every update.

### LangGraph flow

```
START → INTRO → EXPERIENCE → DSA → SQL → REPORT → END
```

A strict linear state machine. Each node sets `current_stage` and `ui_view`. The graph is compiled at import time.

**`advance_stage()`** is the main entry point called by Gemini tool calls:
1. Gets current state from InterviewStore
2. Validates the transition against `VALID_TRANSITIONS`
3. Runs `summarize_stage()` — LLM call to summarize conversation so far
4. Saves summary to both in-memory store AND PostgreSQL `stage_summaries` table
5. Updates `current_stage` in PostgreSQL `interview_sessions` table
6. Invokes the LangGraph with the full state
7. Syncs result back to InterviewStore

### Stage prompts

Each stage has a dedicated prompt generator that constructs the Gemini system instruction:

- **INTRO** — Greet, explain structure, ask about background
- **EXPERIENCE** — Pick from question bank, deep-dive into skills
- **DSA** — Present coding problem, guide through solution
- **SQL** — Present SQL challenge, wait for query
- **REPORT** — Thank candidate, direct to dashboard

All prompts inject `context_summary` from the previous stage (sliding context window).

### Gemini tool definitions

Two tools registered with Gemini:
- **`advance_stage(next_node, reason)`** — Transitions to next stage. Enum constraint enforced via `format="enum"`.
- **`submit_code(code)`** — Submits code/SQL for grading.

### Background tasks

**QuestionGenerator** — Uses Instructor + Gemini to generate:
- 5 technical questions from resume skills
- 1 DSA coding question (LeetCode style)
- 1 SQL question with schema

Has `resolve_skills()` helper that prioritizes `skills_override` from room config over extracted resume skills.

**CodeGrader** — LLM-as-a-judge grading with structured output:
- Overall grade (0-10)
- Sub-scores: correctness, complexity, edge_cases, clarity
- Feedback: summary, strengths, weaknesses, fix_suggestions

**ResumeSkillMatcher** — Extracts skills from resume text aligned with job description:
- Accepts PDF or text input
- Returns matched skills with match_level (low/medium/high)
- Excludes soft skills, focuses on technical competencies

### Sliding context window

To prevent context bloat in long interviews:
1. When `advance_stage()` is called, `summarize_stage()` runs first
2. Uses Instructor + Gemini Flash to produce a <150 word summary
3. Summary is saved to PostgreSQL `stage_summaries` table (upsert)
4. Summary is injected into the next stage's prompt as `Previous Phase Summary`

### Key decisions

- **Google provider (not Vertex AI)** — `llm_client.py` defaults to `"google/gemini-2.5-flash"` which uses the `google-genai` package. The earlier `"vertexai/"` default required `google-cloud-aiplatform` which wasn't installed.
- **Full state to ainvoke()** — `advance_stage()` passes the complete `InterviewState` to the graph, not just 2 fields. Prevents KeyError if nodes ever access other state fields.
- **Separate VALID_STAGES and VALID_STATUSES** — `VALID_STAGES = {"INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"}` for stage transitions. `VALID_STATUSES = {"initializing", "processing", "ready", "error"}` for session status. Prevents accidentally setting `current_stage="INITIALIZING"`.
- **Single UserProfile** — Lives in `core/auth.py`. Removed duplicate from `api/models.py`.

---

## Bug Fixes & Audit

A comprehensive code review identified and fixed 15 issues across all phases:

### CRITICAL (5 — fixed)

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `session_manager.py` | `list.append(a, b)` TypeError | Changed to `list.append((a, b))` |
| 2 | `candidate.py` | Session ID overwrite broke dict keys | DB session created first, UUID passed to manager |
| 3 | `main.py` | No WebSocket route handler | Created `api/websocket.py` with full handler |
| 4 | `llm_client.py` | `"vertexai/"` provider missing dependency | Changed to `"google/"` |
| 5 | `tools.py` | Missing `format="enum"` on Gemini Schema | Added `format="enum"` |

### HIGH (5 — fixed)

| # | File | Issue | Fix |
|---|------|-------|-----|
| 6 | `service.py` | `save_stage_summary` crashed on duplicate | Upsert via `ON CONFLICT DO UPDATE` |
| 7 | `service.py` | `save_code_submission` crashed on resubmit | Upsert via `ON CONFLICT DO UPDATE` |
| 8 | `models.py` | `Evaluation` allowed duplicate sessions | Added `UniqueConstraint('session_id')` |
| 9 | `graph.py` | `ainvoke()` received partial state | Now passes full `InterviewState` |
| 10 | `session_manager.py` | `mark_healthy()` never called | Called on every WebSocket message |

### MEDIUM (3 — fixed)

| # | File | Issue | Fix |
|---|------|-------|-----|
| 14 | `nodes.py` | Hardcoded `"vertexai/gemini-2.5-flash"` | Changed to `get_instructor_client()` (uses default) |
| 15 | `state.py` | `VALID_STAGES` conflated stages/statuses | Split into `VALID_STAGES` + `VALID_STATUSES` |
| 12 | `auth.py` + `models.py` | Duplicate `UserProfile` class | Removed from `api/models.py`, canonical in `core/auth.py` |

---

## Architectural Decisions

### In-memory vs PostgreSQL

The `InterviewStore` and `ConnectionManager` are both in-memory. This is intentional for the MVP:
- No horizontal scaling needed
- Simple dev experience
- `advance_stage()` bridges the gap by persisting summaries and stage transitions to PostgreSQL on every advancement

### ID unification

`session_id` (ConnectionManager) = `candidate_id` (InterviewState) = `session_id` (PostgreSQL InterviewSession). One UUID flows through the entire system. This was a critical fix — the original v2 had separate IDs that caused routing failures.

### No Supabase

All auth is local PostgreSQL. Dev mode: token = user UUID. No JWT, no OAuth, no external dependencies for auth.

### LangGraph as orchestrator

The graph enforces the interview flow. Gemini calls `advance_stage()` as a tool, which invokes the graph. The graph nodes don't contain business logic — they just set `current_stage` and `ui_view`. The real intelligence is in the prompt generators and the Gemini model itself.

---

## What's Next

**Phase 5: Voice Integration** — Port GeminiLive session, merge with v3 BaseLiveSession, implement LangGraph→Voice bridge, sliding context injection.

**Phase 6: Frontend Foundation** — Port admin dashboard, candidate flow, interview room with dynamic UI switching.

**Phase 7: Background Tasks Integration** — Wire QuestionGenerator and CodeGrader into the interview flow.

**Phase 8: Polish & Testing** — Error handling, edge cases, end-to-end testing.

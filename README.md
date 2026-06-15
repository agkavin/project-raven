# Project Raven

AI-powered technical interviewer with live voice conversations, 5-stage orchestration, and real-time code evaluation.

---

## What It Does

Project Raven conducts technical interviews autonomously. A candidate joins a room via a room code, connects over WebSocket, and speaks with an AI interviewer powered by Google Gemini's Multimodal Live API. The interview follows a structured flow:

```
Introduction → Experience & Skills → DSA Coding → SQL Challenge → Report
```

Each stage is orchestrated by a LangGraph state machine with sliding context window summarization to prevent context bloat. Code submissions are graded in real-time by an LLM-as-a-judge. Results are persisted to PostgreSQL with radar chart visualizations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                     │
│  Admin Dashboard │ Candidate Flow │ Interview Room (WS)  │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket
┌──────────────────────────┴──────────────────────────────┐
│                   Backend (FastAPI)                       │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  REST API    │  │  WebSocket   │  │  Background   │  │
│  │  admin.py    │  │  websocket.py│  │  Tasks        │  │
│  │  candidate.py│  │  voice hook  │  │  q_generator  │  │
│  └──────┬───────┘  └──────┬───────┘  │  code_grader  │  │
│         │                 │          │  resume_parser │  │
│         ▼                 ▼          └───────┬───────┘  │
│  ┌─────────────┐  ┌──────────────┐          │          │
│  │  Database    │  │  LangGraph   │◄─────────┘          │
│  │  PostgreSQL  │  │  5-stage FSM │                     │
│  │  8 tables    │  │  + Gemini    │                     │
│  └─────────────┘  └──────┬───────┘                     │
│                           │                             │
│                    ┌──────┴───────┐                     │
│                    │  Gemini Live  │                     │
│                    │  Voice API    │                     │
│                    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy (async), LangGraph |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS |
| **Database** | PostgreSQL 16 (Docker Compose, port 5433) |
| **AI** | Google Gemini Multimodal Live API, Instructor |
| **Code Editor** | Monaco Editor |
| **Charts** | Recharts (radar charts) |
| **State** | Zustand (frontend), InterviewStore (backend) |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.13+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### 1. Start Database

```bash
docker-compose up -d
```

PostgreSQL starts on port 5433 with database `project_raven`, user `postgres`, password `postgres`.

### 2. Start Backend

```bash
cd backend
uv sync
uv run python main.py
```

Backend runs on port 8000. Tables are created automatically on startup.

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:3000.

### 4. Test It

```bash
# Health check
curl http://localhost:8000/health

# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'

# Create a room (use token from login)
curl -X POST http://localhost:8000/admin/rooms \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"interview_type": "voice", "timeout_minutes": 30}'
```

---

## Project Structure

```
project-raven-new/
├── backend/
│   ├── agents/              # LangGraph orchestration
│   │   ├── state.py         # InterviewState + InterviewStore
│   │   ├── graph.py         # 5-stage FSM + advance_stage()
│   │   ├── nodes.py         # Stage prompts + summarizer
│   │   └── tools.py         # Gemini tool definitions
│   ├── api/                 # REST + WebSocket endpoints
│   │   ├── admin.py         # Room management, evaluations
│   │   ├── candidate.py     # Join, validate, resume analysis
│   │   ├── websocket.py     # Live voice WebSocket
│   │   └── models.py        # Pydantic request/response
│   ├── core/                # Auth + session management
│   │   ├── auth.py          # Local PostgreSQL auth
│   │   └── session_manager.py  # ConnectionManager (WS, rooms)
│   ├── db/                  # Database layer
│   │   ├── database.py      # Async engine + sessions
│   │   ├── models.py        # 8 SQLAlchemy ORM models
│   │   └── service.py       # CRUD operations
│   ├── tasks/               # Background AI tasks
│   │   ├── llm_client.py    # Instructor client factory
│   │   ├── q_generator.py   # Question generation
│   │   ├── code_grader.py   # LLM-as-a-judge
│   │   └── resume_parser.py # Skill extraction
│   ├── services/            # External service integrations
│   ├── utils/               # Helpers
│   │   └── room_code.py     # Room code generation
│   ├── main.py              # FastAPI entry point
│   └── pyproject.toml       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router pages
│   │   ├── components/      # UI components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/stores/      # Zustand stores
│   │   └── types/           # TypeScript types
│   └── package.json         # Node dependencies
├── docs/
│   ├── PROJECT_REQUIREMENTS.md  # Full PRD (973 lines)
│   └── walkthrough.md          # Development walkthrough
├── docker-compose.yml       # PostgreSQL 16
└── .env                     # Environment variables
```

---

## API Endpoints

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Dev login (email → token) |
| GET | `/auth/me` | Get current user profile |

### Admin (requires auth)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/admin/rooms` | Create interview room |
| GET | `/admin/rooms` | List all rooms |
| GET | `/admin/rooms/{code}` | Get room details |
| POST | `/admin/rooms/{code}/close` | Close room |
| GET | `/admin/rooms/{code}/candidates` | List candidates |
| GET | `/admin/evaluations` | List evaluations |
| GET | `/admin/evaluations/export` | Export as CSV |
| GET | `/admin/candidates/performance` | Performance metrics |

### Candidate (no auth)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/resume/analyze` | Extract skills from resume |
| GET | `/rooms/{code}/validate` | Check room availability |
| POST | `/rooms/{code}/join` | Join room → get WebSocket URL |

### WebSocket

| Path | Description |
|------|-------------|
| `ws://localhost:8000/ws/voice/{room_code}/{session_id}` | Live voice interview |

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/project_raven

# Google Cloud (for Gemini)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=your-gemini-api-key

# Server
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_REQUIREMENTS.md](docs/PROJECT_REQUIREMENTS.md) | Full product requirements document — architecture, schema, API spec, implementation plan |
| [walkthrough.md](docs/walkthrough.md) | Detailed development walkthrough — what was built in each phase, why decisions were made |

---

## Development Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Done | Project setup, frontend scaffold, Docker Compose |
| Phase 2 | Done | Database layer — 8 tables, async CRUD, upserts |
| Phase 3 | Done | Auth, room management, WebSocket lifecycle |
| Phase 4 | Done | LangGraph 5-stage flow, sliding context, background tasks |
| Phase 5 | Pending | Voice integration — Gemini Live API |
| Phase 6 | Pending | Frontend — admin dashboard, candidate flow, interview room |
| Phase 7 | Pending | Wire background tasks into interview flow |
| Phase 8 | Pending | Polish, error handling, testing |

---

## License

Private — Not for distribution.

# Project Raven: Complete Build Specification

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Database Schema](#5-database-schema)
6. [API Endpoints](#6-api-endpoints)
7. [Frontend Components](#7-frontend-components)
8. [Backend Components](#8-backend-components)
9. [Integration Points](#9-integration-points)
10. [Action Plan: What to Take from Each File](#10-action-plan)
11. [Implementation Phases](#11-implementation-phases)
12. [Environment Setup](#12-environment-setup)

---

## 1. Project Overview

### 1.1 What We Are Building

**Project Raven** is an AI-powered technical interviewer that conducts real-time voice interviews, evaluates candidates, and generates comprehensive performance reports. The system uses Gemini Multimodal Live API for voice conversations, LangGraph for interview orchestration, and a sliding context window to manage conversation memory.

### 1.2 Core Value Proposition

- **For Companies**: Automated, consistent technical interviews at scale
- **For Candidates**: Natural voice-based interview experience
- **For Admins**: Full control over interview configuration, real-time monitoring, and detailed analytics

### 1.3 Key Differentiators

1. **Live Voice**: Real-time voice conversations via Gemini Multimodal Live API (not text chat)
2. **Sliding Context Window**: Summarizes previous stages, only keeps current stage context
3. **Dynamic UI**: Frontend changes based on interview stage (voice for intro, code editor for DSA, etc.)
4. **Multi-Session**: Support for concurrent interviews across multiple rooms
5. **5-Stage Structured Flow**: Intro → Experience → DSA → SQL → Report

---

## 2. Features

### 2.1 Voice Interview Features

| Feature | Description |
|---------|-------------|
| Real-time Voice | Gemini Multimodal Live API for natural conversation |
| Echo Guard | Prevents AI from hearing its own output |
| Barge-in Support | Candidate can interrupt AI at any time |
| Mute/Unmute | Candidate can mute microphone |
| Speaker Mute | Candidate can mute AI output |
| Voice Visualizer | Animated waveform showing who is speaking |
| Transcript Capture | Full transcript of both sides for report generation |

### 2.2 Interview Flow Features

| Feature | Description |
|---------|-------------|
| 5-Stage Flow | Intro → Experience → DSA → SQL → Report |
| Sliding Context | Summarizes each stage, only current stage in context |
| Dynamic Prompts | Stage-specific system instructions for Gemini |
| Tool Calls | AI can call `advance_stage` and `submit_code` tools |
| Code Submission | Monaco editor for DSA/SQL questions |
| Code Grading | LLM-as-a-judge for code evaluation |
| Report Generation | Radar chart with 5 dimensions + executive feedback |

### 2.3 Admin Features

| Feature | Description |
|---------|-------------|
| Room Management | Create/close interview rooms with configurations |
| Candidate Tracking | Monitor all candidates in a room |
| Real-time Monitoring | Live feed of evaluations as they happen |
| Evaluations Dashboard | Table + real-time feed of all evaluations |
| Candidate Performance | Per-candidate skill breakdowns |
| CSV Export | Export evaluations to CSV |
| Job Role Management | Create/manage job role templates |

### 2.4 Candidate Features

| Feature | Description |
|---------|-------------|
| Room Join | Join via room code (no signup required) |
| Resume Upload | PDF upload or text paste |
| Skill Matching | AI extracts skills from resume + JD |
| Interview Stages | Navigate through 5 interview stages |
| Code Editor | Monaco-based code editor for DSA/SQL |
| Final Report | View radar chart and feedback |

### 2.5 Multi-Session Features

| Feature | Description |
|---------|-------------|
| Concurrent Interviews | Multiple candidates in same room |
| Room Isolation | Each room has its own sessions |
| Session Persistence | PostgreSQL-backed session storage |
| Admin Monitoring | Admin can watch any active session |

---

## 3. Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Admin    │  │ Candidate│  │Interview │  │  Login   │          │
│  │Dashboard │  │  Join    │  │  Room    │  │  Page    │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘          │
│       │              │              │                               │
│       └──────────────┴──────────────┴───────────────┐              │
│                                                     │              │
│                    WebSocket + REST API              │              │
└─────────────────────────────────────────────────────┼──────────────┘
                                                      │
┌─────────────────────────────────────────────────────┼──────────────┐
│                        BACKEND (FastAPI)            │              │
│                                                     ▼              │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                     API Layer                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│  │  │  Admin   │  │Candidate │  │  Voice   │  │  Auth    │   │  │
│  │  │ Routes   │  │ Routes   │  │  WS      │  │  Deps    │   │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘   │  │
│  └───────┼──────────────┼──────────────┼───────────────────────┘  │
│          │              │              │                           │
│          ▼              ▼              ▼                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   Service Layer                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│  │  │ Session  │  │   Room   │  │  Gemini  │  │  LangGraph│   │  │
│  │  │ Manager  │  │ Manager  │  │  Live    │  │  Engine   │   │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │  │
│  └───────┼──────────────┼──────────────┼──────────────┼─────────┘  │
│          │              │              │              │             │
│          ▼              ▼              ▼              ▼             │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                   Data Layer                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │
│  │  │PostgreSQL│  │  Redis   │  │ Gemini   │  │ Background│   │  │
│  │  │ Database │  │ (Future) │  │   API    │  │   Tasks  │   │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Interview Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INTERVIEW FLOW                                    │
│                                                                     │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐    ┌─────────┐     │
│  │  INTRO  │───▶│ EXPERIENCE │───▶│   DSA   │───▶│   SQL   │     │
│  │ (Voice) │    │  (Voice)   │    │ (Editor)│    │ (Editor)│     │
│  └────┬────┘    └─────┬──────┘    └────┬────┘    └────┬────┘     │
│       │               │                │               │           │
│       ▼               ▼                ▼               ▼           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Sliding Context Window                          │  │
│  │  • Summarize current stage conversation                     │  │
│  │  • Save summary to database                                 │  │
│  │  • Update Gemini session with new stage instructions        │  │
│  │  • Reset context for new stage                               │  │
│  └─────────────────────────────────────────────────────────────┘  │
│       │               │                │               │           │
│       ▼               ▼                ▼               ▼           │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐    ┌─────────┐     │
│  │ Summary │    │  Summary   │    │ Summary │    │ Summary │     │
│  │ Saved   │    │  Saved     │    │ Saved   │    │ Saved   │     │
│  └─────────┘    └────────────┘    └─────────┘    └─────────┘     │
│                                                                     │
│                                    ┌─────────┐                     │
│                                    │ REPORT  │                     │
│                                    │ (Visual)│                     │
│                                    └─────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Voice Session Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VOICE SESSION                                     │
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐         ┌────────────┐ │
│  │   Browser    │         │   Backend    │         │   Gemini   │ │
│  │  (Next.js)   │         │  (FastAPI)   │         │ Live API   │ │
│  └──────┬───────┘         └──────┬───────┘         └─────┬──────┘ │
│         │                        │                       │         │
│         │   WebSocket Binary     │   WebSocket Binary    │         │
│         │   (PCM Audio)          │   (PCM Audio)         │         │
│         │───────────────────────▶│──────────────────────▶│         │
│         │                        │                       │         │
│         │◀───────────────────────│◀──────────────────────│         │
│         │   WebSocket Binary     │   WebSocket Binary    │         │
│         │   (PCM Audio)          │   (PCM Audio)         │         │
│         │                        │                       │         │
│         │   WebSocket Text       │   WebSocket Text      │         │
│         │   (JSON Control)       │   (JSON Control)      │         │
│         │───────────────────────▶│──────────────────────▶│         │
│         │                        │                       │         │
│         │◀───────────────────────│◀──────────────────────│         │
│         │   WebSocket Text       │   Tool Calls          │         │
│         │   (ui_event, etc.)     │   (advance_stage)     │         │
│         │                        │                       │         │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 LangGraph Orchestration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH ORCHESTRATION                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    InterviewState                            │   │
│  │  • candidate_id    • current_stage    • resume_text         │   │
│  │  • jd_text         • matched_skills   • technical_questions │   │
│  │  • dsa_question    • sql_question     • transcript          │   │
│  │  • code_submission • code_grade       • context_summary     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    StateGraph                                │   │
│  │                                                              │   │
│  │  START ──▶ INTRO ──▶ EXPERIENCE ──▶ DSA ──▶ SQL ──▶ REPORT │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    advance_stage()                           │   │
│  │                                                              │   │
│  │  1. Validate transition (VALID_TRANSITIONS dict)             │   │
│  │  2. summarize_stage() - LLM summarization                   │   │
│  │  3. Save summary to store                                    │   │
│  │  4. Invoke graph with new stage                              │   │
│  │  5. Update store with graph result                           │   │
│  │  6. Send ui_event to frontend                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Tool Calls                                │   │
│  │                                                              │   │
│  │  advance_stage(next_node, reason)                            │   │
│  │  submit_code(code)                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Tech Stack

### 4.1 Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Primary language |
| FastAPI | 0.136+ | Web framework |
| LangGraph | 1.1+ | Interview orchestration |
| Google GenAI SDK | 1.75+ | Gemini Live API |
| Instructor | 1.0+ | Structured LLM output |
| SQLAlchemy | 2.0+ | ORM (async) |
| PostgreSQL | 14+ | Primary database |
| Pydantic | 2.13+ | Data validation |
| Uvicorn | 0.46+ | ASGI server |

### 4.2 Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 16+ | React framework |
| React | 19+ | UI library |
| TypeScript | 5+ | Type safety |
| Tailwind CSS | 3.4+ | Styling |
| Monaco Editor | 4.7+ | Code editor |
| Recharts | 3.8+ | Charts/radar |
| Zustand | 5.0+ | State management |
| Lucide React | 0.564+ | Icons |

### 4.3 AI Services

| Service | Purpose |
|---------|---------|
| Gemini Multimodal Live API | Real-time voice conversations |
| Gemini 2.5 Flash | LLM for evaluation, summarization, question generation |
| Vertex AI | Google Cloud AI platform |

### 4.4 Development Tools

| Tool | Purpose |
|------|---------|
| uv | Python package management |
| npm | Node package management |
| Alembic | Database migrations |
| ESLint | TypeScript linting |
| Prettier | Code formatting |

---

## 5. Database Schema

### 5.1 Core Tables

```sql
-- =====================================================
-- ORGANISATIONS
-- =====================================================
CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_organisations_slug UNIQUE (slug)
);

-- =====================================================
-- USERS (Admin/Super Admin)
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY,  -- Matches Supabase Auth user UUID
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL CHECK (role IN ('super_admin', 'admin')),
    org_id UUID REFERENCES organisations(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_users_email UNIQUE (email)
);

-- =====================================================
-- JOB ROLES (Templates)
-- =====================================================
CREATE TABLE job_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    skills JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_job_roles_code UNIQUE (code)
);

-- =====================================================
-- INTERVIEW ROOMS
-- =====================================================
CREATE TABLE interview_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_code VARCHAR(20) NOT NULL UNIQUE,
    created_by UUID REFERENCES users(id),
    
    -- Configuration
    interview_type VARCHAR(50) NOT NULL DEFAULT 'voice',  -- 'voice', 'text', 'staged'
    stages JSONB NOT NULL DEFAULT '["INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"]',
    timeout_minutes INTEGER NOT NULL DEFAULT 30,
    max_candidates INTEGER NOT NULL DEFAULT 50,
    
    -- Job matching
    jd_text TEXT,
    skills_override JSONB,
    job_role_id UUID REFERENCES job_roles(id),
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_interview_rooms_code UNIQUE (room_code)
);

-- =====================================================
-- INTERVIEW SESSIONS
-- =====================================================
CREATE TABLE interview_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES interview_rooms(id) ON DELETE CASCADE,
    
    -- Candidate info
    candidate_name VARCHAR(255),
    candidate_email VARCHAR(255),
    resume_text TEXT,
    
    -- Interview state
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    current_stage VARCHAR(20) NOT NULL DEFAULT 'INTRO',
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_session_room_candidate UNIQUE (room_id, candidate_email)
);

-- =====================================================
-- STAGE SUMMARIES (Sliding Context Window)
-- =====================================================
CREATE TABLE stage_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    stage VARCHAR(20) NOT NULL,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_stage_summary UNIQUE (session_id, stage)
);

-- =====================================================
-- CODE SUBMISSIONS
-- =====================================================
CREATE TABLE code_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    stage VARCHAR(20) NOT NULL,  -- 'DSA' or 'SQL'
    code TEXT NOT NULL,
    language VARCHAR(50),
    grade JSONB,  -- {correctness: 8, complexity: 7, edge_cases: 6, clarity: 9}
    feedback TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_code_submission UNIQUE (session_id, stage)
);

-- =====================================================
-- EVALUATIONS
-- =====================================================
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    
    -- Overall scores
    overall_score FLOAT,
    stage_scores JSONB,  -- {intro: 8, experience: 7, dsa: 9, sql: 6}
    technical_score FLOAT,
    communication_score FLOAT,
    
    -- Recommendation
    recommendation VARCHAR(20) CHECK (recommendation IN ('strong_hire', 'hire', 'maybe', 'no_hire')),
    
    -- Feedback
    feedback TEXT,
    strengths JSONB,
    weaknesses JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.2 Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│Organisation │────<│    User     │     │  Job Role   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │Interview    │────>│  Room       │
                    │ Room        │     │  Config     │
                    └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Interview   │
                    │  Session    │
                    └─────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │   Stage     │ │   Code      │ │ Evaluation  │
     │  Summary    │ │ Submission  │ │             │
     └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 6. API Endpoints

### 6.1 Auth Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/auth/me` | Get current user profile | Required |
| POST | `/auth/login` | Login (dev mode) | Public |

### 6.2 Admin Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/admin/rooms/create` | Create interview room | Admin |
| GET | `/admin/rooms` | List all rooms | Admin |
| GET | `/admin/rooms/{room_code}` | Get room details | Admin |
| POST | `/admin/rooms/{room_code}/close` | Close room | Admin |
| GET | `/admin/rooms/{room_code}/candidates` | List candidates in room | Admin |
| POST | `/admin/jd/analyze` | Analyze job description | Admin |
| GET | `/admin/job-roles` | List job roles | Admin |
| POST | `/admin/job-roles` | Create job role | Admin |
| PUT | `/admin/job-roles/{role_id}` | Update job role | Admin |
| DELETE | `/admin/job-roles/{role_id}` | Delete job role | Admin |
| POST | `/admin/job-roles/generate` | Generate skills for role | Admin |
| GET | `/admin/evaluations` | List evaluations | Admin |
| GET | `/admin/candidates/performance` | Candidate performance | Admin |
| POST | `/admin/export/csv` | Export evaluations CSV | Admin |

### 6.3 Candidate Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/rooms/{room_code}/validate` | Validate room exists | Public |
| POST | `/rooms/{room_code}/join` | Join room as candidate | Public |
| POST | `/resume/analyze` | Analyze resume skills | Public |

### 6.4 Voice WebSocket Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| WS | `/ws/voice/{room_code}/{session_id}` | Voice interview session | Room |

### 6.5 Health Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | Public |

---

## 7. Frontend Components

### 7.1 Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Entry point with admin/candidate cards |
| Login | `/login` | Email/password login form |
| Admin Dashboard | `/admin` | Room management, evaluations, performance |
| Candidate Join | `/candidate/join` | Enter room code, upload resume |
| Candidate Interview | `/candidate/interview/[sessionId]` | Text-based interview |
| Voice Interview | `/voice/interview/[sessionId]` | Voice-based interview |
| Super Admin | `/super-admin` | Platform stats, organisations |
| Super Admin Sessions | `/super-admin/sessions` | Session management |
| Super Admin Organisations | `/super-admin/organisations` | Org CRUD |
| Super Admin Credits | `/super-admin/credits` | Credit management |
| Super Admin Admins | `/super-admin/admins` | Admin user management |

### 7.2 Admin Components

| Component | File | Description |
|-----------|------|-------------|
| RoomManagementTab | `components/admin/RoomManagementTab.tsx` | Room creation wizard |
| EvaluationsDashboard | `components/admin/EvaluationsDashboard.tsx` | Evaluations view |
| EvaluationTable | `components/admin/EvaluationTable.tsx` | Sortable/filterable table |
| RealtimeFeed | `components/admin/RealtimeFeed.tsx` | Live evaluation feed |
| CandidatePerformanceTab | `components/admin/CandidatePerformanceTab.tsx` | Performance grid |
| CandidateCard | `components/admin/CandidateCard.tsx` | Individual candidate card |
| ExportButton | `components/admin/ExportButton.tsx` | CSV export |

### 7.3 Interview Components

| Component | File | Description |
|-----------|------|-------------|
| InterviewRoom | `components/InterviewRoom.tsx` | Main interview orchestrator |
| CodeEditor | `components/CodeEditor.tsx` | Monaco-based code editor |
| SkillsView | `components/SkillsView.tsx` | Skill alignment matrix |
| ReportView | `components/ReportView.tsx` | Radar chart + feedback |
| VoiceVisualizer | `components/VoiceVisualizer.tsx` | Animated voice waveform |

### 7.4 UI Components

| Component | File | Description |
|-----------|------|-------------|
| Button | `components/ui/button.tsx` | Reusable button |
| Card | `components/ui/card.tsx` | Card container |
| Input | `components/ui/input.tsx` | Form input |
| Textarea | `components/ui/textarea.tsx` | Form textarea |
| Select | `components/ui/select.tsx` | Custom select dropdown |
| Tabs | `components/ui/tabs.tsx` | Custom tabs |
| Table | `components/ui/table.tsx` | Data table |
| Badge | `components/ui/badge.tsx` | Status badge |

### 7.5 Layout Components

| Component | File | Description |
|-----------|------|-------------|
| AppShell | `components/layout/AppShell.tsx` | Dashboard layout |
| Sidebar | `components/layout/Sidebar.tsx` | Navigation sidebar |
| Topbar | `components/layout/Topbar.tsx` | Top navigation bar |
| CreditBadge | `components/layout/CreditBadge.tsx` | Credit balance display |

### 7.6 Hooks

| Hook | File | Description |
|------|------|-------------|
| useVoiceWebSocket | `hooks/useVoiceWebSocket.ts` | Voice WebSocket + audio |
| useWebSocket | `hooks/useWebSocket.ts` | Text WebSocket |

### 7.7 Stores

| Store | File | Description |
|-------|------|-------------|
| authStore | `lib/stores/authStore.ts` | Authentication state |
| adminStore | `lib/stores/adminStore.ts` | Admin dashboard state |
| candidateStore | `lib/stores/candidateStore.ts` | Candidate interview state |

---

## 8. Backend Components

### 8.1 API Layer

| Module | File | Description |
|--------|------|-------------|
| Admin Routes | `app/routes/admin.py` | Admin API endpoints |
| Candidate Routes | `app/routes/candidate.py` | Candidate API endpoints |
| Voice WebSocket | `app/routes/voice_ws.py` | Voice WebSocket handler |
| Auth Dependencies | `app/core/auth.py` | JWT verification |

### 8.2 Service Layer

| Module | File | Description |
|--------|------|-------------|
| Session Manager | `app/core/session_manager.py` | Room/session management |
| Gemini Live Session | `app/voice_agents/base_live_session.py` | Voice session base |
| Gemini Interview Session | `app/voice_agents/gemini_live_session.py` | Voice interview logic |
| Interview Orchestrator | `app/voice_agents/interview_orchestrator.py` | Voice orchestration |
| Filler Manager | `app/voice_agents/filler_manager.py` | Natural conversation fillers |
| Interviewer | `app/voice_agents/interviewer.py` | LLM evaluator + question gen |

### 8.3 LangGraph Layer

| Module | File | Description |
|--------|------|-------------|
| State Definition | `agents/state.py` | InterviewState TypedDict |
| Graph Definition | `agents/graph.py` | LangGraph state machine |
| Node Prompts | `agents/nodes.py` | Stage prompts + summarizer |
| Tool Definitions | `agents/tools.py` | Gemini tool declarations |

### 8.4 Background Tasks

| Module | File | Description |
|--------|------|-------------|
| Question Generator | `tasks/q_generator.py` | Technical/DSA/SQL questions |
| Code Grader | `tasks/code_grader.py` | Code evaluation |
| Resume Parser | `tasks/resume_parser.py` | Skill extraction |
| LLM Client | `tasks/llm_client.py` | Instructor client factory |

### 8.5 Data Layer

| Module | File | Description |
|--------|------|-------------|
| Database | `app/db/database.py` | Async SQLAlchemy setup |
| Models | `app/db/models.py` | ORM models |
| Service | `app/db/service.py` | CRUD operations |

---

## 9. Integration Points

### 9.1 LangGraph → Voice Session Bridge

```
When LangGraph advances stage:
1. summarize_stage() → generate summary via LLM
2. store.update(context_summary=summary)
3. GeminiLive.update_session(new_system_instruction)
4. WebSocket sends ui_event to frontend
5. Frontend switches view (avatar → monaco → report)
```

### 9.2 Room → Session → State Mapping

```
Room (DB) → CandidateSession (DB) → InterviewState (In-Memory)
- room_code + session_id → candidate_id
- ConnectionManager tracks active sessions
- InterviewStore maps candidate_id to LangGraph state
```

### 9.3 Context Summarization → Voice Injection

```
On stage transition:
1. Extract last N transcript turns
2. summarize_stage() via Instructor + Gemini
3. Inject summary into Gemini session via inject_context()
4. Update system instruction with new stage prompt
```

### 9.4 Stage Transitions → UI Updates

```
LangGraph node returns:
- current_stage: "DSA"
- ui_view: "monaco"

WebSocket sends:
{
  "type": "ui_event",
  "view": "monaco",
  "stage": "DSA",
  "question": {...}
}

Frontend switches:
- avatar → VoiceVisualizer
- monaco → CodeEditor + DSA/SQL question
- report → ReportView + radar chart
```

---

## 10. Action Plan

### 10.1 What to Take from Each Project

#### From v2 Backend (`/home/marcus/code/project-raven/backend/`)

| File | Lines | Action | Notes |
|------|-------|--------|-------|
| `agents/state.py` | 66 | **TAKE** | InterviewState TypedDict, InterviewStore singleton |
| `agents/graph.py` | 102 | **TAKE** | LangGraph 5-stage state machine |
| `agents/nodes.py` | 168 | **TAKE** | Stage prompts + summarizer |
| `agents/tools.py` | 48 | **TAKE** | Gemini tool definitions |
| `tasks/q_generator.py` | 275 | **TAKE** | Question generation |
| `tasks/code_grader.py` | 100 | **TAKE** | Code grading |
| `tasks/resume_parser.py` | 128 | **TAKE** | Resume skill extraction |
| `tasks/llm_client.py` | 51 | **TAKE** | Instructor client factory |
| `services/gemini.py` | 226 | **TAKE & MERGE** | Voice session (merge with v3) |
| `api/websocket.py` | 183 | **TAKE & MERGE** | WebSocket handler (merge with v3) |
| `api/candidate.py` | 142 | **TAKE & MODIFY** | Candidate endpoints |
| `main.py` | 44 | **TAKE & MODIFY** | FastAPI entry point |
| `pyproject.toml` | 22 | **TAKE & MODIFY** | Dependencies |

#### From v3 Backend (`/home/marcus/code/project-raven/interview-ai/backend/`)

| File | Lines | Action | Notes |
|------|-------|--------|-------|
| `app/core/auth.py` | 170 | **TAKE** | Supabase JWT auth |
| `app/core/session_manager.py` | 376 | **TAKE** | Room/session management |
| `app/db/database.py` | 92 | **TAKE** | Async SQLAlchemy setup |
| `app/db/models.py` | 255 | **TAKE & EXTEND** | ORM models (extend for 5-stage) |
| `app/db/service.py` | 590 | **TAKE & MODIFY** | CRUD operations |
| `app/models/room.py` | 147 | **TAKE** | Room Pydantic models |
| `app/routes/admin.py` | 526 | **TAKE** | Admin API endpoints |
| `app/routes/candidate.py` | 245 | **TAKE & MODIFY** | Candidate API |
| `app/routes/voice_ws.py` | 228 | **TAKE & MERGE** | Voice WebSocket |
| `app/voice_agents/base_live_session.py` | 396 | **TAKE & MERGE** | Voice session base |
| `app/voice_agents/gemini_live_session.py` | 360 | **TAKE & MERGE** | Voice interview |
| `app/voice_agents/interview_orchestrator.py` | 426 | **TAKE & MERGE** | Voice orchestration |
| `app/voice_agents/filler_manager.py` | 203 | **TAKE** | Filler phrases |
| `app/voice_agents/interviewer.py` | 325 | **TAKE** | LLM evaluator |
| `app/main.py` | 128 | **TAKE & MODIFY** | FastAPI app factory |
| `pyproject.toml` | 36 | **TAKE & MODIFY** | Dependencies |

#### From v2 Frontend (`/home/marcus/code/project-raven/frontend/`)

| File | Lines | Action | Notes |
|------|-------|--------|-------|
| `src/hooks/useVoiceWebSocket.ts` | 308 | **TAKE & MERGE** | Voice WebSocket (merge with v3) |
| `src/components/InterviewRoom.tsx` | 318 | **TAKE & ENHANCE** | Interview room UI |
| `src/components/CodeEditor.tsx` | 94 | **TAKE** | Monaco code editor |
| `src/components/ReportView.tsx` | 90 | **TAKE & ENHANCE** | Report with radar chart |
| `src/components/SkillsView.tsx` | 48 | **TAKE** | Skill alignment matrix |
| `src/components/VoiceVisualizer.tsx` | 43 | **TAKE** | Voice waveform visualizer |
| `src/app/globals.css` | 20 | **TAKE** | Global styles |
| `src/app/layout.tsx` | 33 | **TAKE & MODIFY** | Root layout |
| `package.json` | 30 | **TAKE & MODIFY** | Dependencies |

#### From v3 Frontend (`/home/marcus/code/project-raven/interview-ai/frontend/`)

| File | Lines | Action | Notes |
|------|-------|--------|-------|
| `hooks/useVoiceWebSocket.ts` | 438 | **TAKE & MERGE** | Voice WebSocket (merge with v2) |
| `hooks/useWebSocket.ts` | 172 | **TAKE** | Text WebSocket |
| `lib/api.ts` | 200 | **TAKE** | API client |
| `lib/supabase.ts` | 18 | **TAKE** | Supabase client |
| `lib/stores/authStore.ts` | 132 | **TAKE** | Auth store |
| `lib/stores/adminStore.ts` | 257 | **TAKE** | Admin store |
| `lib/stores/candidateStore.ts` | 218 | **TAKE** | Candidate store |
| `middleware.ts` | 50 | **TAKE** | Route protection |
| `app/admin/page.tsx` | 101 | **TAKE** | Admin dashboard |
| `app/candidate/join/page.tsx` | 439 | **TAKE & MODIFY** | Candidate join |
| `app/voice/interview/[sessionId]/page.tsx` | 420 | **TAKE & MODIFY** | Voice interview |
| `components/admin/RoomManagementTab.tsx` | 733 | **TAKE** | Room management |
| `components/admin/EvaluationsDashboard.tsx` | 111 | **TAKE** | Evaluations |
| `components/admin/EvaluationTable.tsx` | 366 | **TAKE** | Evaluation table |
| `components/admin/RealtimeFeed.tsx` | 108 | **TAKE** | Real-time feed |
| `components/admin/CandidatePerformanceTab.tsx` | 69 | **TAKE** | Performance tab |
| `components/admin/CandidateCard.tsx` | 113 | **TAKE** | Candidate card |
| `components/admin/ExportButton.tsx` | 65 | **TAKE** | CSV export |
| `components/ui/*.tsx` | ~300 | **TAKE** | All UI components |
| `components/layout/*.tsx` | ~300 | **TAKE** | Layout components |
| `types/*.ts` | ~250 | **TAKE** | TypeScript types |
| `package.json` | 35 | **TAKE & MODIFY** | Dependencies |

### 10.2 What to Create New

| Component | Description | Priority |
|-----------|-------------|----------|
| Unified State Model | Merge v2 InterviewState with v3 room/session | HIGH |
| DB-Backed Store | Replace in-memory stores with PostgreSQL | HIGH |
| LangGraph-Voice Bridge | Wire transitions to Gemini session updates | HIGH |
| Room Stage Config | Allow admins to configure stages per room | MEDIUM |
| Report Generator | Aggregate all stage data into final report | HIGH |
| Real-Time Admin Feed | WebSocket monitoring of stage transitions | MEDIUM |
| Filler Phrase System | Context-aware fillers during processing | LOW |

---

## 11. Implementation Phases

### Phase 1: Project Setup (Day 1)

1. Create new repo structure
2. Initialize backend with uv
3. Initialize frontend with Next.js
4. Set up PostgreSQL database
5. Configure environment variables

### Phase 2: Database Layer (Days 2-3)

1. Create SQLAlchemy models
2. Set up Alembic migrations
3. Create database connection pool
4. Implement CRUD operations
5. Test database connectivity

### Phase 3: Auth & Room Management (Days 4-5)

1. Implement Supabase JWT auth
2. Create admin endpoints
3. Create room management
4. Create candidate join flow
5. Test room creation and joining

### Phase 4: LangGraph Core (Days 6-8)

1. Port InterviewState TypedDict
2. Port LangGraph state machine
3. Port stage prompts
4. Port summarizer
5. Port tool definitions
6. Test stage transitions

### Phase 5: Voice Integration (Days 9-12)

1. Port GeminiLive session
2. Port BaseLiveSession
3. Merge voice implementations
4. Implement LangGraph-Voice bridge
5. Implement sliding context injection
6. Test voice conversations

### Phase 6: Frontend Foundation (Days 13-15)

1. Set up Next.js app structure
2. Port UI components
3. Port layout components
4. Implement auth flow
5. Implement admin dashboard

### Phase 7: Interview UI (Days 16-18)

1. Port InterviewRoom component
2. Port CodeEditor component
3. Port VoiceVisualizer
4. Port SkillsView
5. Port ReportView
6. Implement dynamic UI switching

### Phase 8: Background Tasks (Days 19-20)

1. Port QuestionGenerator
2. Port CodeGrader
3. Port ResumeParser
4. Integrate with room join flow

### Phase 9: Polish & Testing (Days 21-23)

1. End-to-end testing
2. Error handling
3. Performance optimization
4. Documentation

---

## 12. Environment Setup

### 12.1 Backend Environment Variables

```bash
# Google AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=your-gemini-api-key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_DB_URL=postgresql+asyncpg://postgres:password@db.project.supabase.co:5432/postgres

# Application
PORT=8001
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
```

### 12.2 Frontend Environment Variables

```bash
# Backend
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8001

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 12.3 Running Locally

```bash
# Backend
cd backend
uv sync
uv run main.py

# Frontend
cd frontend
npm install
npm run dev
```

---

## Appendix A: File Counts

| Source | Files | Lines |
|--------|-------|-------|
| v2 Backend | 23 | 1,820 |
| v2 Frontend | 27 | 7,506 |
| v3 Backend | 50+ | 10,937 |
| v3 Frontend | 57 | ~8,000 |
| **Total** | **157+** | **~28,263** |

## Appendix B: Key Architectural Patterns

1. **Two-Part System**: Gemini Live = mouth/ears, LangGraph = brain
2. **Sliding Context Window**: Only stage summaries kept, not full transcripts
3. **Hard Steer vs Soft Steer**: `session_update` vs `client_content` injection
4. **UI-Ready Handshake**: Backend sends `ui_event` → frontend mounts → sends `ui_ready`
5. **Non-Blocking Architecture**: Every heavy operation runs as `asyncio.Task`
6. **Filler Phrase Strategy**: Context-aware fillers mask LLM processing time

## Appendix C: Known Issues to Address

1. Singleton bug in InterviewStore (v2 state.py)
2. Stale state references after disconnect
3. Race conditions in tool callbacks
4. `context_summary` field unused in v2
5. In-memory session storage (need PostgreSQL)
6. No automatic summarization trigger on stage transition
7. No final stage summarization for report

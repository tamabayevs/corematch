# CLAUDE.md — CoreMatch

## Project Overview

CoreMatch is an AI-powered video interview screening platform. HR users create interview campaigns, invite candidates via email/SMS, candidates record video answers in-browser, and an AI pipeline (Groq) transcribes and scores responses. HR users review scored candidates in a dashboard.

**Tech stack:** Flask (Python 3.11) backend, React 18 (Vite) frontend, PostgreSQL 15, Redis (RQ job queue), Groq API (Whisper + LLaMA), Cloudflare R2 (video storage), AWS SES (email), Twilio (SMS).

**Deployment:** Backend on Railway, frontend on Vercel.

## Repository Structure

```
corematch/
├── backend/
│   ├── ai/
│   │   └── scorer.py           # Groq AI pipeline: video → audio → transcript → score
│   ├── api/
│   │   ├── app.py              # Flask app factory, CORS, rate limiting, security headers
│   │   ├── auth.py             # Auth blueprint: signup, login, refresh, logout, password reset
│   │   ├── campaigns.py        # Campaign CRUD blueprint (JWT-protected)
│   │   ├── candidates.py       # Candidate management blueprint (JWT-protected)
│   │   ├── dashboard.py        # Dashboard stats blueprint (JWT-protected)
│   │   ├── middleware.py        # JWT auth decorator, invite token decorator, CSRF
│   │   └── public.py           # Candidate-facing endpoints (invite token auth)
│   ├── database/
│   │   ├── connection.py       # psycopg2 connection pool (ThreadedConnectionPool)
│   │   └── schema.py           # All table DDL (idempotent CREATE IF NOT EXISTS)
│   ├── services/
│   │   ├── email_service.py    # Email adapter: MockEmailService | SESEmailService
│   │   ├── sms_service.py      # SMS adapter: MockSMSService | TwilioSMSService
│   │   └── storage_service.py  # Storage adapter: LocalStorageService | R2StorageService
│   ├── workers/
│   │   └── video_processor.py  # RQ background job: process_candidate()
│   ├── tests/
│   │   ├── conftest.py         # Fixtures: app, client, DB cleanup, mock RQ/Groq/FFmpeg
│   │   ├── helpers.py          # TestData constants + FlowHelpers for integration tests
│   │   ├── test_auth_endpoints.py
│   │   ├── test_middleware.py
│   │   ├── test_flow_*.py      # End-to-end flow tests
│   │   └── __init__.py
│   ├── smoke_test.py           # Post-deployment HTTP smoke test
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios client + per-resource API modules
│   │   │   ├── client.js       # Axios instance with JWT interceptor + auto-refresh
│   │   │   ├── auth.js, campaigns.js, candidates.js, dashboard.js, public.js
│   │   ├── components/
│   │   │   ├── ui/             # Reusable UI primitives (Button, Card, Badge, etc.)
│   │   │   ├── layout/         # DashboardLayout
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── InterviewLayout.jsx
│   │   ├── pages/
│   │   │   ├── auth/           # Login, Signup, ForgotPassword, ResetPassword
│   │   │   ├── dashboard/      # Dashboard, CampaignCreate, CampaignDetail, CandidateDetail, Settings
│   │   │   └── candidate/      # Welcome, Consent, CameraTest, Recording, Review, Confirmation
│   │   ├── store/              # Zustand stores (authStore)
│   │   ├── lib/
│   │   │   ├── i18n.jsx        # i18n context provider (en/ar)
│   │   │   ├── translations/   # en.json, ar.json
│   │   │   └── useMediaRecorder.js
│   │   ├── App.jsx             # React Router routes
│   │   ├── main.jsx            # Entry point with I18nProvider
│   │   └── index.css           # Tailwind CSS imports
│   ├── package.json
│   └── index.html
├── docker-compose.yml          # Local dev: postgres, redis, backend, worker
├── .github/workflows/
│   └── test-e2e.yml            # CI: pytest on push/PR
├── .env.template               # All environment variables documented
└── .gitignore
```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- FFmpeg (required by AI pipeline for audio extraction)

### Local Development

```bash
# 1. Start infrastructure (Postgres + Redis + Backend + Worker)
docker-compose up -d

# 2. Start frontend dev server
cd frontend && npm install && npm run dev

# 3. Access the app
# Frontend: http://localhost:5173
# Backend API: http://localhost:5000
# Health check: http://localhost:5000/health
```

### Without Docker (backend only)

```bash
# Copy and configure environment
cp .env.template .env
# Edit .env with development values (see DEVELOPMENT ONLY section in template)

# Install Python deps
cd backend
pip install -r requirements.txt

# Initialize database schema
python -m database.schema

# Run the API server
python api/app.py

# Run the RQ worker (separate terminal)
rq worker default --url redis://localhost:6379
```

### Environment Variables

All variables are documented in `.env.template`. Key ones for local dev:

| Variable | Dev Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://corematch:corematch@localhost:5432/corematch` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis for RQ + rate limiting |
| `JWT_SECRET` | `dev_secret_change_in_production` | JWT signing key |
| `STORAGE_PROVIDER` | `local` | `local` or `r2` |
| `EMAIL_PROVIDER` | `mock` | `mock` (prints to console) or `ses` |
| `GROQ_API_KEY` | (empty) | Required for AI scoring; empty = scoring disabled |
| `SMS_ENABLED` | `false` | Enable Twilio SMS |

## Common Commands

### Backend Tests

```bash
# Run all tests (requires running Postgres + Redis)
cd backend && pytest tests/ -v -x --tb=short

# Run a specific test file
pytest tests/test_auth_endpoints.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

**Test requirements:** PostgreSQL (`corematch_test` database) and Redis must be running. Tests use `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/corematch_test` and `REDIS_URL=redis://localhost:6379/1` by default (set in `conftest.py`).

### Frontend

```bash
cd frontend
npm run dev      # Vite dev server (port 5173)
npm run build    # Production build to dist/
npm run preview  # Preview production build
```

### Smoke Test (post-deployment)

```bash
COREMATCH_API_URL=https://your-backend.up.railway.app python backend/smoke_test.py
```

## Architecture & Key Patterns

### Authentication

- **HR users:** JWT access tokens (15-min, stored in sessionStorage) + refresh tokens (7-day, httpOnly cookie). Auto-refresh via Axios interceptor on 401.
- **Candidates:** UUID invite tokens in URL path. No login required. Validated via `@require_invite_token` decorator.
- **CSRF:** Double-submit cookie pattern (`XSRF-TOKEN` cookie + `X-XSRF-Token` header).

### Database

- Raw SQL with `psycopg2` (no ORM). Connection pool via `ThreadedConnectionPool`.
- Context manager pattern: `with get_db() as conn:` — auto-commits on success, rolls back on exception.
- Schema is idempotent — safe to run `create_tables()` multiple times.
- Tables: `users`, `password_reset_tokens`, `campaigns`, `candidates`, `video_answers`, `ai_scores`, `audit_log`.
- All IDs are UUID. Timestamps are `TIMESTAMPTZ` in UTC.

### Service Layer (Pluggable Adapters)

Services use factory pattern with cached singletons:

- **Storage:** `get_storage_service()` returns `LocalStorageService` or `R2StorageService` based on `STORAGE_PROVIDER`.
- **Email:** `get_email_service()` returns `MockEmailService` or `SESEmailService` based on `EMAIL_PROVIDER`.
- **SMS:** `get_sms_service()` returns `MockSMSService` or `TwilioSMSService` based on `SMS_PROVIDER`.

In tests, singletons are reset between tests via `conftest.py:reset_singletons()`.

### AI Pipeline (backend/ai/scorer.py)

1. **Audio extraction:** FFmpeg converts video (webm/mp4) to 16kHz mono WAV
2. **Transcription:** Groq Whisper (`whisper-large-v3`)
3. **Scoring:** Groq LLM (`llama-3.3-70b-versatile`) with structured JSON output
4. **Score weights:** Content 50% + Communication 30% + Behavioral 20%
5. **Tiers:** `strong_proceed` (>=70), `consider` (>=50), `likely_pass` (<50)

Scoring runs in background RQ worker (`workers/video_processor.py`). Falls back to `mixtral-8x7b-32768` if primary model fails.

### Background Jobs

- **Queue:** Redis Queue (RQ) with `default` queue
- **Worker command:** `rq worker default --url redis://redis:6379`
- **Main job:** `process_candidate(candidate_id)` — processes all video answers for a candidate

### Frontend Architecture

- **Routing:** React Router v6 with nested routes
- **State:** Zustand stores (primarily `authStore`)
- **API client:** Axios with request interceptor (JWT) and response interceptor (auto-refresh on 401)
- **Styling:** Tailwind CSS 3
- **i18n:** Custom context provider with English and Arabic (RTL support)
- **Video recording:** Custom `useMediaRecorder` hook using browser MediaRecorder API

### API Route Structure

| Prefix | Blueprint | Auth |
|---|---|---|
| `/api/auth/*` | `auth_bp` | Public (rate-limited) |
| `/api/campaigns/*` | `campaigns_bp` | JWT (`@require_auth`) |
| `/api/candidates/*` | `candidates_bp` | JWT (`@require_auth`) |
| `/api/dashboard/*` | `dashboard_bp` | JWT (`@require_auth`) |
| `/api/public/*` | `public_bp` | Invite token (`@require_invite_token`) |
| `/health` | Direct route | Public |

### Rate Limiting

- Global: 200/minute, 2000/hour per IP
- Auth endpoints are more restrictive (signup: 3/min, login: 5/min)
- Backed by Redis via Flask-Limiter
- Disabled in tests via `RATELIMIT_ENABLED=False`

## Testing Conventions

- Tests are in `backend/tests/` using `pytest`.
- `conftest.py` provides fixtures: `test_app`, `client`, `clean_db` (truncates all tables between tests), `mock_rq_enqueue`, `email_capture`, `mock_groq_client`, `mock_ffmpeg`.
- `helpers.py` provides `TestData` (constants) and `FlowHelpers` (reusable API call sequences).
- Flow tests (`test_flow_*.py`) test complete user journeys (e.g., signup → create campaign → invite → consent → upload → submit).
- All external services (RQ, Groq, FFmpeg, email, SMS) are mocked in tests.

## Security Considerations

- **PDPL compliance:** Audit log for all HR actions. Consent recorded server-side before any video upload. Candidate data erasure endpoint.
- **Password hashing:** bcrypt with cost factor 12.
- **Input validation:** `email-validator` for emails. Password strength requirements (8+ chars, uppercase, digit).
- **Video validation:** MIME type + magic byte verification. UUID-based storage keys (never user-supplied filenames).
- **Security headers:** X-Frame-Options DENY, CSP, HSTS in production, nosniff, XSS protection.
- **Anti-enumeration:** Login and forgot-password return generic errors.
- **PII protection:** Sentry configured with `send_default_pii=False`. Werkzeug logging suppressed in production.

## CI/CD

- **GitHub Actions** (`.github/workflows/test-e2e.yml`): Runs `pytest` on push to `main`/`develop` and PRs to `main`.
- Services: PostgreSQL 15 + Redis 7 in CI.
- Python 3.11, FFmpeg installed.
- Test results uploaded as artifacts.

## Key Conventions

- **No ORM** — all database queries are raw SQL with parameterized queries.
- **Blueprint-based Flask architecture** — each API domain is a separate Blueprint.
- **Factory pattern** for services — all external service adapters use `get_*_service()` with cached singletons.
- **JSONB** for flexible data (questions, scores, audit metadata).
- **Questions snapshot** — candidates receive a frozen copy of questions at invite time; campaign edits don't affect existing invitations.
- **Logging** — standard Python `logging` module; each module has its own named logger.
- **Error handling** — try/except at endpoint level with appropriate HTTP status codes and JSON error responses.
- **Frontend JSX** — all components use `.jsx` extension. No TypeScript in the frontend.

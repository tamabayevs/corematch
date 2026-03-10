# CoreMatch — Project Guide (v3.1)

## IMPORTANT — Start of Every Conversation
At the start of every new conversation, ALWAYS read these files first before doing anything:
1. **This file** (`CLAUDE.md`) — project structure, patterns, and rules
2. **MEMORY.md** — auto-memory with detailed build history, lessons learned, and current state

These files contain critical context that prevents mistakes and repeated work. Read them fully before responding to any task.

## IMPORTANT — End of Every Conversation
Before the session ends or context runs out, ALWAYS update these files:
1. **MEMORY.md** — add new lessons learned, bugs fixed, features built, deployment notes, and any decisions made
2. **CLAUDE.md** — update version, tables, patterns, or features if anything structural changed

Nothing should be lost between sessions. If you built something, fixed something, or learned something — write it down.

## What is this?
AI-powered video interview platform for MENA HR teams. Candidates record async video answers; AI scores them; HR reviews and decides.

**Version:** 3.1 (2026-03-10)
**Status:** Full product (26 features + agentic pipeline) + go-to-market layer + admin panel + AI eval bench. 105 backend tests passing.

## Tech Stack
- **Backend:** Flask 3.0 + PostgreSQL 15 + Redis/RQ + Groq API (Python 3.9)
- **Frontend:** React 18 + Vite + Tailwind CSS + Zustand + React Router 6
- **i18n:** English + Arabic (RTL) with Hijri calendar support — all UI strings in `frontend/src/lib/translations/{en,ar}.json`
- **Design System:** "Data-Confident Professional" — dark navy sidebar, teal (primary) + amber (accent)

## Project Structure
```
backend/
  api/           # Flask blueprints: auth, campaigns, candidates, public, dashboard,
                 # reviews, templates, insights, compliance, scorecards, comments,
                 # team, notifications, branding, assignments, calibration, dsr,
                 # talent_pool, integrations, reports, saudization, notification_templates,
                 # pipeline, demand, admin, eval_bench
  database/      # schema.py (raw SQL), connection.py (pool), migrations.py (incremental)
  ai/            # scorer.py (Groq Whisper + LLM scoring), providers.py, cv_screener.py,
                 # video_agent.py, deep_evaluator.py, shortlist_ranker.py
  workers/       # video_processor.py (RQ background jobs), pipeline_worker.py, eval_bench_worker.py
  services/      # email (SES/Brevo), sms (Twilio), storage (R2/local), scheduling (MENA weekend),
                 # notification_service, mention_service, pipeline_service, stripe_service
  tests/         # pytest suite — 105 tests across 9 test files

frontend/
  src/
    api/         # Axios API clients (client.js, campaigns.js, dashboard.js, demand.js, etc.)
    components/  # ui/ (Button, Card, Badge, Input, Modal, etc.), layout/ (DashboardLayout),
                 # OnboardingChecklist, ProtectedRoute
    pages/       # auth/ (Login, Signup, VerifyEmail), dashboard/ (17 pages incl. DemandPage),
                 # candidate/ (incl. ApplyPage), LandingPage
    store/       # Zustand stores (authStore — JWT access + httpOnly refresh cookies)
    lib/         # i18n.jsx, translations/, formatDate.js, hijriCalendar.js
```

## Key Commands
```bash
# Frontend dev
cd frontend && npm run dev

# Frontend build
cd frontend && npx vite build

# Deploy frontend (NOT git-connected)
cd frontend && npx vercel --prod --yes

# Backend runs on Railway (auto-deploys on push to main)
git push origin main

# Run backend tests (105 tests)
cd backend && python3 -m pytest tests/ -v

# Run network stress test (85 endpoint tests)
bash stress_test.sh
```

## Deployment
- **Frontend:** https://frontend-pearl-eta-17.vercel.app (Vercel, CLI deploy only)
- **Backend:** https://corematch-production.up.railway.app (Railway, auto-deploy)
- **Test account:** olzhas.tamabayev@gmail.com / CoreMatch2026

## Database Tables (31 tables)

**Core:** `users`, `password_reset_tokens`, `campaigns`, `candidates`, `video_answers`, `ai_scores`, `audit_log`

**Phase 1:** `campaign_templates`, `retention_policies`, `reminder_schedules`

**Phase 2-3:** `scorecard_templates`, `candidate_evaluations`, `team_members`, `company_settings`, `candidate_comments`, `notifications`, `data_subject_requests`, `saved_searches`, `review_assignments`, `company_branding`, `notification_templates`, `ats_integrations`, `saudization_quotas`

**v2.0 Pipeline:** `pipeline_configs`, `candidate_documents`, `agent_evaluations`

**v3.0 GTM:** `plan_limits`, `waitlist_signups`, `page_events`

**v3.1 Eval:** `eval_benchmarks`, `eval_runs`, `eval_results`

## Important Patterns
- Python 3.9: Use `Optional[str]` not `str | None` (PEP 604 requires 3.10+)
- All candidate-facing auth uses `invite_token` (UUID), not JWT
- All route handlers with UUID path params must validate UUID format (returns 400 for invalid format)
- Uploading all videos auto-triggers `_submit_for_processing()` → status='submitted'
- After submission, middleware returns 409 for all subsequent requests
- Campaign question edits don't affect existing invitations (questions_snapshot)
- Campaign creation requires minimum 3 questions
- Every state-changing action on candidate data must write to `audit_log` (PDPL)
- RTL: Use `start`/`end` not `left`/`right` in Tailwind classes
- Custom Tailwind colors: `primary-*` (teal), `accent-*` (amber), `navy-*` (dark slate)
- Dates: Use shared `formatDate.js` utility (supports Hijri dual-display in Arabic mode)
- MENA weekends: Invite/remind endpoints include weekend warnings on Fri/Sat (non-blocking)
- Public application flow: `/apply/:campaignId` → self-registration → auto-redirect to interview
- Date inputs: Add `lang` attribute matching current locale to avoid system-locale date format
- Auth: JWT access tokens (15min) + httpOnly refresh cookies (7 days) with auto-rotation
- Landing page at `/` for unauthenticated visitors, auto-redirects to `/dashboard` if logged in
- Email verification: 6-digit code on signup, must verify before dashboard access
- Usage limits: `plan_limits` table checked before campaign create, candidate invite, team invite
- Demand tracking: `POST /api/demand/track` (public, fire-and-forget), `POST /api/demand/waitlist` (public)
- Stripe billing: 3 plans (Free $0, Starter $99/mo, Growth $249/mo) via Checkout + Customer Portal
- Admin panel: Server-rendered HTML at `/admin`, protected by `ADMIN_API_KEY` env var (query param `?key=` or cookie)
- Eval bench API: `/api/eval-bench/*`, protected by `X-Admin-Key` header or `?key=` query param
- Admin panel has 3 pages: Overview (DB stats), Eval Bench (upload videos, run evaluations), Database (browse any table)

## Sidebar Navigation
```
OVERVIEW
  Dashboard         — KPIs, pipeline, action items, activity feed
  Demand            — Waitlist signups, page analytics, LinkedIn outreach funnel
  Campaigns         — List, create, detail, invite, bulk-invite, remind, export

REVIEW
  Video Reviews     — Queue with filters, focused review mode with keyboard shortcuts
  Assignments       — Reviewer assignment, round-robin, progress tracking
  Calibration       — Side-by-side reviewer comparison
  Insights          — Funnel, score distribution, campaign comparison
  Reports           — Executive summary, tier distribution, PDF/CSV export
  Drop-off Analysis — Per-question abandonment charts

MANAGE
  Templates         — Campaign templates, system templates, duplication
  Notification Tmpl — Email/WhatsApp templates with variable substitution
  Scorecards        — Competency-based evaluation templates
  Talent Pool       — Cross-campaign search, saved searches, re-engage
  Team              — Team members, role-based access
  Saudization       — Nationality quota monitoring

SETTINGS
  Settings          — Profile, billing (Stripe)
  Branding          — Company logo, colors, welcome message
  Integrations      — Greenhouse + Lever ATS connectors
  PDPL Compliance   — Audit log, retention policy, data expiry timeline
  Data Requests     — Data subject requests (access/erasure/rectification)
```

## Feature Roadmap — All Phases Complete ✅

### Phase 1 — Complete MVP ✅ (8 features)
1. ✅ Enhanced Dashboard (KPIs, pipeline, action items, activity feed)
2. ✅ Bulk Invite & Campaign Reminders (CSV upload, 500/batch, 48h reminder cooldown)
3. ✅ Video Reviews Queue & Focused Mode (queue + focused review with keyboard shortcuts)
4. ✅ Campaign Templates & Duplication (4 system templates, save/duplicate campaigns)
5. ✅ Basic Insights & Pipeline Analytics (funnel, score distribution, campaign comparison)
6. ✅ PDPL Compliance Dashboard (audit log, retention policy, data expiry timeline)
7. ✅ Campaign Export (CSV with per-question AI scores)
8. ✅ Sidebar Navigation Update (4-section nav: Overview, Review, Manage, Settings)

### Phase 2 — Competitive Differentiation ✅ (10 features)
9. ✅ Scorecards — Templates & Human Evaluation (competency-based, anti-peeking)
10. ✅ Team Accounts & Role-Based Access (Admin/Recruiter/Reviewer/Viewer)
11. ✅ Talent Pool (cross-campaign search, full-text transcript search, re-engage)
12. ✅ WhatsApp Invitations (Business API integration, weekend-aware)
13. ✅ Review Assignments (round-robin, manual, progress tracking)
14. ✅ Candidate Comments & Discussions (threaded, @mentions, notifications)
15. ✅ Candidate Status Portal (public status page, no scores revealed)
16. ✅ Drop-off Analysis & Advanced Insights (per-question abandonment)
17. ✅ Company Branding (logo, colors, welcome message)
18. ✅ Data Subject Request Workflow (access/erasure/rectification, 30-day deadline)

### Phase 3 — Market Leadership ✅ (8 features)
19. ✅ Scorecard Calibration View (side-by-side reviewer comparison)
20. ✅ Custom Notification Templates (email/WhatsApp, variable substitution)
21. ✅ ATS Integrations (Greenhouse + Lever API connectors)
22. ✅ Advanced Analytics + PDF Reports (executive summary, trend charts)
23. ✅ Talent Pool Saved Searches + Auto-notify
24. ✅ Practice Question + Offline Resilience
25. ✅ Hijri Calendar Support (dual Gregorian/Hijri display in Arabic mode)
26. ✅ Saudization/Nitaqat Tracking (nationality quota monitoring)

### Hardening ✅
- ✅ Hijri calendar wired into all 11 date locations across 8 files
- ✅ MENA weekend-awareness on invite/remind/bulk-invite endpoints
- ✅ 105 backend tests (62 Phase 1 + 43 Phase 2-3)
- ✅ UUID validation on all campaign/candidate route handlers
- ✅ 85/85 network stress tests passing (including concurrent + sequential burst)

### v1.1 Gap Fixes ✅
- ✅ Notification service (`services/notification_service.py`) — wired into 7 event points (submission, AI scoring, decision, comment, assignment, DSR, evaluation)
- ✅ Logo upload (`POST /api/branding/logo`) — file upload via storage service, PNG/JPEG/SVG, 2MB max
- ✅ Full-text transcript search — GIN index on `video_answers.transcript`, wired into talent pool search
- ✅ @mentions in comments (`services/mention_service.py`) — parses @patterns, resolves team members, creates notifications
- ✅ PDF export (`GET /api/reports/export/pdf`) — executive report with KPIs, tier distribution, top campaigns via fpdf2
- ✅ Migration 14: FTS index on video_answers transcript

### v1.2 UI Polish & Public Application Flow ✅
- ✅ 61 missing translation keys added to en.json and ar.json (Assignments, Talent Pool, DSR, Video Reviews)
- ✅ Fixed DSRPage column header bug (success message displayed as column header)
- ✅ Fixed "Shortlist Rate: 300%" on Reports page (capped conversion rates, fixed denominator)
- ✅ Fixed "Reviewed: 300%" on Insights funnel (capped step-to-step rates at 100%)
- ✅ Added `lang` attribute to all date inputs to fix Russian locale date format issue
- ✅ Fixed "1 questions" grammar on Template Library (proper singular/plural)
- ✅ Added "Export PDF" button to Reports page (calls existing PDF endpoint)
- ✅ Added logo upload UI to Branding page (file input, preview, delete)
- ✅ Populated Drop-off Analysis page with per-question charts and abandonment data
- ✅ Fixed Review Queue subtitle to show candidate count
- ✅ **Public Application Flow** — new feature:
  - `GET /api/public/campaign-info/:id` — returns campaign details + branding for public landing page
  - `POST /api/public/apply/:id` — candidate self-registration (name, email, phone → creates candidate + invite token)
  - `ApplyPage.jsx` at `/apply/:campaignId` — branded landing page with registration form
  - "Copy Public Link" button on Campaign Detail page — clipboard copy with toast notification
  - Duplicate email detection (409), closed campaign detection (410), full audit trail

### v2.0 Agentic Pipeline ✅
- ✅ 4-stage AI pipeline: CV Screen → Video Interview → Deep Evaluation → Final Shortlist
- ✅ Pipeline opt-in per campaign via `pipeline_enabled` boolean
- ✅ AI Provider abstraction: Groq (default), Anthropic (Claude), OpenAI — configurable per stage
- ✅ CV upload (PDF/DOCX) via multipart/form-data
- ✅ Frontend: PipelinePage (Kanban), AgentEvaluation component, PipelineProgress stepper
- ✅ Prompt templates in `backend/ai/prompts/*.txt`

### v3.0 Go-to-Market ✅
- ✅ **Stripe Billing** — 3 plans (Free $0 / Starter $99 / Growth $249), Checkout sessions, Customer Portal, webhook handler
- ✅ **Auth Persistence** — JWT refresh token rotation (15min access + 7-day httpOnly refresh cookies)
- ✅ **Email Verification** — 6-digit code on signup, resend with cooldown
- ✅ **Usage Limits** — `plan_limits` table, enforced on campaign create / candidate invite / team invite, monthly auto-reset
- ✅ **Onboarding Checklist** — 5-step progress card on dashboard for new users
- ✅ **Landing Page** — Full marketing page at `/` with hero, value props, pricing, waitlist form
- ✅ **SEO Meta Tags** — OpenGraph + Twitter Card
- ✅ **Demand Measurement** — self-hosted analytics (page_events table), waitlist capture with auto-reply email, demand dashboard with KPIs/charts/LinkedIn funnel

### v3.1 Admin Panel & AI Eval Bench ✅
- ✅ **Admin Panel** — Server-rendered HTML at `/admin` (no React, no build step)
  - Overview: DB table counts, quick links
  - Database browser: View any table's rows (50 row limit)
  - Eval Bench UI: Upload videos, trigger runs, view results
  - Auth: `ADMIN_API_KEY` env var, cookie persistence after first login
- ✅ **AI Eval Bench** — Upload benchmark interview videos, run through AI scorer, compare results
  - 3 tables: `eval_benchmarks`, `eval_runs`, `eval_results` (Migration 27)
  - RQ worker processes all benchmarks: video → FFmpeg → Whisper → LLM score
  - Tracks per-benchmark: transcript, scores (content/communication/behavioral/overall), tier, latency
  - Models: `llama-3.3-70b-versatile` (default), `mixtral-8x7b-32768` (fallback) — both free via Groq
  - **Backlog:** Multi-model consensus (run same videos through multiple providers, compare quality)

## Test Summary
- **105/105 backend tests passing**
- **85/85 network stress tests passing**
- **Avg response time:** ~350ms
- **Concurrent (10x):** 100% success rate
- **Zero 500 errors**, zero timeouts

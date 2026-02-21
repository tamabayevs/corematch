# CoreMatch — Project Guide (v1.1)

## What is this?
AI-powered video interview platform for MENA HR teams. Candidates record async video answers; AI scores them; HR reviews and decides.

**Version:** 1.1 (2026-02-21)
**Status:** All 26 features fully wired end-to-end. v1.1 fixes 6 gaps found in v1.0 audit: notification service, logo upload, full-text transcript search, @mentions, PDF export. 105 backend tests passing. 85/85 network stress tests passing.

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
                 # talent_pool, integrations, reports, saudization, notification_templates
  database/      # schema.py (raw SQL), connection.py (pool), migrations.py (incremental)
  ai/            # scorer.py (Groq Whisper + LLM scoring)
  workers/       # video_processor.py (RQ background jobs)
  services/      # email (SES), sms (Twilio), storage (R2/local), scheduling (MENA weekend),
                 # notification_service (in-app notifications), mention_service (@mentions)
  tests/         # pytest suite — 105 tests across 6 test files

frontend/
  src/
    api/         # Axios API clients (client.js, campaigns.js, dashboard.js, templates.js, etc.)
    components/  # ui/ (Button, Card, Badge, Input, Modal, etc.), layout/ (DashboardLayout)
    pages/       # auth/, dashboard/ (15 pages), candidate/
    store/       # Zustand stores (authStore)
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

## Database Tables (22 tables)

**Core:** `users`, `password_reset_tokens`, `campaigns`, `candidates`, `video_answers`, `ai_scores`, `audit_log`

**Phase 1:** `campaign_templates`, `retention_policies`, `reminder_schedules`

**Phase 2-3:** `scorecard_templates`, `candidate_evaluations`, `team_members`, `company_settings`, `candidate_comments`, `notifications`, `data_subject_requests`, `saved_searches`, `review_assignments`, `company_branding`, `notification_templates`, `ats_integrations`, `saudization_quotas`

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

## Sidebar Navigation
```
OVERVIEW
  Dashboard         — KPIs, pipeline, action items, activity feed
  Campaigns         — List, create, detail, invite, bulk-invite, remind, export

REVIEW
  Video Reviews     — Queue with filters, focused review mode with keyboard shortcuts
  Insights          — Funnel, score distribution, campaign comparison, drop-off analysis
  Reports           — Executive summary, tier distribution, PDF/CSV export

MANAGE
  Talent Pool       — Cross-campaign search, saved searches, re-engage
  Assignments       — Reviewer assignment, round-robin, progress tracking
  Saudization       — Nationality quota monitoring

SETTINGS
  Settings          — Profile, team, scorecards, notification templates, integrations
  PDPL Compliance   — Audit log, retention policy, data expiry timeline
  DSR Management    — Data subject requests (access/erasure/rectification)
  Branding          — Company logo, colors, welcome message
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

## Stress Test Summary (v1.1)
- **85/85 tests passing** — auth, dashboard, campaigns, candidates, reviews, assignments, insights, reports, templates, scorecards, compliance, DSR, branding, team, integrations, talent pool, saudization, public endpoints, error handling, concurrent stress, sequential burst
- **Avg response time:** ~350ms
- **Concurrent (10x):** 100% success rate across 8 endpoints
- **Sequential burst (50x):** 50/50 OK, avg 420ms
- **Zero 500 errors**, zero timeouts, zero slow responses

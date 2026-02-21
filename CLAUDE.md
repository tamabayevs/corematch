# CoreMatch — Project Guide

## What is this?
AI-powered video interview platform for MENA HR teams. Candidates record async video answers; AI scores them; HR reviews and decides.

## Tech Stack
- **Backend:** Flask 3.0 + PostgreSQL 15 + Redis/RQ + Groq API (Python 3.9)
- **Frontend:** React 18 + Vite + Tailwind CSS + Zustand + React Router 6
- **i18n:** English + Arabic (RTL) — all UI strings in `frontend/src/lib/translations/{en,ar}.json`
- **Design System:** "Data-Confident Professional" — dark navy sidebar, teal (primary) + amber (accent)

## Project Structure
```
backend/
  api/           # Flask blueprints: auth, campaigns, candidates, public, dashboard, reviews, templates, insights, compliance
  database/      # schema.py (raw SQL), connection.py (pool), migrations.py (incremental changes)
  ai/            # scorer.py (Groq Whisper + LLM scoring)
  workers/       # video_processor.py (RQ background jobs)
  services/      # email (SES), sms (Twilio), storage (R2/local)
  tests/         # pytest suite

frontend/
  src/
    api/         # Axios API clients (client.js, campaigns.js, dashboard.js, templates.js, etc.)
    components/  # ui/ (Button, Card, Badge, Input, Modal, etc.), layout/ (DashboardLayout)
    pages/       # auth/, dashboard/, candidate/
    store/       # Zustand stores (authStore)
    lib/         # i18n.jsx, translations/
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

# Run backend tests
cd backend && python3 -m pytest tests/ -v
```

## Deployment
- **Frontend:** https://frontend-pearl-eta-17.vercel.app (Vercel, CLI deploy only)
- **Backend:** https://corematch-production.up.railway.app (Railway, auto-deploy)
- **Test account:** olzhas.tamabayev@gmail.com / CoreMatch2026

## Database Tables
`users`, `password_reset_tokens`, `campaigns`, `candidates`, `video_answers`, `ai_scores`, `audit_log`, `campaign_templates`

## Important Patterns
- Python 3.9: Use `Optional[str]` not `str | None` (PEP 604 requires 3.10+)
- All candidate-facing auth uses `invite_token` (UUID), not JWT
- Uploading all videos auto-triggers `_submit_for_processing()` → status='submitted'
- After submission, middleware returns 409 for all subsequent requests
- Campaign question edits don't affect existing invitations (questions_snapshot)
- Every state-changing action on candidate data must write to `audit_log` (PDPL)
- RTL: Use `start`/`end` not `left`/`right` in Tailwind classes
- Custom Tailwind colors: `primary-*` (teal), `accent-*` (amber), `navy-*` (dark slate)

## Current Roadmap
Full plan: `.claude/plans/snoopy-jumping-pnueli.md`

### Phase 1 — Complete MVP ✅ (all 8 features done)
1. ✅ Enhanced Dashboard (KPIs, pipeline, action items, activity feed)
2. ✅ Bulk Invite & Campaign Reminders (CSV upload, 500/batch, 48h reminder cooldown)
3. ✅ Video Reviews Queue & Focused Mode (queue + focused review with keyboard shortcuts)
4. ✅ Campaign Templates & Duplication (4 system templates, save/duplicate campaigns)
5. ✅ Basic Insights & Pipeline Analytics (funnel, score distribution, campaign comparison)
6. ✅ PDPL Compliance Dashboard (audit log, retention policy, data expiry timeline)
7. ✅ Campaign Export (CSV with per-question AI scores)
8. ✅ Sidebar Navigation Update (4-section nav: Overview, Review, Manage, Settings)

### Phase 2 — Competitive Differentiation (10 features)
9-18: Scorecards, Team accounts, Talent Pool, WhatsApp, Review assignments, Comments, Candidate portal, Advanced insights, Branding, Data subject requests

### Phase 3 — Market Leadership (8 features)
19-26: Calibration, Custom templates, ATS integrations, PDF reports, Saved searches, Practice questions, Hijri calendar, Saudization tracking

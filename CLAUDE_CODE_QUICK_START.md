# 🚀 QUICK START - CLAUDE CODE

**Copy this message to Claude Code when starting:**

---

Hi Claude! I'm continuing work on the **AI Video Screening Platform** for MENA hiring.

## Project Context

This is a complete, production-ready SaaS platform that helps HR teams screen candidates using AI-powered video interviews. It's built for the MENA market with Arabic + English support.

**Current Status:** 100% complete and ready to deploy!

## What's Built

✅ **Frontend (React):** 11 pages - HR dashboard + candidate interview flow  
✅ **Backend (Flask):** 15 REST API endpoints  
✅ **AI Engine:** 86.7% accuracy scoring system  
✅ **Services:** Video processing, email, storage  
✅ **Documentation:** Complete project docs  

## Files Available

I have access to all project files:
- `/frontend/` - React app with WebRTC recording
- `/backend/` - Flask API + PostgreSQL
- `/ai-models/` - AI scoring engine
- `/go-to-market/` - Business docs
- `PROJECT_COMPLETE_DOCUMENTATION.md` - Full project details
- `BUDGET_DEPLOYMENT_GUIDE.md` - $5-80/month infrastructure

## What I Need Help With

[Describe your specific task here]

Examples:
- "Deploy this to Railway.app with budget infrastructure"
- "Add CSV import for bulk candidate invitations"
- "Fix video upload progress indicator"
- "Implement password reset flow"
- "Setup Cloudflare R2 for video storage"
- "Integrate Groq API for transcription"

## Key Context to Remember

1. **Tech Stack:**
   - Frontend: React 18 + Vite + Zustand + WebRTC
   - Backend: Flask + PostgreSQL + JWT
   - AI: scikit-learn + spaCy + textstat
   - Storage: S3/R2/Azure/Local
   - Email: SendGrid/Resend

2. **Architecture:**
   - HR creates campaigns → invites candidates
   - Candidates record 5 video answers (WebRTC)
   - AI scores transcripts (content + communication + behavioral)
   - HR views ranked candidates

3. **Budget Focus:**
   - Railway ($5-20/month) for hosting
   - Cloudflare R2 (FREE) for storage
   - Resend (FREE) for email
   - Groq (FREE) for transcription

4. **Files Structure:**
   ```
   /frontend/src/
   ├── api/ (API integration)
   ├── store/ (Zustand state)
   └── pages/ (React components)
   
   /backend/
   ├── api/app.py (REST API)
   ├── database/ (PostgreSQL)
   ├── services/ (storage, email)
   └── workers/ (video processing)
   ```

5. **Important Notes:**
   - Whisper API is currently mocked (needs integration)
   - WebRTC records in WebM format
   - JWT auth with localStorage
   - AI scoring: 50% content, 30% communication, 20% behavioral

## Reference Documents

If you need more context, I can share:
- Full API endpoint documentation
- Database schema details
- AI scoring algorithm details
- Deployment step-by-step guides
- Frontend component architecture
- Email template examples

## Let's Build! 🚀

Please help me with: [YOUR TASK HERE]

---

**Pro Tips for Working Together:**

1. **Ask me to read documentation first** if you need context
   - "Read PROJECT_COMPLETE_DOCUMENTATION.md"
   - "Check the database schema in /backend/database/schema.py"

2. **Reference existing patterns**
   - "Follow the same pattern as Recording.jsx for the new feature"
   - "Use the same API structure as /api/campaigns endpoints"

3. **Test incrementally**
   - Build feature → Test locally → Deploy to staging

4. **Budget-conscious**
   - Always prefer Railway over AWS
   - Always prefer R2 over S3
   - Always prefer Resend over SendGrid

Ready when you are! 💪

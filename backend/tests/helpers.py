"""
CoreMatch — Test Helpers
Reusable flow steps and test data constants.
"""
import io
import json


class TestData:
    """Constants for test data."""
    HR_EMAIL = "hr@testcompany.com"
    HR_PASSWORD = "TestPass123"
    HR_NAME = "Test HR User"
    HR_COMPANY = "Test Company"

    CANDIDATE_EMAIL = "candidate@gmail.com"
    CANDIDATE_NAME = "Test Candidate"
    CANDIDATE_PHONE = "+1234567890"

    CAMPAIGN_NAME = "Backend Developer Campaign"
    JOB_TITLE = "Senior Backend Developer"
    JOB_DESCRIPTION = "Building scalable APIs"

    QUESTIONS_3 = [
        {"text": "Tell me about your backend development experience.", "think_time_seconds": 30},
        {"text": "How do you handle database optimization?", "think_time_seconds": 30},
        {"text": "Describe a challenging technical problem you solved.", "think_time_seconds": 30},
    ]

    QUESTIONS_5 = QUESTIONS_3 + [
        {"text": "How do you approach code reviews?", "think_time_seconds": 15},
        {"text": "What's your experience with CI/CD pipelines?", "think_time_seconds": 15},
    ]

    # Minimal valid WebM file (EBML header)
    FAKE_WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 100

    # Minimal valid MP4 file (ftyp box)
    FAKE_MP4 = b"\x00\x00\x00\x18" + b"ftyp" + b"\x00" * 100


class FlowHelpers:
    """Reusable API flow steps for tests."""

    def __init__(self, client):
        self.client = client
        self._access_token = None

    def _auth_headers(self, token=None):
        t = token or self._access_token
        return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

    # ── Auth flows ──

    def signup_user(self, email=None, password=None, full_name=None, company_name=None):
        """Sign up and store access token."""
        res = self.client.post("/api/auth/signup", json={
            "email": email or TestData.HR_EMAIL,
            "password": password or TestData.HR_PASSWORD,
            "full_name": full_name or TestData.HR_NAME,
            "company_name": company_name or TestData.HR_COMPANY,
        })
        if res.status_code == 201:
            self._access_token = res.get_json()["access_token"]
        return res

    def login_user(self, email=None, password=None):
        """Login and store access token."""
        res = self.client.post("/api/auth/login", json={
            "email": email or TestData.HR_EMAIL,
            "password": password or TestData.HR_PASSWORD,
        })
        if res.status_code == 200:
            self._access_token = res.get_json()["access_token"]
        return res

    def get_me(self):
        return self.client.get("/api/auth/me", headers=self._auth_headers())

    def update_me(self, data):
        return self.client.put("/api/auth/me", json=data, headers=self._auth_headers())

    # ── Campaign flows ──

    def create_campaign(self, questions=None, **overrides):
        """Create a campaign with default or custom questions."""
        payload = {
            "name": TestData.CAMPAIGN_NAME,
            "job_title": TestData.JOB_TITLE,
            "job_description": TestData.JOB_DESCRIPTION,
            "questions": questions or TestData.QUESTIONS_3,
            "language": "en",
            "invite_expiry_days": 7,
            "max_recording_seconds": 120,
            "allow_retakes": True,
        }
        payload.update(overrides)
        return self.client.post(
            "/api/campaigns",
            json=payload,
            headers=self._auth_headers(),
        )

    def list_campaigns(self, status=None):
        url = "/api/campaigns"
        if status:
            url += f"?status={status}"
        return self.client.get(url, headers=self._auth_headers())

    def get_campaign(self, campaign_id):
        return self.client.get(
            f"/api/campaigns/{campaign_id}",
            headers=self._auth_headers(),
        )

    # ── Invite flows ──

    def invite_candidate(self, campaign_id, email=None, full_name=None, phone=None):
        return self.client.post(
            f"/api/campaigns/{campaign_id}/invite",
            json={
                "email": email or TestData.CANDIDATE_EMAIL,
                "full_name": full_name or TestData.CANDIDATE_NAME,
                "phone": phone or "",
            },
            headers=self._auth_headers(),
        )

    # ── Public (candidate) flows ──

    def get_invite(self, token):
        return self.client.get(f"/api/public/invite/{token}")

    def record_consent(self, token):
        return self.client.post(f"/api/public/consent/{token}")

    def upload_video(self, token, question_index, video_bytes=None, content_type="video/webm"):
        """Upload a fake video for a question."""
        data = {
            "question_index": str(question_index),
            "duration_seconds": "45.0",
        }
        video_data = video_bytes or TestData.FAKE_WEBM
        return self.client.post(
            f"/api/public/video-upload/{token}",
            data=data,
            content_type="multipart/form-data",
            buffered=True,
            headers={"Content-Type": "multipart/form-data"},
            # Flask test client handles multipart differently
        )

    def upload_video_multipart(self, token, question_index, video_bytes=None, content_type="video/webm"):
        """Upload a fake video using proper multipart form."""
        video_data = video_bytes or TestData.FAKE_WEBM
        data = {
            "video": (io.BytesIO(video_data), f"q{question_index}.webm", content_type),
            "question_index": str(question_index),
            "duration_seconds": "45.0",
        }
        return self.client.post(
            f"/api/public/video-upload/{token}",
            data=data,
            content_type="multipart/form-data",
        )

    def get_status(self, token):
        return self.client.get(f"/api/public/status/{token}")

    def submit_interview(self, token, submit_partial=False):
        return self.client.post(
            f"/api/public/submit/{token}",
            json={"submit_partial": submit_partial},
        )

    # ── Candidate management flows ──

    def list_candidates(self, campaign_id, **params):
        return self.client.get(
            f"/api/candidates/campaign/{campaign_id}",
            query_string=params,
            headers=self._auth_headers(),
        )

    def get_candidate(self, candidate_id):
        return self.client.get(
            f"/api/candidates/{candidate_id}",
            headers=self._auth_headers(),
        )

    def set_decision(self, candidate_id, decision, note=""):
        return self.client.put(
            f"/api/candidates/{candidate_id}/decision",
            json={"decision": decision, "note": note},
            headers=self._auth_headers(),
        )

    def erase_candidate(self, candidate_id):
        return self.client.delete(
            f"/api/candidates/{candidate_id}/erase",
            headers=self._auth_headers(),
        )

    # ── Helper to get invite token from DB ──

    def get_invite_token_from_db(self, candidate_email=None):
        """Retrieve invite token directly from DB."""
        from database.connection import get_db
        email = candidate_email or TestData.CANDIDATE_EMAIL
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT invite_token FROM candidates WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    def get_candidate_id_from_db(self, candidate_email=None):
        """Retrieve candidate ID directly from DB."""
        from database.connection import get_db
        email = candidate_email or TestData.CANDIDATE_EMAIL
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM candidates WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
                return str(row[0]) if row else None

    # ── Phase 2: Scorecards ──

    def create_scorecard_template(self, name="Test Scorecard", competencies=None):
        if competencies is None:
            competencies = [
                {"name": "Communication", "weight": 50},
                {"name": "Technical Skills", "weight": 50},
            ]
        return self.client.post(
            "/api/scorecards/templates",
            json={"name": name, "competencies": competencies},
            headers=self._auth_headers(),
        )

    def list_scorecard_templates(self):
        return self.client.get("/api/scorecards/templates", headers=self._auth_headers())

    def submit_evaluation(self, candidate_id, ratings=None, overall_rating=4):
        if ratings is None:
            ratings = [{"competency": "Communication", "score": 4}]
        return self.client.post(
            f"/api/scorecards/evaluate/{candidate_id}",
            json={"ratings": ratings, "overall_rating": overall_rating},
            headers=self._auth_headers(),
        )

    def get_evaluations(self, candidate_id):
        return self.client.get(
            f"/api/scorecards/evaluate/{candidate_id}",
            headers=self._auth_headers(),
        )

    # ── Phase 2: Comments ──

    def create_comment(self, candidate_id, content="Test comment", parent_id=None):
        payload = {"content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return self.client.post(
            f"/api/comments/{candidate_id}",
            json=payload,
            headers=self._auth_headers(),
        )

    def get_comments(self, candidate_id):
        return self.client.get(
            f"/api/comments/{candidate_id}",
            headers=self._auth_headers(),
        )

    # ── Phase 2: DSR ──

    def create_dsr(self, requester_name="John Doe", requester_email="john@gmail.com",
                   request_type="access", description=""):
        return self.client.post(
            "/api/dsr",
            json={
                "requester_name": requester_name,
                "requester_email": requester_email,
                "request_type": request_type,
                "description": description,
            },
            headers=self._auth_headers(),
        )

    def list_dsr(self, **params):
        return self.client.get("/api/dsr", query_string=params, headers=self._auth_headers())

    def get_dsr_stats(self):
        return self.client.get("/api/dsr/stats", headers=self._auth_headers())

    # ── Phase 2: Notifications ──

    def list_notifications(self):
        return self.client.get("/api/notifications", headers=self._auth_headers())

    def get_unread_count(self):
        return self.client.get("/api/notifications/unread-count", headers=self._auth_headers())

    # ── Phase 3: Notification Templates ──

    def create_notif_template(self, name="Test Template", template_type="email",
                               subject="Test Subject", body="Hello {{candidate_name}}"):
        return self.client.post(
            "/api/notification-templates",
            json={"name": name, "type": template_type, "subject": subject, "body": body},
            headers=self._auth_headers(),
        )

    def list_notif_templates(self):
        return self.client.get("/api/notification-templates", headers=self._auth_headers())

    # ── Phase 3: Reports ──

    def get_executive_summary(self, **params):
        return self.client.get("/api/reports/executive-summary", query_string=params,
                               headers=self._auth_headers())

    def get_tier_distribution(self, **params):
        return self.client.get("/api/reports/tier-distribution", query_string=params,
                               headers=self._auth_headers())

    # ── Phase 3: Saudization ──

    def get_saudization_dashboard(self, **params):
        return self.client.get("/api/saudization/dashboard", query_string=params,
                               headers=self._auth_headers())

    def create_saudization_quota(self, category="General", target_percentage=30, notes=""):
        return self.client.post(
            "/api/saudization/quotas",
            json={"category": category, "target_percentage": target_percentage,
                  "notes": notes},
            headers=self._auth_headers(),
        )

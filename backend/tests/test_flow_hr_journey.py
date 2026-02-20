"""
Flow 1: HR User Journey
Signup → create campaign → list → invite → view candidates → decisions → profile
"""
import pytest
from tests.helpers import FlowHelpers, TestData


class TestHRJourney:

    def test_signup_creates_user(self, client):
        h = FlowHelpers(client)
        res = h.signup_user()
        assert res.status_code == 201
        data = res.get_json()
        assert data["access_token"]
        assert data["user"]["email"] == TestData.HR_EMAIL

    def test_signup_duplicate_email(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.signup_user()
        assert res.status_code == 409

    def test_login_after_signup(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.login_user()
        assert res.status_code == 200
        assert res.get_json()["access_token"]

    def test_create_campaign_3_questions(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_campaign(questions=TestData.QUESTIONS_3)
        assert res.status_code == 201
        campaign = res.get_json()["campaign"]
        assert campaign["name"] == TestData.CAMPAIGN_NAME
        assert len(campaign["questions"]) == 3

    def test_create_campaign_5_questions(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_campaign(questions=TestData.QUESTIONS_5)
        assert res.status_code == 201
        assert len(res.get_json()["campaign"]["questions"]) == 5

    def test_list_campaigns(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_campaign()
        res = h.list_campaigns()
        assert res.status_code == 200
        campaigns = res.get_json()["campaigns"]
        assert len(campaigns) == 1

    def test_list_campaigns_filter_active(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_campaign()
        res = h.list_campaigns(status="active")
        assert res.status_code == 200
        assert len(res.get_json()["campaigns"]) == 1

    def test_get_campaign(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        res = h.get_campaign(campaign_id)
        assert res.status_code == 200
        assert res.get_json()["campaign"]["id"] == campaign_id

    def test_invite_candidate(self, client, email_capture):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        res = h.invite_candidate(campaign_id)
        assert res.status_code == 201
        assert res.get_json()["candidate"]["email"] == TestData.CANDIDATE_EMAIL
        # Email was sent
        assert len(email_capture.sent) == 1
        assert email_capture.sent[0]["type"] == "candidate_invitation"

    def test_invite_two_candidates(self, client, email_capture):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id, email="cand1@gmail.com", full_name="Candidate 1")
        h.invite_candidate(campaign_id, email="cand2@gmail.com", full_name="Candidate 2")
        res = h.list_candidates(campaign_id)
        assert res.status_code == 200
        assert res.get_json()["total"] == 2

    def test_view_candidate_list(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        res = h.list_candidates(campaign_id)
        assert res.status_code == 200
        candidates = res.get_json()["candidates"]
        assert len(candidates) == 1
        assert candidates[0]["full_name"] == TestData.CANDIDATE_NAME

    def test_set_decision_shortlist(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()
        res = h.set_decision(candidate_id, "shortlisted", "Great candidate")
        assert res.status_code == 200
        assert res.get_json()["decision"] == "shortlisted"

    def test_set_decision_reject(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()
        res = h.set_decision(candidate_id, "rejected")
        assert res.status_code == 200
        assert res.get_json()["decision"] == "rejected"

    def test_clear_decision(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_campaign()
        campaign_id = create_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()
        h.set_decision(candidate_id, "shortlisted")
        res = h.set_decision(candidate_id, None)
        assert res.status_code == 200
        assert res.get_json()["decision"] is None

    def test_get_profile(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_me()
        assert res.status_code == 200
        assert res.get_json()["email"] == TestData.HR_EMAIL

    def test_update_profile(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.update_me({"full_name": "Updated Name", "language": "ar"})
        assert res.status_code == 200
        me = h.get_me().get_json()
        assert me["full_name"] == "Updated Name"
        assert me["language"] == "ar"

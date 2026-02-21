"""
Phase 2 — Scorecards, Evaluations & Comments
Tests for scorecard template CRUD, candidate evaluations, and threaded comments.
"""
import pytest
from tests.helpers import FlowHelpers, TestData


class TestScorecardTemplates:
    """Scorecard template CRUD tests."""

    def test_create_scorecard_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_scorecard_template(
            name="Backend Engineer",
            competencies=[
                {"name": "Communication", "weight": 40},
                {"name": "Technical Skills", "weight": 60},
            ],
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["template"]["name"] == "Backend Engineer"
        assert data["template"]["id"]

    def test_create_requires_min_2_competencies(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_scorecard_template(
            name="Incomplete",
            competencies=[{"name": "Only One", "weight": 100}],
        )
        assert res.status_code == 400
        assert "2 competencies" in res.get_json()["error"]

    def test_list_templates(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_scorecard_template(name="Template A")
        h.create_scorecard_template(name="Template B")
        res = h.list_scorecard_templates()
        assert res.status_code == 200
        templates = res.get_json()["templates"]
        names = [t["name"] for t in templates]
        assert "Template A" in names
        assert "Template B" in names

    def test_update_own_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_scorecard_template(name="Original")
        template_id = create_res.get_json()["template"]["id"]

        res = client.put(
            f"/api/scorecards/templates/{template_id}",
            json={"name": "Renamed"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Template updated"

    def test_delete_own_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_scorecard_template(name="To Delete")
        template_id = create_res.get_json()["template"]["id"]

        res = client.delete(
            f"/api/scorecards/templates/{template_id}",
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Template deleted"

        # Verify it's gone from the list
        list_res = h.list_scorecard_templates()
        names = [t["name"] for t in list_res.get_json()["templates"]]
        assert "To Delete" not in names

    def test_create_template_no_name(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_scorecard_template(
            name="",
            competencies=[
                {"name": "A", "weight": 50},
                {"name": "B", "weight": 50},
            ],
        )
        assert res.status_code == 400


class TestCandidateEvaluations:
    """Human evaluation submission tests."""

    def _setup_candidate(self, client):
        """Helper: signup, create campaign, invite, get candidate_id."""
        h = FlowHelpers(client)
        h.signup_user()
        camp_res = h.create_campaign()
        campaign_id = camp_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()
        return h, campaign_id, candidate_id

    def test_submit_evaluation(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        res = h.submit_evaluation(
            candidate_id,
            ratings=[{"competency": "Communication", "score": 4}],
            overall_rating=4,
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["evaluation_id"]

    def test_get_evaluations(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        h.submit_evaluation(
            candidate_id,
            ratings=[{"competency": "Communication", "score": 5}],
            overall_rating=5,
        )
        res = h.get_evaluations(candidate_id)
        assert res.status_code == 200
        evals = res.get_json()["evaluations"]
        assert len(evals) == 1
        assert evals[0]["overall_rating"] == 5

    def test_evaluation_upsert(self, client):
        """Re-submitting for same candidate should update, not duplicate."""
        h, campaign_id, candidate_id = self._setup_candidate(client)
        h.submit_evaluation(candidate_id, overall_rating=3)
        h.submit_evaluation(candidate_id, overall_rating=5)
        res = h.get_evaluations(candidate_id)
        evals = res.get_json()["evaluations"]
        assert len(evals) == 1
        assert evals[0]["overall_rating"] == 5

    def test_evaluation_invalid_rating(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        res = h.submit_evaluation(candidate_id, overall_rating=6)
        assert res.status_code == 400

    def test_evaluation_no_ratings(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        res = client.post(
            f"/api/scorecards/evaluate/{candidate_id}",
            json={"ratings": [], "overall_rating": 4},
            headers=h._auth_headers(),
        )
        assert res.status_code == 400


class TestComments:
    """Candidate comment CRUD and threading tests."""

    def _setup_candidate(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        camp_res = h.create_campaign()
        campaign_id = camp_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()
        return h, campaign_id, candidate_id

    def test_create_comment(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        res = h.create_comment(candidate_id, content="Great candidate!")
        assert res.status_code == 201
        data = res.get_json()
        assert data["comment"]["content"] == "Great candidate!"
        assert data["comment"]["author_name"] == TestData.HR_NAME

    def test_get_comments(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        h.create_comment(candidate_id, content="First comment")
        h.create_comment(candidate_id, content="Second comment")
        res = h.get_comments(candidate_id)
        assert res.status_code == 200
        comments = res.get_json()["comments"]
        assert len(comments) == 2

    def test_create_threaded_reply(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        parent_res = h.create_comment(candidate_id, content="Parent comment")
        parent_id = parent_res.get_json()["comment"]["id"]

        reply_res = h.create_comment(
            candidate_id, content="Reply to parent", parent_id=parent_id,
        )
        assert reply_res.status_code == 201
        assert reply_res.get_json()["comment"]["parent_id"] == parent_id

    def test_edit_own_comment(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        create_res = h.create_comment(candidate_id, content="Original")
        comment_id = create_res.get_json()["comment"]["id"]

        res = client.put(
            f"/api/comments/edit/{comment_id}",
            json={"content": "Edited content"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Comment updated"

    def test_delete_own_comment(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        create_res = h.create_comment(candidate_id, content="To delete")
        comment_id = create_res.get_json()["comment"]["id"]

        res = client.delete(
            f"/api/comments/edit/{comment_id}",
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Comment deleted"

        # Verify it's gone
        list_res = h.get_comments(candidate_id)
        assert len(list_res.get_json()["comments"]) == 0

    def test_empty_comment_rejected(self, client):
        h, campaign_id, candidate_id = self._setup_candidate(client)
        res = h.create_comment(candidate_id, content="")
        assert res.status_code == 400

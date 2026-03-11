"""
Phase 3 — Notification Templates, Reports & Saudization
Tests for customizable templates, executive reporting, and Nitaqat tracking.
"""
import pytest
from tests.helpers import FlowHelpers, TestData


class TestNotificationTemplates:
    """Notification template CRUD and preview tests."""

    def test_list_templates(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.list_notif_templates()
        assert res.status_code == 200
        # Should return at least empty list (or system templates if seeded)
        assert "templates" in res.get_json()

    def test_create_custom_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_notif_template(
            name="Interview Invite",
            template_type="email",
            subject="You're invited to interview at {{company_name}}",
            body="Dear {{candidate_name}}, please join us for an interview.",
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["template"]["name"] == "Interview Invite"

    def test_update_custom_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_notif_template(name="Original Name")
        template_id = create_res.get_json()["template"]["id"]

        res = client.put(
            f"/api/notification-templates/{template_id}",
            json={"name": "Updated Name", "body": "Updated body content"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Template updated"

    def test_delete_custom_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_notif_template(name="To Delete")
        template_id = create_res.get_json()["template"]["id"]

        res = client.delete(
            f"/api/notification-templates/{template_id}",
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Template deleted"

    def test_preview_template(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_notif_template(
            name="Preview Test",
            subject="Welcome {{candidate_name}}",
            body="Hello {{candidate_name}}, your interview for {{job_title}} is ready.",
        )
        template_id = create_res.get_json()["template"]["id"]

        res = client.post(
            f"/api/notification-templates/{template_id}/preview",
            json={"values": {"candidate_name": "Fatima", "job_title": "Engineer"}},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "Fatima" in data["subject_preview"]
        assert "Engineer" in data["body_preview"]

    def test_create_template_missing_body(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_notif_template(name="No Body", body="")
        assert res.status_code == 400

    def test_create_template_invalid_type(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_notif_template(
            name="Bad Type",
            template_type="invalid",
            body="Some content",
        )
        assert res.status_code == 400


class TestReports:
    """Executive summary and tier distribution tests."""

    def test_executive_summary_empty(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_executive_summary()
        assert res.status_code == 200
        data = res.get_json()
        assert "kpis" in data
        assert data["kpis"]["total_candidates"] == 0
        assert "monthly_trends" in data
        assert "top_campaigns" in data

    def test_executive_summary_with_data(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_campaign()
        camp_res = h.list_campaigns()
        campaign_id = camp_res.get_json()["campaigns"][0]["id"]
        h.invite_candidate(campaign_id)
        res = h.get_executive_summary()
        assert res.status_code == 200
        data = res.get_json()
        assert data["kpis"]["total_candidates"] >= 1

    def test_tier_distribution_empty(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_tier_distribution()
        assert res.status_code == 200
        data = res.get_json()
        assert data["distribution"] == []
        assert data["total"] == 0


class TestSaudization:
    """Saudization/Nitaqat dashboard and quota tests."""

    def test_dashboard_empty(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_saudization_dashboard()
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["total_candidates"] == 0
        assert data["nationality_breakdown"] == []

    def test_create_quota(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_saudization_quota(
            category="Engineering",
            target_percentage=30,
            notes="Nitaqat green zone",
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["quota"]["category"] == "Engineering"
        assert data["quota"]["target_percentage"] == 30

    def test_set_candidate_nationality(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        camp_res = h.create_campaign()
        campaign_id = camp_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()

        res = client.put(
            f"/api/saudization/candidate/{candidate_id}/nationality",
            json={"nationality": "Saudi"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["message"] == "Nationality updated"

    def test_dashboard_with_data(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        camp_res = h.create_campaign()
        campaign_id = camp_res.get_json()["campaign"]["id"]
        h.invite_candidate(campaign_id)
        candidate_id = h.get_candidate_id_from_db()

        # Set nationality
        client.put(
            f"/api/saudization/candidate/{candidate_id}/nationality",
            json={"nationality": "Saudi"},
            headers=h._auth_headers(),
        )

        res = h.get_saudization_dashboard()
        assert res.status_code == 200
        data = res.get_json()
        assert data["summary"]["total_candidates"] >= 1
        assert data["summary"]["saudi_count"] >= 1

    def test_create_quota_missing_category(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_saudization_quota(category="", target_percentage=30)
        assert res.status_code == 400

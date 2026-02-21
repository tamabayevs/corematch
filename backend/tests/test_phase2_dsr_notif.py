"""
Phase 2 — Data Subject Requests & Notifications
Tests for PDPL DSR workflow and in-app notification endpoints.
"""
import pytest
from tests.helpers import FlowHelpers, TestData


class TestDSR:
    """Data Subject Request CRUD and stats tests."""

    def test_create_dsr_access(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_dsr(
            requester_name="Ahmed Al-Rashid",
            requester_email="ahmed@gmail.com",
            request_type="access",
            description="Requesting all personal data",
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["request"]["request_type"] == "access"
        assert data["request"]["status"] == "pending"
        assert data["request"]["due_date"]  # auto-set 30 days

    def test_create_dsr_erasure(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_dsr(
            requester_name="Sara Ali",
            requester_email="sara@gmail.com",
            request_type="erasure",
        )
        assert res.status_code == 201
        assert res.get_json()["request"]["request_type"] == "erasure"

    def test_create_dsr_invalid_type(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_dsr(
            requester_name="Test",
            requester_email="test@gmail.com",
            request_type="invalid_type",
        )
        assert res.status_code == 400

    def test_create_dsr_missing_name(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.create_dsr(
            requester_name="",
            requester_email="test@gmail.com",
        )
        assert res.status_code == 400

    def test_list_dsr(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_dsr(requester_name="Person A", requester_email="a@gmail.com")
        h.create_dsr(requester_name="Person B", requester_email="b@gmail.com")
        res = h.list_dsr()
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2
        assert len(data["requests"]) == 2

    def test_update_dsr_status(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        create_res = h.create_dsr()
        dsr_id = create_res.get_json()["request"]["id"]

        # Move to in_progress
        res = client.put(
            f"/api/dsr/{dsr_id}",
            json={"status": "in_progress"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["status"] == "in_progress"

        # Complete it
        res = client.put(
            f"/api/dsr/{dsr_id}",
            json={"status": "completed", "response_notes": "Data provided"},
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["status"] == "completed"

    def test_dsr_stats(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        h.create_dsr(requester_name="A", requester_email="a@gmail.com")
        h.create_dsr(requester_name="B", requester_email="b@gmail.com")
        res = h.get_dsr_stats()
        assert res.status_code == 200
        stats = res.get_json()["stats"]
        assert stats["total"] == 2
        assert stats["pending"] == 2
        assert stats["completed"] == 0

    def test_dsr_stats_empty(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_dsr_stats()
        assert res.status_code == 200
        stats = res.get_json()["stats"]
        assert stats["total"] == 0


class TestNotifications:
    """In-app notification endpoint tests."""

    def test_list_notifications_empty(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.list_notifications()
        assert res.status_code == 200
        data = res.get_json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    def test_unread_count_zero(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = h.get_unread_count()
        assert res.status_code == 200
        assert res.get_json()["unread_count"] == 0

    def test_mark_all_read(self, client):
        h = FlowHelpers(client)
        h.signup_user()
        res = client.put(
            "/api/notifications/read-all",
            headers=h._auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["updated"] == 0

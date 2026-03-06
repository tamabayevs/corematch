"""
CoreMatch — Greenhouse ATS Connector
Integrates with Greenhouse Harvest API v1.
Docs: https://developers.greenhouse.io/harvest.html
"""
import logging
import requests
from requests.auth import HTTPBasicAuth
from services.ats import ATSConnector

logger = logging.getLogger(__name__)

GREENHOUSE_BASE_URL = "https://harvest.greenhouse.io/v1"


class GreenhouseConnector(ATSConnector):

    def test_connection(self, api_key):
        """Validate API key by fetching the authenticated user."""
        try:
            resp = requests.get(
                f"{GREENHOUSE_BASE_URL}/users",
                auth=HTTPBasicAuth(api_key, ""),
                params={"per_page": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "Connected successfully to Greenhouse"
            elif resp.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"Greenhouse returned status {resp.status_code}"
        except requests.Timeout:
            return False, "Connection timed out"
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"

    def export_candidate(self, candidate_data, api_key, settings=None):
        """
        Create a candidate in Greenhouse.
        candidate_data expects: full_name, email, phone, job_title,
                                overall_score, tier, campaign_name
        """
        try:
            # Split name into first/last
            name_parts = (candidate_data.get("full_name") or "").split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            payload = {
                "first_name": first_name,
                "last_name": last_name,
                "email_addresses": [
                    {"value": candidate_data.get("email"), "type": "personal"}
                ],
                "phone_numbers": (
                    [{"value": candidate_data.get("phone"), "type": "mobile"}]
                    if candidate_data.get("phone")
                    else []
                ),
                "tags": [
                    f"CoreMatch: {candidate_data.get('tier', 'unscored')}",
                    f"Score: {candidate_data.get('overall_score', 'N/A')}",
                ],
                "custom_fields": [],
            }

            # If a Greenhouse job_id is provided in settings, attach as application
            job_id = (settings or {}).get("greenhouse_job_id")

            resp = requests.post(
                f"{GREENHOUSE_BASE_URL}/candidates",
                json=payload,
                auth=HTTPBasicAuth(api_key, ""),
                headers={"On-Behalf-Of": (settings or {}).get("on_behalf_of", "")},
                timeout=15,
            )

            if resp.status_code in (200, 201):
                gh_candidate = resp.json()
                external_id = str(gh_candidate.get("id", ""))
                logger.info("Exported candidate to Greenhouse: %s", external_id)
                return True, external_id, "Candidate created in Greenhouse"
            else:
                msg = resp.json().get("message", resp.text[:200])
                return False, None, f"Greenhouse error ({resp.status_code}): {msg}"

        except requests.RequestException as e:
            return False, None, f"Export failed: {str(e)}"

    def import_jobs(self, api_key, settings=None):
        """Fetch open jobs from Greenhouse."""
        try:
            resp = requests.get(
                f"{GREENHOUSE_BASE_URL}/jobs",
                auth=HTTPBasicAuth(api_key, ""),
                params={"status": "open", "per_page": 50},
                timeout=15,
            )
            if resp.status_code == 200:
                jobs = resp.json()
                return [
                    {
                        "external_id": str(j["id"]),
                        "title": j.get("name", ""),
                        "status": j.get("status", ""),
                        "departments": [d["name"] for d in j.get("departments", [])],
                        "offices": [o["name"] for o in j.get("offices", [])],
                    }
                    for j in jobs
                ]
            return []
        except requests.RequestException as e:
            logger.error("Greenhouse import_jobs failed: %s", e)
            return []

    def sync_decision(self, candidate_external_id, decision, api_key, settings=None):
        """Update candidate stage/status in Greenhouse based on CoreMatch decision."""
        try:
            # Map CoreMatch decisions to Greenhouse actions
            if decision == "rejected":
                # Reject the candidate
                resp = requests.post(
                    f"{GREENHOUSE_BASE_URL}/candidates/{candidate_external_id}/reject",
                    json={"rejection_reason": "Did not pass CoreMatch screening"},
                    auth=HTTPBasicAuth(api_key, ""),
                    headers={"On-Behalf-Of": (settings or {}).get("on_behalf_of", "")},
                    timeout=10,
                )
            else:
                # For shortlisted/hold, add a note
                resp = requests.post(
                    f"{GREENHOUSE_BASE_URL}/candidates/{candidate_external_id}/activity_feed/notes",
                    json={"body": f"CoreMatch decision: {decision}", "visibility": "public"},
                    auth=HTTPBasicAuth(api_key, ""),
                    headers={"On-Behalf-Of": (settings or {}).get("on_behalf_of", "")},
                    timeout=10,
                )

            if resp.status_code in (200, 201):
                return True, "Decision synced to Greenhouse"
            return False, f"Greenhouse returned {resp.status_code}"
        except requests.RequestException as e:
            return False, f"Sync failed: {str(e)}"

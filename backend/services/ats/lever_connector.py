"""
CoreMatch — Lever ATS Connector
Integrates with Lever API v1.
Docs: https://hire.lever.co/developer/documentation
"""
import logging
import requests
from requests.auth import HTTPBasicAuth
from services.ats import ATSConnector

logger = logging.getLogger(__name__)

LEVER_BASE_URL = "https://api.lever.co/v1"


class LeverConnector(ATSConnector):

    def test_connection(self, api_key):
        """Validate API key by fetching postings."""
        try:
            resp = requests.get(
                f"{LEVER_BASE_URL}/postings",
                auth=HTTPBasicAuth(api_key, ""),
                params={"limit": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                return True, "Connected successfully to Lever"
            elif resp.status_code == 401:
                return False, "Invalid API key"
            else:
                return False, f"Lever returned status {resp.status_code}"
        except requests.Timeout:
            return False, "Connection timed out"
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"

    def export_candidate(self, candidate_data, api_key, settings=None):
        """
        Create an opportunity (candidate) in Lever.
        candidate_data expects: full_name, email, phone, job_title,
                                overall_score, tier, campaign_name
        """
        try:
            payload = {
                "name": candidate_data.get("full_name", ""),
                "emails": [candidate_data.get("email")],
                "phones": (
                    [{"value": candidate_data.get("phone")}]
                    if candidate_data.get("phone")
                    else []
                ),
                "tags": [
                    f"CoreMatch: {candidate_data.get('tier', 'unscored')}",
                    f"Score: {candidate_data.get('overall_score', 'N/A')}",
                    "source:corematch",
                ],
                "sources": ["CoreMatch"],
            }

            # If a Lever posting_id is provided, attach to that posting
            posting_id = (settings or {}).get("lever_posting_id")
            if posting_id:
                payload["postings"] = [posting_id]

            resp = requests.post(
                f"{LEVER_BASE_URL}/opportunities",
                json=payload,
                auth=HTTPBasicAuth(api_key, ""),
                timeout=15,
            )

            if resp.status_code in (200, 201):
                lever_opp = resp.json().get("data", {})
                external_id = lever_opp.get("id", "")
                logger.info("Exported candidate to Lever: %s", external_id)
                return True, external_id, "Candidate created in Lever"
            else:
                error_msg = resp.text[:200]
                return False, None, f"Lever error ({resp.status_code}): {error_msg}"

        except requests.RequestException as e:
            return False, None, f"Export failed: {str(e)}"

    def import_jobs(self, api_key, settings=None):
        """Fetch open postings from Lever."""
        try:
            resp = requests.get(
                f"{LEVER_BASE_URL}/postings",
                auth=HTTPBasicAuth(api_key, ""),
                params={"state": "published", "limit": 50},
                timeout=15,
            )
            if resp.status_code == 200:
                postings = resp.json().get("data", [])
                return [
                    {
                        "external_id": p.get("id", ""),
                        "title": p.get("text", ""),
                        "status": p.get("state", ""),
                        "departments": [p.get("categories", {}).get("department", "")],
                        "location": p.get("categories", {}).get("location", ""),
                    }
                    for p in postings
                ]
            return []
        except requests.RequestException as e:
            logger.error("Lever import_jobs failed: %s", e)
            return []

    def sync_decision(self, candidate_external_id, decision, api_key, settings=None):
        """Add a note to the Lever opportunity with the CoreMatch decision."""
        try:
            if decision == "rejected":
                # Archive the opportunity with reason
                resp = requests.post(
                    f"{LEVER_BASE_URL}/opportunities/{candidate_external_id}/archived",
                    json={"reason": "44071bc2-2fdb-44cf-aaaa-000000000000"},  # Default "other" reason
                    auth=HTTPBasicAuth(api_key, ""),
                    timeout=10,
                )
            else:
                # Add a note for shortlisted/hold
                resp = requests.post(
                    f"{LEVER_BASE_URL}/opportunities/{candidate_external_id}/notes",
                    json={"value": f"CoreMatch decision: {decision}"},
                    auth=HTTPBasicAuth(api_key, ""),
                    timeout=10,
                )

            if resp.status_code in (200, 201):
                return True, "Decision synced to Lever"
            return False, f"Lever returned {resp.status_code}"
        except requests.RequestException as e:
            return False, f"Sync failed: {str(e)}"

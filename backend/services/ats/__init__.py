"""
CoreMatch — ATS Integration Connectors
Factory pattern for Greenhouse, Lever, and other ATS providers.
"""
import logging

logger = logging.getLogger(__name__)


class ATSConnector:
    """Base class for ATS connectors."""

    def test_connection(self, api_key):
        """Test if the API key is valid. Returns (success, message)."""
        raise NotImplementedError

    def export_candidate(self, candidate_data, api_key, settings=None):
        """Export a candidate to the ATS. Returns (success, external_id, message)."""
        raise NotImplementedError

    def import_jobs(self, api_key, settings=None):
        """Import job listings from the ATS. Returns list of jobs."""
        raise NotImplementedError

    def sync_decision(self, candidate_external_id, decision, api_key, settings=None):
        """Sync a hiring decision to the ATS. Returns (success, message)."""
        raise NotImplementedError


def get_connector(provider):
    """Factory: return the correct ATS connector for the provider."""
    provider = provider.lower()
    if provider == "greenhouse":
        from services.ats.greenhouse_connector import GreenhouseConnector
        return GreenhouseConnector()
    elif provider == "lever":
        from services.ats.lever_connector import LeverConnector
        return LeverConnector()
    else:
        raise ValueError(f"Unsupported ATS provider: {provider}")

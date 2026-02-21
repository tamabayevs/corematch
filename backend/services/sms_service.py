"""
CoreMatch — SMS Service
Pluggable adapter: mock (dev) or Twilio (prod).
Provider selected via SMS_PROVIDER env var: 'mock' | 'twilio'
SMS only sent for candidate invitations when phone number is provided.
"""
import os
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

MAX_SMS_LENGTH = 160


def _build_invitation_sms(company_name: str, job_title: str, short_link: str, language: str = "en") -> str:
    """
    Build SMS message under 160 characters.
    Short link format: https://backend-url/s/TOKEN
    """
    if language == "ar":
        # Arabic SMS (uses Unicode — counts as 70 chars per segment, use short message)
        msg = f"{company_name} تدعوك لمقابلة فيديو: {job_title}\nأكملها هنا: {short_link}\nتنتهي خلال ٧ أيام. -CoreMatch"
    else:
        msg = f"{company_name} invites you for a video interview — {job_title}.\n~15 min: {short_link}\nExpires 7 days. -CoreMatch"

    # Truncate company name if overall message is too long
    if len(msg) > MAX_SMS_LENGTH:
        truncated = company_name[:20] + "..." if len(company_name) > 20 else company_name
        if language == "ar":
            msg = f"{truncated} تدعوك لمقابلة فيديو: {job_title[:30]}\n{short_link}\n-CoreMatch"
        else:
            msg = f"{truncated} video interview — {job_title[:30]}.\n{short_link}\n-CoreMatch"

    return msg[:MAX_SMS_LENGTH]


# ──────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────

class SMSService(ABC):
    def send_candidate_invitation(self, to_phone: str, company_name: str,
                                   job_title: str, short_link: str, language: str = "en") -> None:
        message = _build_invitation_sms(company_name, job_title, short_link, language)
        self._send(to_phone, message)

    @abstractmethod
    def _send(self, to_phone: str, message: str) -> None:
        pass


# ──────────────────────────────────────────────────────────────
# Mock SMS (development)
# ──────────────────────────────────────────────────────────────

class MockSMSService(SMSService):
    def _send(self, to_phone: str, message: str) -> None:
        logger.info("📱 [MOCK SMS] To: %s | Message: %s", to_phone, message)


# ──────────────────────────────────────────────────────────────
# Twilio SMS
# ──────────────────────────────────────────────────────────────

class TwilioSMSService(SMSService):
    def __init__(self):
        from twilio.rest import Client
        self.client = Client(
            os.environ["TWILIO_ACCOUNT_SID"],
            os.environ["TWILIO_AUTH_TOKEN"],
        )
        self.from_number = os.environ["TWILIO_PHONE_NUMBER"]

    def _send(self, to_phone: str, message: str) -> None:
        self.client.messages.create(
            body=message,
            from_=self.from_number,
            to=to_phone,
        )
        logger.info("SMS sent via Twilio to %s", to_phone[:4] + "***")


# ──────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────

_sms_instance = None


def get_sms_service() -> SMSService:
    global _sms_instance
    if _sms_instance is None:
        provider = os.environ.get("SMS_PROVIDER", "mock").lower()
        if provider == "twilio" and os.environ.get("SMS_ENABLED", "false").lower() == "true":
            _sms_instance = TwilioSMSService()
            logger.info("SMS provider: Twilio")
        else:
            _sms_instance = MockSMSService()
            logger.info("SMS provider: mock (dev)")
    return _sms_instance

"""
CoreMatch — Email Service
Pluggable adapter: mock (dev) or AWS SES via SMTP (prod).
Provider selected via EMAIL_PROVIDER env var: 'mock' | 'ses'
"""
import os
import smtplib
import logging
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# HTML Email Templates
# ──────────────────────────────────────────────────────────────

def _render_candidate_invitation(
    to_name: str,
    company_name: str,
    job_title: str,
    interview_url: str,
    expires_at: datetime,
    question_count: int,
    language: str = "en",
) -> tuple[str, str]:
    """Returns (subject, html_body)"""
    expires_str = expires_at.strftime("%B %d, %Y") if expires_at else "7 days from now"

    if language == "ar":
        subject = f"تمت دعوتك لإجراء مقابلة لوظيفة {job_title} في {company_name}"
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'Cairo', Arial, sans-serif; background:#f8fafc; margin:0; padding:20px; direction:rtl; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#2563EB; padding:24px; text-align:center; }}
  .header h1 {{ color:#fff; margin:0; font-size:24px; }}
  .header p {{ color:#bfdbfe; margin:4px 0 0; font-size:14px; }}
  .body {{ padding:32px; }}
  .card {{ background:#f1f5f9; border-radius:8px; padding:16px; margin:20px 0; }}
  .btn {{ display:block; background:#2563EB; color:#fff; text-align:center; padding:14px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin:24px 0; font-size:16px; }}
  .footer {{ background:#f8fafc; padding:20px; text-align:center; font-size:12px; color:#64748b; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>● CoreMatch</h1><p>Screen smarter. Hire better.</p></div>
  <div class="body">
    <p>مرحباً {to_name}،</p>
    <p>دعتك <strong>{company_name}</strong> لإجراء مقابلة فيديو قصيرة للوظيفة التالية:</p>
    <div class="card">
      <p><strong>الوظيفة:</strong> {job_title}</p>
      <p><strong>الشركة:</strong> {company_name}</p>
      <p><strong>التنسيق:</strong> {question_count} أسئلة فيديو (~١٥ دقيقة)</p>
      <p><strong>ينتهي في:</strong> {expires_str}</p>
    </div>
    <a href="{interview_url}" class="btn">ابدأ مقابلتك الآن</a>
    <p>نتمنى لك التوفيق!</p>
  </div>
  <div class="footer">
    <p>CoreMatch — www.corematch.ai | support@corematch.ai</p>
    <p>© {datetime.utcnow().year} CoreMatch. جميع الحقوق محفوظة.</p>
  </div>
</div>
</body></html>"""
    else:
        subject = f"You've been invited to interview for {job_title} at {company_name}"
        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background:#f8fafc; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#2563EB; padding:24px; text-align:center; }}
  .header h1 {{ color:#fff; margin:0; font-size:24px; }}
  .header p {{ color:#bfdbfe; margin:4px 0 0; font-size:14px; }}
  .body {{ padding:32px; }}
  .card {{ background:#f1f5f9; border-radius:8px; padding:16px; margin:20px 0; }}
  .card p {{ margin:6px 0; }}
  .btn {{ display:block; background:#2563EB; color:#fff !important; text-align:center; padding:14px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin:24px 0; font-size:16px; }}
  .steps {{ margin:20px 0; }}
  .steps li {{ margin:8px 0; }}
  .footer {{ background:#f8fafc; padding:20px; text-align:center; font-size:12px; color:#64748b; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>● CoreMatch</h1><p>Screen smarter. Hire better.</p></div>
  <div class="body">
    <p>Hi {to_name},</p>
    <p><strong>{company_name}</strong> has invited you to complete a short video interview:</p>
    <div class="card">
      <p><strong>Position:</strong> {job_title}</p>
      <p><strong>Company:</strong> {company_name}</p>
      <p><strong>Format:</strong> {question_count} video questions (~15 minutes)</p>
      <p><strong>Expires:</strong> {expires_str}</p>
    </div>
    <a href="{interview_url}" class="btn">START YOUR INTERVIEW</a>
    <p><strong>What to expect:</strong></p>
    <ol class="steps">
      <li>Answer {question_count} short video questions</li>
      <li>You have think time before each recording</li>
      <li>You can re-record each answer once</li>
      <li>The whole process takes about 15 minutes</li>
    </ol>
    <p style="color:#64748b; font-size:13px;">This link expires on {expires_str}. If you cannot complete it in time, contact the employer directly.</p>
  </div>
  <div class="footer">
    <p>CoreMatch — www.corematch.ai | support@corematch.ai</p>
    <p>© {datetime.utcnow().year} CoreMatch. All rights reserved.</p>
    <p>This email was sent on behalf of {company_name}.</p>
  </div>
</div>
</body></html>"""

    return subject, html


def _render_candidate_confirmation(
    to_name: str,
    company_name: str,
    job_title: str,
    reference_id: str,
    submitted_at: datetime,
) -> tuple[str, str]:
    submitted_str = submitted_at.strftime("%B %d, %Y at %I:%M %p") if submitted_at else "just now"
    subject = f"Your interview has been submitted — {job_title} at {company_name}"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background:#f8fafc; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#16A34A; padding:24px; text-align:center; }}
  .header h1 {{ color:#fff; margin:0; font-size:22px; }}
  .body {{ padding:32px; }}
  .card {{ background:#f1f5f9; border-radius:8px; padding:16px; margin:20px 0; }}
  .ref {{ background:#1e293b; color:#94a3b8; font-family:monospace; font-size:18px; text-align:center; padding:12px; border-radius:6px; margin:16px 0; }}
  .footer {{ background:#f8fafc; padding:20px; text-align:center; font-size:12px; color:#64748b; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>✓ You're all done, {to_name}!</h1></div>
  <div class="body">
    <p>Your video interview responses have been submitted to <strong>{company_name}</strong>.</p>
    <div class="card">
      <p><strong>Position:</strong> {job_title}</p>
      <p><strong>Company:</strong> {company_name}</p>
      <p><strong>Submitted:</strong> {submitted_str}</p>
    </div>
    <p><strong>Your reference ID:</strong></p>
    <div class="ref" dir="ltr">{reference_id}</div>
    <p><strong>What happens next:</strong></p>
    <ol>
      <li>The hiring team will review your responses</li>
      <li>CoreMatch AI assists with initial scoring — humans make all final decisions</li>
      <li>{company_name} will contact you directly if they wish to move forward</li>
    </ol>
    <p>Good luck! 🌟</p>
  </div>
  <div class="footer">
    <p>Questions? Email support@corematch.ai with your reference ID.</p>
    <p>© {datetime.utcnow().year} CoreMatch. CoreMatch does not make hiring decisions.</p>
  </div>
</div>
</body></html>"""
    return subject, html


def _render_hr_notification(
    hr_name: str,
    candidate_name: str,
    job_title: str,
    campaign_name: str,
    overall_score: float,
    tier: str,
    strengths: list,
    dashboard_url: str,
) -> tuple[str, str]:
    tier_colors = {
        "strong_proceed": "#16A34A",
        "consider": "#D97706",
        "likely_pass": "#DC2626",
    }
    tier_labels = {
        "strong_proceed": "STRONG PROCEED",
        "consider": "CONSIDER",
        "likely_pass": "LIKELY PASS",
    }
    color = tier_colors.get(tier, "#64748b")
    label = tier_labels.get(tier, tier.upper().replace("_", " "))
    score_str = f"{overall_score:.0f}/100" if overall_score is not None else "Pending"
    strengths_html = "".join(f"<li>✓ {s}</li>" for s in (strengths or [])[:3])
    subject = f"{candidate_name} completed their interview — {job_title} | CoreMatch"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background:#f8fafc; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#1e293b; padding:20px 24px; }}
  .header h1 {{ color:#fff; margin:0; font-size:18px; }}
  .body {{ padding:24px; }}
  .score-card {{ border:1px solid #e2e8f0; border-radius:8px; padding:20px; margin:16px 0; }}
  .score {{ font-size:36px; font-weight:bold; color:#1e293b; }}
  .badge {{ display:inline-block; background:{color}; color:#fff; padding:4px 12px; border-radius:4px; font-weight:bold; font-size:13px; margin:8px 0; }}
  .btn {{ display:block; background:#2563EB; color:#fff !important; text-align:center; padding:14px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin:20px 0; }}
  .footer {{ background:#f8fafc; padding:16px; text-align:center; font-size:12px; color:#64748b; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>● CoreMatch — New Candidate Alert</h1></div>
  <div class="body">
    <p>Hi {hr_name},</p>
    <p><strong>{candidate_name}</strong> has completed their video interview.</p>
    <div class="score-card">
      <p style="margin:0;color:#64748b;font-size:13px;">{campaign_name} — {job_title}</p>
      <div class="score">{score_str}</div>
      <div class="badge">{label}</div>
      {f'<ul style="margin:12px 0">{strengths_html}</ul>' if strengths_html else ''}
    </div>
    <a href="{dashboard_url}" class="btn">REVIEW CANDIDATE IN DASHBOARD</a>
    <p style="font-size:12px;color:#64748b;">Note: AI scores are decision-support tools only. Final hiring decisions rest with your team.</p>
  </div>
  <div class="footer">
    <p>© {datetime.utcnow().year} CoreMatch. All rights reserved.</p>
  </div>
</div>
</body></html>"""
    return subject, html


def _render_password_reset(
    to_name: str,
    reset_url: str,
    expires_in_hours: int,
    request_ip: str,
) -> tuple[str, str]:
    subject = "Reset your CoreMatch password"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background:#f8fafc; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background:#2563EB; padding:24px; text-align:center; }}
  .header h1 {{ color:#fff; margin:0; font-size:22px; }}
  .body {{ padding:32px; }}
  .btn {{ display:block; background:#2563EB; color:#fff !important; text-align:center; padding:14px 24px; border-radius:8px; text-decoration:none; font-weight:bold; margin:24px 0; }}
  .warning {{ background:#fef3c7; border:1px solid #D97706; border-radius:8px; padding:16px; margin:16px 0; }}
  .url {{ background:#f1f5f9; font-family:monospace; font-size:12px; padding:12px; border-radius:6px; word-break:break-all; }}
  .footer {{ background:#f8fafc; padding:16px; text-align:center; font-size:12px; color:#64748b; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>● CoreMatch</h1></div>
  <div class="body">
    <p>Hi {to_name},</p>
    <p>We received a request to reset your CoreMatch password.</p>
    <a href="{reset_url}" class="btn">RESET MY PASSWORD</a>
    <p>⚠ This link expires in <strong>{expires_in_hours} hour{'s' if expires_in_hours != 1 else ''}</strong>.</p>
    <div class="warning">
      <p><strong>🔒 Security notice:</strong> CoreMatch will NEVER ask for your password via email, phone, or chat.</p>
      <p>If you did not request this reset, please ignore this email — your account is safe.</p>
      <p>Concerns? Contact <a href="mailto:security@corematch.ai">security@corematch.ai</a></p>
    </div>
    <p style="font-size:12px;color:#64748b;">Can't click the button? Copy this link:</p>
    <div class="url" dir="ltr">{reset_url}</div>
  </div>
  <div class="footer">
    <p>Requested from IP: {request_ip}</p>
    <p>© {datetime.utcnow().year} CoreMatch. All rights reserved.</p>
  </div>
</div>
</body></html>"""
    return subject, html


# ──────────────────────────────────────────────────────────────
# Notification Template Resolution
# ──────────────────────────────────────────────────────────────

def _resolve_template(user_id, template_type, variables):
    """
    Look up a user-customized notification template from the DB.
    Falls back to system template, then returns None (use hardcoded).
    template_type: e.g. "Interview Invitation", "Interview Reminder", etc.
    variables: dict of {{key}} → value substitutions.
    Returns (subject, html_body) or None if no template found.
    """
    if not user_id:
        return None
    try:
        from database.connection import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                # Try user's custom template first, then system template
                cur.execute(
                    """
                    SELECT subject, body FROM notification_templates
                    WHERE (user_id = %s OR is_system = TRUE)
                      AND LOWER(name) = LOWER(%s)
                    ORDER BY is_system ASC
                    LIMIT 1
                    """,
                    (user_id, template_type),
                )
                row = cur.fetchone()
        if not row:
            return None
        subject = row[0] or ""
        body = row[1] or ""
        # Perform {{variable}} substitution
        for key, val in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, str(val) if val else "")
            body = body.replace(placeholder, str(val) if val else "")
        # Wrap body in basic HTML if it doesn't look like HTML
        if "<html" not in body.lower():
            body = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body {{ font-family: -apple-system, Arial, sans-serif; background:#f8fafc; padding:20px; }}
.container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; padding:32px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}</style></head>
<body><div class="container">{body}</div></body></html>"""
        return subject, body
    except Exception as e:
        logger.debug("Template resolution failed (falling back to hardcoded): %s", e)
        return None


# ──────────────────────────────────────────────────────────────
# Abstract base
# ──────────────────────────────────────────────────────────────

class EmailService(ABC):
    def send_candidate_invitation(self, to_email, to_name, company_name, job_title,
                                   interview_url, expires_at, question_count, language="en",
                                   user_id=None):
        # Try user-customized or system template first
        variables = {
            "candidate_name": to_name,
            "job_title": job_title,
            "company_name": company_name,
            "interview_link": interview_url,
            "expiry_date": expires_at.strftime("%B %d, %Y") if expires_at else "7 days",
            "sender_name": company_name,
            "question_count": str(question_count),
        }
        resolved = _resolve_template(user_id, "Interview Invitation", variables)
        if resolved:
            subject, html = resolved
        else:
            subject, html = _render_candidate_invitation(
                to_name, company_name, job_title, interview_url, expires_at, question_count, language
            )
        self._send(to_email, subject, html)

    def send_candidate_confirmation(self, to_email, to_name, company_name, job_title,
                                     reference_id, submitted_at, user_id=None):
        variables = {
            "candidate_name": to_name,
            "job_title": job_title,
            "company_name": company_name,
            "reference_id": reference_id,
            "submitted_at": submitted_at.strftime("%B %d, %Y") if submitted_at else "just now",
        }
        resolved = _resolve_template(user_id, "Interview Confirmation", variables)
        if resolved:
            subject, html = resolved
        else:
            subject, html = _render_candidate_confirmation(
                to_name, company_name, job_title, reference_id, submitted_at
            )
        self._send(to_email, subject, html)

    def send_hr_notification(self, to_email, hr_name, candidate_name, job_title,
                              campaign_name, overall_score, tier, strengths, dashboard_url,
                              user_id=None):
        variables = {
            "candidate_name": candidate_name,
            "job_title": job_title,
            "campaign_name": campaign_name,
            "overall_score": f"{overall_score:.0f}" if overall_score else "N/A",
            "tier": tier,
            "dashboard_url": dashboard_url,
            "hr_name": hr_name,
        }
        resolved = _resolve_template(user_id, "HR Notification", variables)
        if resolved:
            subject, html = resolved
        else:
            subject, html = _render_hr_notification(
                hr_name, candidate_name, job_title, campaign_name,
                overall_score, tier, strengths, dashboard_url
            )
        self._send(to_email, subject, html)

    def send_password_reset(self, to_email, to_name, reset_url, expires_in_hours=1, request_ip="unknown"):
        subject, html = _render_password_reset(to_name, reset_url, expires_in_hours, request_ip)
        self._send(to_email, subject, html)

    @abstractmethod
    def _send(self, to_email: str, subject: str, html_body: str) -> None:
        pass


# ──────────────────────────────────────────────────────────────
# Mock Email (development)
# ──────────────────────────────────────────────────────────────

class MockEmailService(EmailService):
    def _send(self, to_email: str, subject: str, html_body: str) -> None:
        logger.info("📧 [MOCK EMAIL] To: %s | Subject: %s", to_email, subject)
        # Optionally save to /tmp for inspection
        try:
            import tempfile, hashlib, time
            fname = f"/tmp/corematch_email_{int(time.time())}.html"
            with open(fname, "w") as f:
                f.write(f"<!-- To: {to_email} | Subject: {subject} -->\n{html_body}")
            logger.debug("Mock email saved to %s", fname)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
# AWS SES via SMTP
# ──────────────────────────────────────────────────────────────

class SESEmailService(EmailService):
    def __init__(self):
        self.host = os.environ["AWS_SES_SMTP_HOST"]
        self.port = int(os.environ.get("AWS_SES_SMTP_PORT", 587))
        self.username = os.environ["AWS_SES_SMTP_USERNAME"]
        self.password = os.environ["AWS_SES_SMTP_PASSWORD"]
        self.from_address = os.environ.get("EMAIL_FROM_ADDRESS", "noreply@corematch.ai")
        self.from_name = os.environ.get("EMAIL_FROM_NAME", "CoreMatch")

    def _send(self, to_email: str, subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_address}>"
        msg["To"] = to_email

        # Plain text fallback
        plain_text = f"Please view this email in an HTML-capable email client.\n\nSubject: {subject}"
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_address, [to_email], msg.as_string())

        logger.info("Email sent via SES to %s | %s", to_email[:3] + "***", subject)


# ──────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────

_email_instance = None


def get_email_service() -> EmailService:
    global _email_instance
    if _email_instance is None:
        provider = os.environ.get("EMAIL_PROVIDER", "mock").lower()
        if provider == "ses":
            _email_instance = SESEmailService()
            logger.info("Email provider: AWS SES")
        else:
            _email_instance = MockEmailService()
            logger.info("Email provider: mock (dev)")
    return _email_instance

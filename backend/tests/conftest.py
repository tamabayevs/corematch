"""
CoreMatch — Test Fixtures
All test infrastructure: app, client, DB cleanup, mocks.
"""
import os
import json
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Set test environment BEFORE any app imports
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/corematch_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-do-not-use-in-production")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("NODE_ENV", "development")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("GROQ_API_KEY", "")


@pytest.fixture(scope="session")
def test_app():
    """Create Flask app once for the entire test session."""
    # Set a temp dir for uploads
    upload_dir = tempfile.mkdtemp(prefix="corematch_test_uploads_")
    os.environ["LOCAL_UPLOAD_DIR"] = upload_dir

    from api.app import create_app
    from database.schema import create_tables

    app = create_app()
    app.config["TESTING"] = True

    # Create schema
    with app.app_context():
        create_tables()

    yield app

    # Cleanup
    shutil.rmtree(upload_dir, ignore_errors=True)


@pytest.fixture
def client(test_app):
    """Flask test client per test."""
    return test_app.test_client()


@pytest.fixture(autouse=True)
def clean_db(test_app):
    """Truncate all tables between tests for isolation."""
    from database.connection import get_db

    with test_app.app_context():
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    TRUNCATE TABLE audit_log, ai_scores, video_answers,
                    candidates, campaigns, password_reset_tokens, users
                    CASCADE
                """)
    yield


@pytest.fixture(autouse=True)
def clean_storage():
    """Clean upload directory between tests."""
    upload_dir = os.environ.get("LOCAL_UPLOAD_DIR", "/tmp/corematch_test_uploads")
    if os.path.exists(upload_dir):
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                os.remove(item_path)
    yield


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset service singletons between tests."""
    import services.storage_service as storage_mod
    import services.email_service as email_mod
    import services.sms_service as sms_mod

    storage_mod._storage_instance = None
    email_mod._email_instance = None
    sms_mod._sms_instance = None
    yield
    storage_mod._storage_instance = None
    email_mod._email_instance = None
    sms_mod._sms_instance = None


@pytest.fixture(autouse=True)
def mock_rq_enqueue():
    """Prevent real RQ job enqueue in tests."""
    with patch("redis.from_url") as mock_redis:
        mock_conn = MagicMock()
        mock_redis.return_value = mock_conn

        mock_queue = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_queue.enqueue.return_value = mock_job

        with patch("rq.Queue", return_value=mock_queue):
            yield mock_queue


@pytest.fixture
def email_capture():
    """Capture sent emails for assertions."""

    class CapturingEmailService:
        def __init__(self):
            self.sent = []

        def send_candidate_invitation(self, **kwargs):
            self.sent.append({"type": "candidate_invitation", **kwargs})

        def send_candidate_confirmation(self, **kwargs):
            self.sent.append({"type": "candidate_confirmation", **kwargs})

        def send_hr_notification(self, **kwargs):
            self.sent.append({"type": "hr_notification", **kwargs})

        def send_password_reset(self, **kwargs):
            self.sent.append({"type": "password_reset", **kwargs})

    capture = CapturingEmailService()

    import services.email_service as email_mod
    email_mod._email_instance = capture
    yield capture
    email_mod._email_instance = None


@pytest.fixture
def mock_groq_client():
    """Mock Groq API client for AI scoring tests."""

    class MockTranscriptionResponse:
        text = "This is a test transcript about my experience."
        language = "en"

    class MockGroqTranscription:
        def create(self, **kwargs):
            return MockTranscriptionResponse()

    class MockGroqChatCompletion:
        def create(self, **kwargs):
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = json.dumps({
                "content_score": 75,
                "communication_score": 80,
                "behavioral_score": 70,
                "strengths": ["Clear communication", "Relevant experience"],
                "improvements": ["Could provide more examples"],
                "language_match": True,
            })
            return response

    class MockGroqClient:
        def __init__(self):
            self.audio = MagicMock()
            self.audio.transcriptions = MockGroqTranscription()
            self.chat = MagicMock()
            self.chat.completions = MockGroqChatCompletion()

    mock_client = MockGroqClient()

    with patch("groq.Groq", return_value=mock_client), \
         patch.dict(os.environ, {"GROQ_API_KEY": "test-mock-key"}):
        yield mock_client


@pytest.fixture
def mock_ffmpeg():
    """Mock FFmpeg subprocess for audio extraction."""
    # Minimal WAV header (44 bytes) + 1 second of silence at 16kHz mono
    wav_header = (
        b"RIFF"
        + (32044).to_bytes(4, "little")  # File size - 8
        + b"WAVE"
        + b"fmt "
        + (16).to_bytes(4, "little")  # Chunk size
        + (1).to_bytes(2, "little")   # PCM format
        + (1).to_bytes(2, "little")   # Mono
        + (16000).to_bytes(4, "little")  # Sample rate
        + (32000).to_bytes(4, "little")  # Byte rate
        + (2).to_bytes(2, "little")   # Block align
        + (16).to_bytes(2, "little")  # Bits per sample
        + b"data"
        + (32000).to_bytes(4, "little")  # Data size
    )
    fake_wav = wav_header + b"\x00" * 32000

    def mock_run(*args, **kwargs):
        # The ffmpeg command passes the output file as the last argument
        cmd_args = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd_args, (list, tuple)) and len(cmd_args) > 0:
            # Last arg is the output file path
            output_path = cmd_args[-1]
            if output_path.endswith(".wav"):
                with open(output_path, "wb") as f:
                    f.write(fake_wav)

        result = MagicMock()
        result.returncode = 0
        result.stdout = fake_wav
        result.stderr = b""
        return result

    with patch("subprocess.run", side_effect=mock_run):
        yield fake_wav

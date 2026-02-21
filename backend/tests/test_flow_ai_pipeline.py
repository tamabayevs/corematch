"""
Flow 3: AI Pipeline
transcribe → score → full pipeline → overall computation → tier assignment
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from tests.helpers import FlowHelpers, TestData


class TestAIPipeline:

    def test_transcribe_audio(self, client, mock_groq_client, mock_ffmpeg):
        """Groq Whisper transcription returns text + language."""
        from ai.scorer import transcribe_audio

        transcript, lang = transcribe_audio(mock_ffmpeg, "en")
        assert isinstance(transcript, str)
        assert len(transcript) > 0
        assert lang is not None

    def test_score_answer_valid(self, client, mock_groq_client):
        """score_answer with a real transcript returns valid ScoreResult."""
        from ai.scorer import score_answer

        result = score_answer(
            question="Tell me about your experience.",
            transcript="I have 5 years of experience building scalable APIs.",
            job_title="Backend Developer",
            job_description="Building scalable APIs",
            duration_seconds=45.0,
            detected_language="en",
            expected_language="en",
        )
        assert 0 <= result.content_score <= 100
        assert 0 <= result.communication_score <= 100
        assert 0 <= result.behavioral_score <= 100
        assert 0 <= result.overall_score <= 100
        assert result.tier in ("strong_proceed", "consider", "likely_pass")
        assert isinstance(result.strengths, list)
        assert isinstance(result.improvements, list)

    def test_score_answer_empty_transcript(self, client, mock_groq_client):
        """Empty/very short transcript returns fallback low score."""
        from ai.scorer import score_answer

        result = score_answer(
            question="Tell me about yourself.",
            transcript="",
            job_title="Developer",
            job_description="",
            duration_seconds=5.0,
            detected_language="en",
            expected_language="en",
        )
        assert result.overall_score < 10
        assert result.tier == "likely_pass"
        assert result.scoring_source == "fallback"

    def test_score_answer_invalid_json_fallback(self, client):
        """When LLM returns invalid JSON, falls back to second model."""
        import os
        from ai.scorer import score_answer

        call_count = 0

        class MockBadThenGoodCompletion:
            def create(self, **kwargs):
                nonlocal call_count
                call_count += 1
                response = MagicMock()
                response.choices = [MagicMock()]
                if call_count == 1:
                    response.choices[0].message.content = "NOT VALID JSON {{"
                else:
                    response.choices[0].message.content = json.dumps({
                        "content_score": 60,
                        "communication_score": 65,
                        "behavioral_score": 55,
                        "strengths": ["Adequate"],
                        "improvements": ["More detail needed"],
                        "language_match": True,
                    })
                return response

        mock_client = MagicMock()
        mock_client.chat.completions = MockBadThenGoodCompletion()

        with patch("groq.Groq", return_value=mock_client), \
             patch.dict(os.environ, {"GROQ_API_KEY": "test-mock-key"}):
            result = score_answer(
                question="Experience?",
                transcript="I have worked on many projects over the years.",
                job_title="Dev",
                job_description="",
                duration_seconds=30.0,
                detected_language="en",
                expected_language="en",
            )
        assert result.content_score == 60
        assert call_count == 2  # First call failed, second succeeded

    def test_score_video_full_pipeline(self, client, mock_groq_client, mock_ffmpeg):
        """Full pipeline: video bytes → audio → transcript → score."""
        from ai.scorer import score_video

        result = score_video(
            video_bytes=TestData.FAKE_WEBM,
            question="Tell me about your backend experience.",
            job_title="Senior Backend Developer",
            job_description="Building scalable APIs",
            expected_language="en",
        )
        assert result.transcript is not None
        assert result.overall_score > 0
        assert result.tier in ("strong_proceed", "consider", "likely_pass")
        assert result.model_used != ""

    def test_overall_score_computation(self, client, mock_groq_client):
        """Verify weighted score: content*0.5 + comm*0.3 + behavioral*0.2."""
        from ai.scorer import score_answer

        result = score_answer(
            question="Experience?",
            transcript="I have extensive experience in backend development.",
            job_title="Dev",
            job_description="",
            duration_seconds=30.0,
            detected_language="en",
            expected_language="en",
        )
        # Mock returns content=75, communication=80, behavioral=70
        expected = 75 * 0.5 + 80 * 0.3 + 70 * 0.2
        assert abs(result.overall_score - expected) < 0.1

    def test_tier_assignment(self, client, mock_groq_client):
        """Verify tier thresholds: >=70 strong_proceed, >=50 consider, else likely_pass."""
        from ai.scorer import score_answer

        # Mock returns overall ~75.5 which is >=70 → strong_proceed
        result = score_answer(
            question="Experience?",
            transcript="I have strong experience in many technical areas.",
            job_title="Dev",
            job_description="",
            duration_seconds=30.0,
            detected_language="en",
            expected_language="en",
        )
        assert result.tier == "strong_proceed"

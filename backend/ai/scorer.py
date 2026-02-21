"""
CoreMatch — AI Scoring Engine
Uses Groq API for:
  1. Audio transcription (whisper-large-v3)
  2. Interview scoring (llama-3.3-70b-versatile)

Input: video file bytes or path
Output: ScoreResult dataclass with all scores and analysis
"""
import os
import io
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Scoring weights (must sum to 1.0)
CONTENT_WEIGHT = 0.50
COMMUNICATION_WEIGHT = 0.30
BEHAVIORAL_WEIGHT = 0.20

# Tier thresholds
TIER_STRONG_PROCEED = 70
TIER_CONSIDER = 50

# Groq model names
MODEL_TRANSCRIPTION = os.environ.get("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3")
MODEL_SCORING = os.environ.get("GROQ_SCORING_MODEL", "llama-3.3-70b-versatile")
MODEL_FALLBACK = os.environ.get("GROQ_FALLBACK_MODEL", "mixtral-8x7b-32768")


@dataclass
class ScoreResult:
    content_score: float = 0.0
    communication_score: float = 0.0
    behavioral_score: float = 0.0
    overall_score: float = 0.0
    tier: str = "likely_pass"
    strengths: list = field(default_factory=list)
    improvements: list = field(default_factory=list)
    transcript: str = ""
    detected_language: str = "en"
    language_match: bool = True
    model_used: str = ""
    scoring_source: str = "groq"
    raw_response: dict = field(default_factory=dict)


def _get_groq_client():
    """Return a Groq client. Raises if GROQ_API_KEY not set."""
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return Groq(api_key=api_key)


def _extract_audio_wav(video_bytes: bytes) -> bytes:
    """
    Use FFmpeg to extract 16kHz mono WAV audio from video bytes.
    Returns WAV bytes suitable for Groq Whisper.
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as video_tmp:
        video_tmp.write(video_bytes)
        video_tmp_path = video_tmp.name

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_tmp:
        audio_tmp_path = audio_tmp.name

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_tmp_path,
                "-vn",              # No video
                "-ar", "16000",     # 16kHz (Whisper requirement)
                "-ac", "1",         # Mono
                "-f", "wav",
                audio_tmp_path,
            ],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")

        with open(audio_tmp_path, "rb") as f:
            return f.read()
    finally:
        import os as _os
        for path in [video_tmp_path, audio_tmp_path]:
            try:
                _os.unlink(path)
            except Exception:
                pass


def transcribe_audio(audio_bytes: bytes, expected_language: str = "en") -> tuple[str, str]:
    """
    Transcribe audio using Groq Whisper.
    Returns (transcript_text, detected_language).

    expected_language: 'en' | 'ar' | 'both' — used as a hint to Whisper
    """
    client = _get_groq_client()

    # Whisper language hint
    language_hint = None
    if expected_language == "ar":
        language_hint = "ar"
    elif expected_language == "en":
        language_hint = "en"
    # For 'both', let Whisper auto-detect

    kwargs = {
        "file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
        "model": MODEL_TRANSCRIPTION,
        "response_format": "verbose_json",  # Includes detected language
        "temperature": 0.0,
    }
    if language_hint:
        kwargs["language"] = language_hint

    try:
        response = client.audio.transcriptions.create(**kwargs)
        transcript = response.text.strip()
        detected_language = getattr(response, "language", expected_language) or expected_language
        logger.info(
            "Transcription complete: %d chars, language=%s",
            len(transcript), detected_language
        )
        return transcript, detected_language
    except Exception as e:
        logger.error("Groq Whisper transcription failed: %s", str(e))
        raise


def score_answer(
    question: str,
    transcript: str,
    job_title: str,
    job_description: str,
    duration_seconds: float,
    detected_language: str,
    expected_language: str,
) -> ScoreResult:
    """
    Score a single interview answer using Groq LLM.
    Returns ScoreResult with all scores and analysis.
    """
    if not transcript or len(transcript.strip()) < 10:
        # Very short/empty transcript — likely silence or noise
        return ScoreResult(
            content_score=0.0,
            communication_score=0.0,
            behavioral_score=5.0,
            overall_score=1.5,
            tier="likely_pass",
            strengths=[],
            improvements=["No response provided", "Please ensure your microphone is working"],
            transcript=transcript,
            detected_language=detected_language,
            language_match=True,
            model_used="none",
            scoring_source="fallback",
        )

    language_note = ""
    if expected_language != "both" and detected_language != expected_language:
        language_note = f"Note: The expected interview language was {expected_language.upper()}, but the candidate responded in {detected_language.upper()}."

    prompt = f"""You are an expert HR interview evaluator. Score the following video interview response.

Job Title: {job_title}
Job Description: {job_description or 'Not provided'}
Interview Question: {question}
Candidate Transcript: {transcript}
Response Duration: {duration_seconds:.0f} seconds
Detected Language: {detected_language}
{language_note}

Evaluate and return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "content_score": <0-100>,
  "communication_score": <0-100>,
  "behavioral_score": <0-100>,
  "overall_score": <0-100>,
  "tier": "<strong_proceed|consider|likely_pass>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<improvement 1>", "<improvement 2>"],
  "language_match": <true|false>
}}

Scoring criteria:
- content_score (50%): Relevance to question, depth of answer, specific examples, domain knowledge
- communication_score (30%): Clarity, structure, fluency, conciseness, vocabulary
- behavioral_score (20%): Confidence, enthusiasm, professionalism, energy level
- overall_score: content*0.5 + communication*0.3 + behavioral*0.2
- tier: strong_proceed if overall>=70, consider if overall>=50, likely_pass otherwise
- language_match: true if candidate responded in the expected language, false otherwise"""

    client = _get_groq_client()
    model_used = MODEL_SCORING

    for attempt in range(2):  # Try primary model, fallback on failure
        try:
            response = client.chat.completions.create(
                model=model_used,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )

            raw_text = response.choices[0].message.content.strip()

            # Strip any markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            result_data = json.loads(raw_text)

            # Validate and clamp scores
            content = max(0.0, min(100.0, float(result_data.get("content_score", 0))))
            communication = max(0.0, min(100.0, float(result_data.get("communication_score", 0))))
            behavioral = max(0.0, min(100.0, float(result_data.get("behavioral_score", 0))))

            # Recompute overall from weighted components (don't trust LLM math)
            overall = (
                content * CONTENT_WEIGHT +
                communication * COMMUNICATION_WEIGHT +
                behavioral * BEHAVIORAL_WEIGHT
            )

            # Determine tier from computed overall
            if overall >= TIER_STRONG_PROCEED:
                tier = "strong_proceed"
            elif overall >= TIER_CONSIDER:
                tier = "consider"
            else:
                tier = "likely_pass"

            return ScoreResult(
                content_score=round(content, 2),
                communication_score=round(communication, 2),
                behavioral_score=round(behavioral, 2),
                overall_score=round(overall, 2),
                tier=tier,
                strengths=result_data.get("strengths", [])[:5],
                improvements=result_data.get("improvements", [])[:3],
                transcript=transcript,
                detected_language=detected_language,
                language_match=bool(result_data.get("language_match", True)),
                model_used=model_used,
                scoring_source="groq",
                raw_response=result_data,
            )

        except json.JSONDecodeError as e:
            logger.warning("LLM returned invalid JSON (attempt %d): %s", attempt + 1, str(e))
            if attempt == 0:
                model_used = MODEL_FALLBACK
                logger.info("Retrying with fallback model: %s", MODEL_FALLBACK)
            else:
                raise RuntimeError(f"LLM scoring failed: invalid JSON after 2 attempts")

        except Exception as e:
            logger.error("LLM scoring error (attempt %d, model %s): %s", attempt + 1, model_used, str(e))
            if attempt == 0:
                model_used = MODEL_FALLBACK
            else:
                raise


def score_video(
    video_bytes: bytes,
    question: str,
    job_title: str,
    job_description: str,
    expected_language: str = "en",
) -> ScoreResult:
    """
    Full pipeline: video bytes → audio extraction → transcription → scoring.
    Returns ScoreResult.
    """
    # Step 1: Extract audio
    logger.info("Extracting audio from video (%d bytes)...", len(video_bytes))
    audio_bytes = _extract_audio_wav(video_bytes)
    logger.info("Audio extracted: %d bytes", len(audio_bytes))

    # Step 2: Transcribe
    logger.info("Transcribing audio...")
    transcript, detected_language = transcribe_audio(audio_bytes, expected_language)
    logger.info("Transcript: %d chars", len(transcript))

    # Step 3: Score
    logger.info("Scoring answer with Groq LLM...")
    result = score_answer(
        question=question,
        transcript=transcript,
        job_title=job_title,
        job_description=job_description,
        duration_seconds=len(audio_bytes) / (16000 * 2),  # Rough estimate from WAV
        detected_language=detected_language,
        expected_language=expected_language,
    )

    return result

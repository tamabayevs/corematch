"""
CoreMatch — Public Blueprint
Candidate-facing endpoints. Auth via invite_token (no JWT).
These endpoints handle the full candidate interview flow.
"""
import os
import io
import json
import uuid
import logging
import datetime
from flask import Blueprint, request, jsonify, g, redirect
from database.connection import get_db
from api.middleware import require_invite_token

logger = logging.getLogger(__name__)
public_bp = Blueprint("public", __name__)


# ──────────────────────────────────────────────────────────────
# GET /api/public/campaign-info/:campaign_id
# Public endpoint — returns campaign info for the apply page
# ──────────────────────────────────────────────────────────────

@public_bp.route("/campaign-info/<campaign_id>", methods=["GET"])
def get_campaign_info(campaign_id):
    """
    Public endpoint returning campaign info for the self-registration page.
    No auth required — this is the landing page for public application links.
    """
    # Validate UUID format
    try:
        uuid.UUID(campaign_id)
    except ValueError:
        return jsonify({"error": "Invalid campaign ID format"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.id, c.name, c.job_title, c.job_description,
                           c.company_name, c.language, c.status,
                           c.questions, c.max_recording_seconds,
                           b.logo_url, b.primary_color, b.secondary_color
                    FROM campaigns c
                    LEFT JOIN company_branding b ON b.user_id = c.user_id
                    WHERE c.id = %s
                    """,
                    (campaign_id,),
                )
                row = cur.fetchone()
    except Exception as e:
        logger.error("Campaign info DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch campaign info"}), 500

    if not row:
        return jsonify({"error": "Campaign not found"}), 404

    if row[6] != "active":
        return jsonify({"error": "This campaign is no longer accepting applications"}), 410

    questions = row[7] if isinstance(row[7], list) else json.loads(row[7]) if row[7] else []

    return jsonify({
        "campaign": {
            "id": str(row[0]),
            "name": row[1],
            "job_title": row[2],
            "job_description": row[3],
            "company_name": row[4],
            "language": row[5],
            "question_count": len(questions),
            "max_recording_seconds": row[8],
        },
        "branding": {
            "logo_url": row[9],
            "primary_color": row[10] or "#0D9488",
            "secondary_color": row[11] or "#F59E0B",
        },
    })


# ──────────────────────────────────────────────────────────────
# POST /api/public/apply/:campaign_id
# Public self-registration endpoint
# ──────────────────────────────────────────────────────────────

@public_bp.route("/apply/<campaign_id>", methods=["POST"])
def public_apply(campaign_id):
    """
    Public self-registration endpoint.
    Candidates submit name/email to receive an invite token and start the interview.
    """
    # Validate UUID format
    try:
        uuid.UUID(campaign_id)
    except ValueError:
        return jsonify({"error": "Invalid campaign ID format"}), 400

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip() or None

    if not full_name:
        return jsonify({"error": "Full name is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Basic email validation
    import re
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({"error": "Invalid email format"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check campaign exists and is active
                cur.execute(
                    """
                    SELECT id, name, job_title, company_name, questions, status,
                           user_id, invite_expiry_days, language
                    FROM campaigns WHERE id = %s
                    """,
                    (campaign_id,),
                )
                campaign = cur.fetchone()

                if not campaign:
                    return jsonify({"error": "Campaign not found"}), 404

                if campaign[5] != "active":
                    return jsonify({"error": "This campaign is no longer accepting applications"}), 410

                # Check for duplicate email in this campaign
                cur.execute(
                    """
                    SELECT id FROM candidates
                    WHERE campaign_id = %s AND email = %s
                    """,
                    (campaign_id, email),
                )
                existing = cur.fetchone()
                if existing:
                    return jsonify({"error": "You have already applied to this campaign"}), 409

                # Create candidate
                candidate_id = str(uuid.uuid4())
                invite_token = str(uuid.uuid4())
                reference_id = f"CM-{uuid.uuid4().hex[:6].upper()}"
                questions = campaign[4] if isinstance(campaign[4], list) else json.loads(campaign[4]) if campaign[4] else []
                expiry_days = campaign[7] or 7
                invite_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)

                cur.execute(
                    """
                    INSERT INTO candidates
                    (id, campaign_id, full_name, email, phone, status, invite_token,
                     reference_id, questions_snapshot, invite_expires_at, source, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'invited', %s, %s, %s::jsonb, %s,
                            'public_application', NOW())
                    """,
                    (
                        candidate_id, campaign_id, full_name, email, phone,
                        invite_token, reference_id,
                        json.dumps(questions), invite_expires_at,
                    ),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        "candidate.public_application",
                        "candidate",
                        candidate_id,
                        json.dumps({
                            "campaign_id": campaign_id,
                            "campaign_name": campaign[1],
                            "email": email,
                        }),
                        request.remote_addr,
                    ),
                )

    except Exception as e:
        logger.error("Public apply DB error: %s", str(e))
        return jsonify({"error": "Failed to process application"}), 500

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    interview_url = f"{frontend_url}/interview/{invite_token}/welcome"

    return jsonify({
        "message": "Application submitted successfully",
        "invite_token": invite_token,
        "reference_id": reference_id,
        "interview_url": interview_url,
    }), 201

# Valid video MIME types and their magic bytes
VALID_VIDEO_TYPES = {
    "video/webm": b"\x1a\x45\xdf\xa3",   # WebM EBML header
    "video/mp4": None,                    # MP4 checked differently (ftyp at byte 4)
}
MAX_VIDEO_SIZE_BYTES = 500 * 1024 * 1024  # 500MB hard limit


def _check_magic_bytes(file_data: bytes, mime_type: str) -> bool:
    """Verify file magic bytes match the declared MIME type."""
    if mime_type == "video/webm":
        return file_data[:4] == b"\x1a\x45\xdf\xa3"
    if mime_type == "video/mp4":
        # MP4 has "ftyp" at bytes 4-8, but may also start with moov atom
        if len(file_data) < 8:
            return False
        return file_data[4:8] == b"ftyp" or file_data[0:4] == b"\x00\x00\x00\x18"
    return False


# ──────────────────────────────────────────────────────────────
# GET /s/:token — Short link redirect (for SMS)
# ──────────────────────────────────────────────────────────────

@public_bp.route("/s/<token>", methods=["GET"])
def short_link_redirect(token):
    """
    Redirect SMS short link to full interview URL.
    The token is a valid invite token.
    This endpoint is intentionally not authenticated — it's a redirect.
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return redirect(f"{frontend_url}/interview/{token}/welcome", code=302)


# Register short link route at /s/ directly (not under /api/public)
# Note: This route is also registered in app.py at root level


# ──────────────────────────────────────────────────────────────
# GET /api/public/invite/:token
# ──────────────────────────────────────────────────────────────

@public_bp.route("/invite/<token>", methods=["GET"])
@require_invite_token
def get_invite(token):
    """
    Validate invite token and return campaign + candidate info.
    Called by Welcome.jsx on page load.
    """
    candidate = g.candidate
    campaign = g.campaign

    return jsonify({
        "candidate": {
            "id": candidate["id"],
            "full_name": candidate["full_name"],
            "status": candidate["status"],
            "consent_given": candidate["consent_given"],
            "reference_id": candidate["reference_id"],
        },
        "campaign": {
            "id": campaign["id"],
            "name": campaign["name"],
            "job_title": campaign["job_title"],
            "company_name": campaign["company_name"],
            "language": campaign["language"],
            "max_recording_seconds": campaign["max_recording_seconds"],
            "allow_retakes": campaign["allow_retakes"],
            "question_count": len(candidate["questions_snapshot"]),
        },
        "questions": candidate["questions_snapshot"],
        "invite_expires_at": candidate["invite_expires_at"].isoformat() if candidate["invite_expires_at"] else None,
    })


# ──────────────────────────────────────────────────────────────
# POST /api/public/consent/:token
# ──────────────────────────────────────────────────────────────

@public_bp.route("/consent/<token>", methods=["POST"])
@require_invite_token
def record_consent(token):
    """
    Record candidate's informed consent.
    Must be called before any recording can begin.
    PDPL requirement: consent must be explicit and recorded server-side.
    """
    candidate = g.candidate

    if candidate["consent_given"]:
        return jsonify({"message": "Consent already recorded"}), 200

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE candidates
                    SET consent_given = TRUE,
                        consent_given_at = NOW(),
                        status = CASE WHEN status = 'invited' THEN 'started' ELSE status END
                    WHERE id = %s
                    """,
                    (candidate["id"],),
                )

                # Audit log
                cur.execute(
                    """
                    INSERT INTO audit_log (action, entity_type, entity_id, metadata, ip_address)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        "candidate.consent_given",
                        "candidate",
                        candidate["id"],
                        json.dumps({"campaign_id": candidate["campaign_id"]}),
                        request.remote_addr,
                    ),
                )
    except Exception as e:
        logger.error("Record consent DB error: %s", str(e))
        return jsonify({"error": "Failed to record consent"}), 500

    return jsonify({"message": "Consent recorded", "consent_given": True})


# ──────────────────────────────────────────────────────────────
# POST /api/public/video-upload/:token
# Rate limit: 20/hour per token
# ──────────────────────────────────────────────────────────────

@public_bp.route("/video-upload/<token>", methods=["POST"])
@require_invite_token
def upload_video(token):
    """
    Upload a single video answer for a specific question.
    - Validates file type and size
    - Stores to Cloudflare R2 (or local in development)
    - Creates/updates video_answer record
    - Enqueues AI processing job if all videos are uploaded
    Rate limit: 20/hour per token (5 answers + re-records buffer)
    """
    candidate = g.candidate
    campaign = g.campaign

    # Consent must be given before uploading
    if not candidate["consent_given"]:
        return jsonify({"error": "Consent must be given before uploading videos"}), 403

    # Get question index
    question_index_raw = request.form.get("question_index")
    if question_index_raw is None:
        return jsonify({"error": "question_index is required"}), 400

    try:
        question_index = int(question_index_raw)
    except ValueError:
        return jsonify({"error": "question_index must be an integer"}), 400

    questions = candidate["questions_snapshot"]
    if not (0 <= question_index < len(questions)):
        return jsonify({"error": f"question_index must be 0-{len(questions)-1}"}), 400

    question_text = questions[question_index].get("text", "")

    # Validate file presence
    if "video" not in request.files:
        return jsonify({"error": "video file is required"}), 400

    video_file = request.files["video"]

    # Validate content type
    content_type = video_file.content_type or ""
    if content_type not in VALID_VIDEO_TYPES:
        return jsonify({"error": "Invalid file type. Only video/webm and video/mp4 are accepted"}), 400

    # Read file data for size and magic byte checks
    file_data = video_file.read()

    if len(file_data) == 0:
        return jsonify({"error": "File is empty"}), 400

    if len(file_data) > MAX_VIDEO_SIZE_BYTES:
        return jsonify({"error": f"File too large. Maximum size is 500MB"}), 413

    # Validate magic bytes (don't trust Content-Type header alone)
    if not _check_magic_bytes(file_data, content_type):
        logger.warning(
            "Magic byte mismatch for candidate %s, claimed type: %s",
            candidate["id"], content_type
        )
        return jsonify({"error": "File content does not match declared type"}), 400

    # Generate storage key (UUID filename — never use original filename)
    file_ext = "webm" if content_type == "video/webm" else "mp4"
    storage_key = f"interviews/{candidate['campaign_id']}/{candidate['id']}/q{question_index}_{uuid.uuid4()}.{file_ext}"

    # Upload to storage
    try:
        from services.storage_service import get_storage_service
        storage = get_storage_service()
        file_obj = io.BytesIO(file_data)
        storage.upload_file(file_obj, storage_key, content_type=content_type)
    except Exception as e:
        logger.error("Video upload storage error: %s", str(e))
        return jsonify({"error": "Failed to store video"}), 500

    # Duration from form data (set by frontend MediaRecorder)
    duration_raw = request.form.get("duration_seconds")
    duration_seconds = None
    if duration_raw:
        try:
            duration_seconds = float(duration_raw)
        except ValueError:
            pass

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Upsert video_answer (allow re-record: update if exists)
                cur.execute(
                    """
                    INSERT INTO video_answers
                    (candidate_id, question_index, question_text, storage_key,
                     storage_provider, file_format, file_size_bytes, duration_seconds,
                     processing_status, uploaded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                    ON CONFLICT (candidate_id, question_index)
                    DO UPDATE SET
                        storage_key = EXCLUDED.storage_key,
                        file_format = EXCLUDED.file_format,
                        file_size_bytes = EXCLUDED.file_size_bytes,
                        duration_seconds = EXCLUDED.duration_seconds,
                        processing_status = 'pending',
                        transcript = NULL,
                        uploaded_at = NOW()
                    RETURNING id
                    """,
                    (
                        candidate["id"], question_index, question_text, storage_key,
                        "r2", file_ext, len(file_data), duration_seconds,
                    ),
                )
                video_answer_id = str(cur.fetchone()[0])

                # Count how many videos have been uploaded for this candidate
                cur.execute(
                    """
                    SELECT COUNT(*) FROM video_answers
                    WHERE candidate_id = %s AND storage_key IS NOT NULL
                    """,
                    (candidate["id"],),
                )
                uploaded_count = cur.fetchone()[0]

    except Exception as e:
        logger.error("Video upload DB error: %s", str(e))
        # Try to clean up the uploaded file
        try:
            from services.storage_service import get_storage_service
            get_storage_service().delete_file(storage_key)
        except Exception:
            pass
        return jsonify({"error": "Failed to record video upload"}), 500

    total_questions = len(questions)
    all_uploaded = uploaded_count >= total_questions

    response_data = {
        "message": "Video uploaded successfully",
        "video_answer_id": video_answer_id,
        "question_index": question_index,
        "uploaded_count": uploaded_count,
        "total_questions": total_questions,
        "all_uploaded": all_uploaded,
    }

    # If all questions answered, trigger AI processing
    if all_uploaded:
        try:
            _submit_for_processing(candidate["id"])
            response_data["processing_started"] = True
        except Exception as e:
            logger.error("Failed to enqueue processing job: %s", str(e))
            response_data["processing_started"] = False

    return jsonify(response_data), 201


def _submit_for_processing(candidate_id: str) -> None:
    """
    Mark candidate as submitted and enqueue background AI processing job.
    """
    import redis
    from rq import Queue

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_conn = redis.from_url(redis_url)
    q = Queue("default", connection=redis_conn)

    # Mark candidate as submitted
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE candidates SET status = 'submitted' WHERE id = %s",
                (candidate_id,),
            )
            cur.execute(
                """
                INSERT INTO audit_log (action, entity_type, entity_id, ip_address)
                VALUES (%s, %s, %s, %s)
                """,
                ("candidate.submitted", "candidate", candidate_id, "system"),
            )

    # Enqueue the processing job (runs in background RQ worker)
    from workers.video_processor import process_candidate
    job = q.enqueue(
        process_candidate,
        candidate_id,
        job_timeout=600,  # 10 minutes max
        result_ttl=86400,  # Keep result for 24 hours
    )
    logger.info("Enqueued AI processing job %s for candidate %s", job.id, candidate_id)

    # In-app notification to campaign owner
    from services.notification_service import notify_campaign_owner
    notify_campaign_owner(
        candidate_id=candidate_id,
        notification_type="submission",
        title="New interview submission",
        message="A candidate has submitted their video interview.",
    )


# ──────────────────────────────────────────────────────────────
# GET /api/public/status/:token
# ──────────────────────────────────────────────────────────────

@public_bp.route("/status/<token>", methods=["GET"])
@require_invite_token
def get_status(token):
    """
    Poll endpoint for AI processing status.
    Frontend polls this after final video upload to know when scoring is complete.
    """
    candidate = g.candidate

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT va.question_index, va.processing_status,
                           s.overall_score, s.tier
                    FROM video_answers va
                    LEFT JOIN ai_scores s ON s.video_answer_id = va.id
                    WHERE va.candidate_id = %s
                    ORDER BY va.question_index ASC
                    """,
                    (candidate["id"],),
                )
                rows = cur.fetchall()
    except Exception as e:
        logger.error("Get status DB error: %s", str(e))
        return jsonify({"error": "Failed to fetch status"}), 500

    if not rows:
        return jsonify({
            "status": candidate["status"],
            "processing_status": "pending",
            "answers": [],
        })

    # Determine overall processing status
    statuses = [row[1] for row in rows]
    if all(s == "complete" for s in statuses):
        overall = "complete"
    elif any(s == "failed" for s in statuses):
        overall = "partial"
    elif any(s == "processing" for s in statuses):
        overall = "processing"
    else:
        overall = "pending"

    return jsonify({
        "status": candidate["status"],
        "processing_status": overall,
        "answers": [
            {
                "question_index": row[0],
                "processing_status": row[1],
                "overall_score": float(row[2]) if row[2] else None,
                "tier": row[3],
            }
            for row in rows
        ],
        "overall_score": candidate["overall_score"],
    })


# ──────────────────────────────────────────────────────────────
# POST /api/public/submit/:token
# Called when ALL videos are uploaded to finalize submission
# ──────────────────────────────────────────────────────────────

@public_bp.route("/submit/<token>", methods=["POST"])
@require_invite_token
def submit_interview(token):
    """
    Explicitly mark interview as submitted.
    Also accepts an optional 'submit_partial' flag to submit even if some uploads failed.
    """
    candidate = g.candidate
    campaign = g.campaign

    if candidate["status"] == "submitted":
        return jsonify({
            "message": "Already submitted",
            "reference_id": candidate["reference_id"],
        })

    data = request.get_json(silent=True) or {}
    submit_partial = data.get("submit_partial", False)

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM video_answers
                    WHERE candidate_id = %s AND storage_key IS NOT NULL
                    """,
                    (candidate["id"],),
                )
                uploaded_count = cur.fetchone()[0]

    except Exception as e:
        logger.error("Submit interview count error: %s", str(e))
        return jsonify({"error": "Failed to verify uploads"}), 500

    total_questions = len(candidate["questions_snapshot"])

    if uploaded_count < total_questions and not submit_partial:
        return jsonify({
            "error": "Not all questions have been answered",
            "uploaded": uploaded_count,
            "total": total_questions,
        }), 400

    try:
        _submit_for_processing(candidate["id"])
    except Exception as e:
        logger.error("Submit for processing error: %s", str(e))
        return jsonify({"error": "Failed to submit interview"}), 500

    return jsonify({
        "message": "Interview submitted successfully",
        "reference_id": candidate["reference_id"],
        "uploaded_count": uploaded_count,
        "total_questions": total_questions,
        "partial": uploaded_count < total_questions,
    })

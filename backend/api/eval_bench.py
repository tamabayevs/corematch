"""
CoreMatch — Eval Bench API
Upload benchmark videos, run AI scoring evaluations, view results.
Protected by ADMIN_API_KEY — only accessible by admin.
"""
import os
import uuid
import json
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g
from database.connection import get_db

logger = logging.getLogger(__name__)
eval_bench_bp = Blueprint("eval_bench", __name__)

ALLOWED_EXTENSIONS = {"webm", "mp4"}
ALLOWED_MIMETYPES = {"video/webm", "video/mp4"}
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

# WebM: EBML header, MP4: ftyp box
MAGIC_BYTES = {
    "webm": b"\x1a\x45\xdf\xa3",
    "mp4": b"ftyp",
}

VALID_MODELS = [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
]


def require_admin(f):
    """Require ADMIN_API_KEY header or query param for access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_key = os.environ.get("ADMIN_API_KEY", "")
        if not admin_key:
            return jsonify({"error": "Admin access not configured"}), 503

        provided = (
            request.headers.get("X-Admin-Key", "") or
            request.args.get("admin_key", "") or
            request.args.get("key", "")
        )
        if provided != admin_key:
            return jsonify({"error": "Unauthorized"}), 401

        # Get admin user (first user in DB or from header)
        admin_user_id = request.headers.get("X-Admin-User-Id")
        if not admin_user_id:
            # Default to first user
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users ORDER BY created_at LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        admin_user_id = str(row[0])
                    else:
                        return jsonify({"error": "No users in database"}), 500

        g.admin_user_id = admin_user_id
        return f(*args, **kwargs)
    return decorated


def _validate_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


# ── Benchmark Endpoints ──────────────────────────────────────


@eval_bench_bp.route("/benchmarks", methods=["GET"])
@require_admin
def list_benchmarks():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, question_text, job_title, job_description,
                       language, storage_key, file_size_bytes, notes, created_at
                FROM eval_benchmarks
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (g.admin_user_id,))
            rows = cur.fetchall()

    benchmarks = []
    for r in rows:
        benchmarks.append({
            "id": str(r[0]),
            "name": r[1],
            "question_text": r[2],
            "job_title": r[3],
            "job_description": r[4] or "",
            "language": r[5],
            "storage_key": r[6],
            "file_size_bytes": r[7],
            "notes": r[8] or "",
            "created_at": r[9].isoformat() if r[9] else None,
        })

    return jsonify({"benchmarks": benchmarks, "total": len(benchmarks)}), 200


@eval_bench_bp.route("/benchmarks", methods=["POST"])
@require_admin
def upload_benchmark():
    """Upload a benchmark video with metadata."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files["video"]
    name = request.form.get("name", "").strip()
    question_text = request.form.get("question_text", "").strip()
    job_title = request.form.get("job_title", "").strip()

    if not name or not question_text or not job_title:
        return jsonify({"error": "name, question_text, and job_title are required"}), 400

    # Read video bytes
    video_bytes = video_file.read()
    if len(video_bytes) > MAX_VIDEO_SIZE:
        return jsonify({"error": f"Video too large (max {MAX_VIDEO_SIZE // (1024*1024)}MB)"}), 400

    if len(video_bytes) < 100:
        return jsonify({"error": "Video file too small"}), 400

    # Magic byte validation
    is_webm = video_bytes[:4] == MAGIC_BYTES["webm"]
    is_mp4 = video_bytes[4:8] == MAGIC_BYTES["mp4"] or video_bytes[:4] == b"\x00\x00\x00\x18"
    if not is_webm and not is_mp4:
        return jsonify({"error": "Invalid video format. Only WebM and MP4 accepted."}), 400

    file_ext = "webm" if is_webm else "mp4"

    # Upload to storage
    from services.storage_service import get_storage_service
    import io
    storage = get_storage_service()
    storage_key = f"eval-bench/{g.admin_user_id}/{uuid.uuid4()}.{file_ext}"
    content_type = "video/webm" if is_webm else "video/mp4"
    storage.upload_file(io.BytesIO(video_bytes), storage_key, content_type)

    # Insert into DB
    job_description = request.form.get("job_description", "").strip()
    language = request.form.get("language", "en").strip()
    notes = request.form.get("notes", "").strip()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO eval_benchmarks
                    (user_id, name, question_text, job_title, job_description,
                     language, storage_key, file_size_bytes, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (
                g.admin_user_id, name, question_text, job_title,
                job_description, language, storage_key, len(video_bytes), notes,
            ))
            row = cur.fetchone()

    return jsonify({
        "message": "Benchmark uploaded",
        "benchmark": {
            "id": str(row[0]),
            "name": name,
            "question_text": question_text,
            "job_title": job_title,
            "storage_key": storage_key,
            "file_size_bytes": len(video_bytes),
            "created_at": row[1].isoformat() if row[1] else None,
        }
    }), 201


@eval_bench_bp.route("/benchmarks/<benchmark_id>", methods=["DELETE"])
@require_admin
def delete_benchmark(benchmark_id):
    if not _validate_uuid(benchmark_id):
        return jsonify({"error": "Invalid benchmark ID"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT storage_key FROM eval_benchmarks WHERE id = %s AND user_id = %s",
                (benchmark_id, g.admin_user_id)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Benchmark not found"}), 404

            storage_key = row[0]

            # Delete from storage
            try:
                from services.storage_service import get_storage_service
                get_storage_service().delete_file(storage_key)
            except Exception as e:
                logger.warning("Failed to delete storage file %s: %s", storage_key, str(e))

            # Delete from DB (cascades to eval_results)
            cur.execute("DELETE FROM eval_benchmarks WHERE id = %s", (benchmark_id,))

    return jsonify({"message": "Benchmark deleted"}), 200


# ── Run Endpoints ────────────────────────────────────────────


@eval_bench_bp.route("/runs", methods=["GET"])
@require_admin
def list_runs():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, model_name, status, total_benchmarks,
                       completed_benchmarks, failed_benchmarks,
                       started_at, completed_at, created_at
                FROM eval_runs
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (g.admin_user_id,))
            rows = cur.fetchall()

    runs = []
    for r in rows:
        runs.append({
            "id": str(r[0]),
            "model_name": r[1],
            "status": r[2],
            "total_benchmarks": r[3] or 0,
            "completed_benchmarks": r[4] or 0,
            "failed_benchmarks": r[5] or 0,
            "started_at": r[6].isoformat() if r[6] else None,
            "completed_at": r[7].isoformat() if r[7] else None,
            "created_at": r[8].isoformat() if r[8] else None,
        })

    return jsonify({"runs": runs}), 200


@eval_bench_bp.route("/runs", methods=["POST"])
@require_admin
def start_run():
    """Start a new evaluation run with the specified model."""
    data = request.get_json(silent=True) or {}
    model_name = data.get("model", "llama-3.3-70b-versatile")

    if model_name not in VALID_MODELS:
        return jsonify({
            "error": f"Invalid model. Choose from: {', '.join(VALID_MODELS)}"
        }), 400

    # Check benchmarks exist
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM eval_benchmarks WHERE user_id = %s",
                (g.admin_user_id,)
            )
            count = cur.fetchone()[0]

    if count == 0:
        return jsonify({"error": "No benchmarks uploaded. Upload videos first."}), 400

    # Check no run already in progress
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM eval_runs WHERE user_id = %s AND status IN ('pending', 'running') LIMIT 1",
                (g.admin_user_id,)
            )
            if cur.fetchone():
                return jsonify({"error": "An evaluation run is already in progress"}), 409

    # Create run + result placeholders
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO eval_runs (user_id, model_name, status, total_benchmarks)
                VALUES (%s, %s, 'pending', %s)
                RETURNING id
            """, (g.admin_user_id, model_name, count))
            run_id = str(cur.fetchone()[0])

            # Create placeholder result rows for each benchmark
            cur.execute(
                "SELECT id FROM eval_benchmarks WHERE user_id = %s ORDER BY created_at",
                (g.admin_user_id,)
            )
            bm_ids = [str(r[0]) for r in cur.fetchall()]

            for bm_id in bm_ids:
                cur.execute("""
                    INSERT INTO eval_results (run_id, benchmark_id, status)
                    VALUES (%s, %s, 'pending')
                """, (run_id, bm_id))

    # Enqueue RQ job
    try:
        import redis
        from rq import Queue
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_conn = redis.from_url(redis_url)
        q = Queue("default", connection=redis_conn)
        q.enqueue(
            "workers.eval_bench_worker.run_eval",
            run_id, g.admin_user_id, model_name,
            job_timeout=900,
        )
        logger.info("Eval run %s enqueued: %d benchmarks with model %s", run_id, count, model_name)
    except Exception as e:
        logger.error("Failed to enqueue eval run: %s", str(e))
        # Mark run as failed if can't enqueue
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE eval_runs SET status = 'failed' WHERE id = %s",
                    (run_id,)
                )
        return jsonify({"error": f"Failed to start evaluation: {str(e)}"}), 500

    return jsonify({
        "message": "Evaluation run started",
        "run_id": run_id,
        "model": model_name,
        "benchmarks": count,
    }), 201


@eval_bench_bp.route("/runs/<run_id>", methods=["GET"])
@require_admin
def get_run(run_id):
    """Get full details of a run including per-benchmark results."""
    if not _validate_uuid(run_id):
        return jsonify({"error": "Invalid run ID"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, model_name, status, total_benchmarks,
                       completed_benchmarks, failed_benchmarks,
                       started_at, completed_at, created_at
                FROM eval_runs WHERE id = %s AND user_id = %s
            """, (run_id, g.admin_user_id))
            run_row = cur.fetchone()
            if not run_row:
                return jsonify({"error": "Run not found"}), 404

            # Fetch results with benchmark info
            cur.execute("""
                SELECT er.id, er.benchmark_id, er.status,
                       er.transcript, er.detected_language,
                       er.content_score, er.communication_score,
                       er.behavioral_score, er.overall_score, er.tier,
                       er.strengths, er.improvements,
                       er.language_match, er.model_used, er.latency_ms,
                       er.error_message,
                       eb.name, eb.question_text, eb.job_title
                FROM eval_results er
                JOIN eval_benchmarks eb ON er.benchmark_id = eb.id
                WHERE er.run_id = %s
                ORDER BY eb.created_at
            """, (run_id,))
            result_rows = cur.fetchall()

    results = []
    for r in result_rows:
        results.append({
            "id": str(r[0]),
            "benchmark_id": str(r[1]),
            "status": r[2],
            "transcript": r[3] or "",
            "detected_language": r[4] or "",
            "content_score": float(r[5]) if r[5] is not None else None,
            "communication_score": float(r[6]) if r[6] is not None else None,
            "behavioral_score": float(r[7]) if r[7] is not None else None,
            "overall_score": float(r[8]) if r[8] is not None else None,
            "tier": r[9],
            "strengths": r[10] if r[10] else [],
            "improvements": r[11] if r[11] else [],
            "language_match": r[12],
            "model_used": r[13] or "",
            "latency_ms": r[14],
            "error_message": r[15] or "",
            "benchmark_name": r[16],
            "question_text": r[17],
            "job_title": r[18],
        })

    run = {
        "id": str(run_row[0]),
        "model_name": run_row[1],
        "status": run_row[2],
        "total_benchmarks": run_row[3] or 0,
        "completed_benchmarks": run_row[4] or 0,
        "failed_benchmarks": run_row[5] or 0,
        "started_at": run_row[6].isoformat() if run_row[6] else None,
        "completed_at": run_row[7].isoformat() if run_row[7] else None,
        "created_at": run_row[8].isoformat() if run_row[8] else None,
        "results": results,
    }

    return jsonify({"run": run}), 200


@eval_bench_bp.route("/runs/<run_id>/status", methods=["GET"])
@require_admin
def get_run_status(run_id):
    """Lightweight status polling endpoint."""
    if not _validate_uuid(run_id):
        return jsonify({"error": "Invalid run ID"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, total_benchmarks, completed_benchmarks, failed_benchmarks
                FROM eval_runs WHERE id = %s AND user_id = %s
            """, (run_id, g.admin_user_id))
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "Run not found"}), 404

    return jsonify({
        "status": row[0],
        "total_benchmarks": row[1] or 0,
        "completed_benchmarks": row[2] or 0,
        "failed_benchmarks": row[3] or 0,
    }), 200

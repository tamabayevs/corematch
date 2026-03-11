"""
CoreMatch — Admin Panel
Server-rendered HTML admin interface for internal tools.
Protected by ADMIN_API_KEY via query param or cookie.
"""
import os
import json
import logging
from functools import wraps
from flask import Blueprint, request, redirect, make_response
from database.connection import get_db

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


def _check_admin():
    """Check admin key from cookie or query param. Returns True if valid."""
    admin_key = os.environ.get("ADMIN_API_KEY", "")
    if not admin_key:
        return False
    provided = request.cookies.get("admin_key", "") or request.args.get("key", "")
    return provided == admin_key


def require_admin_html(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_key = os.environ.get("ADMIN_API_KEY", "")
        if not admin_key:
            return _html_page("Admin", "<p style='color:#e74c3c;'>ADMIN_API_KEY env var is not set on the server.</p>"), 503
        if not _check_admin():
            key_param = request.args.get("key", "")
            if key_param:
                # Debug: show lengths to diagnose mismatch (no values exposed)
                provided_len = len(key_param)
                expected_len = len(admin_key)
                hint = "Length mismatch: you sent %d chars, expected %d" % (provided_len, expected_len)
                if provided_len == expected_len:
                    # Same length but different — check for whitespace
                    hint = "Same length (%d) but values differ. Check for trailing spaces or quotes in Railway env var." % provided_len
                msg = "<p style='color:#e74c3c;'>Invalid admin key. %s</p>" % hint
                return _html_page("Admin", msg + _login_form()), 401
            return _html_page("Admin Login", _login_form()), 401
        return f(*args, **kwargs)
    return decorated


def _login_form():
    return """
    <div style="max-width:400px;margin:60px auto;text-align:center;">
        <h2>Admin Access</h2>
        <form method="get" action="/admin">
            <input type="password" name="key" placeholder="Admin API Key"
                   style="width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:6px;font-size:14px;" />
            <button type="submit" style="width:100%;padding:10px;background:#0d9488;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">
                Enter
            </button>
        </form>
    </div>
    """


def _html_page(title, body, extra_head=""):
    admin_key = request.cookies.get("admin_key", "") or request.args.get("key", "")
    path = request.path
    overview_cls = "active" if path == "/admin" else ""
    eval_cls = "active" if "/eval-bench" in path else ""
    db_cls = "active" if path.startswith("/admin/db") else ""
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + title + ' — CoreMatch Admin</title>'
        '<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">'
        '<style>'
        'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f8fafc; }'
        '.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 16px; }'
        '.badge { display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }'
        '.badge-green { background: #d1fae5; color: #065f46; }'
        '.badge-yellow { background: #fef3c7; color: #92400e; }'
        '.badge-red { background: #fee2e2; color: #991b1b; }'
        '.badge-blue { background: #dbeafe; color: #1e40af; }'
        '.badge-gray { background: #f1f5f9; color: #475569; }'
        '.btn { display: inline-block; padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 500; text-decoration: none; cursor: pointer; border: none; }'
        '.btn-primary { background: #0d9488; color: #fff; }'
        '.btn-danger { background: #ef4444; color: #fff; }'
        '.btn-secondary { background: #e2e8f0; color: #334155; }'
        'table { width: 100%; border-collapse: collapse; }'
        'th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }'
        'th { font-weight: 600; color: #64748b; font-size: 12px; text-transform: uppercase; }'
        'nav a { color: #64748b; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 14px; }'
        'nav a:hover, nav a.active { background: #0d9488; color: #fff; }'
        + extra_head +
        '</style></head><body>'
        '<div style="max-width:1200px;margin:0 auto;padding:20px;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">'
        '<h1 style="font-size:24px;font-weight:700;color:#0f172a;">CoreMatch Admin</h1>'
        '<nav style="display:flex;gap:4px;">'
        '<a href="/admin?key=' + admin_key + '" class="' + overview_cls + '">Overview</a>'
        '<a href="/admin/eval-bench?key=' + admin_key + '" class="' + eval_cls + '">Eval Bench</a>'
        '<a href="/admin/db?key=' + admin_key + '" class="' + db_cls + '">Database</a>'
        '</nav></div>'
        + body +
        '</div></body></html>'
    )


def _key_param():
    return request.cookies.get("admin_key", "") or request.args.get("key", "")


# ── Overview ──────────────────────────────────────────────────


@admin_bp.route("/ping")
def admin_ping():
    """Simple health check for admin panel."""
    admin_key = os.environ.get("ADMIN_API_KEY", "not-set")
    return {"status": "ok", "admin_key_configured": bool(admin_key and admin_key != "not-set")}


@admin_bp.route("")
@admin_bp.route("/")
@require_admin_html
def overview():
    stats = {}
    with get_db() as conn:
        with conn.cursor() as cur:
            for table in ["users", "campaigns", "candidates", "video_answers",
                          "ai_scores", "eval_benchmarks", "eval_runs"]:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cur.fetchone()[0]
                except Exception:
                    stats[table] = "N/A"

    cards = ""
    icons = {
        "users": "👤", "campaigns": "📋", "candidates": "🎥",
        "video_answers": "🎬", "ai_scores": "🤖",
        "eval_benchmarks": "🧪", "eval_runs": "▶️",
    }
    for table, count in stats.items():
        cards += f"""
        <div class="card" style="text-align:center;">
            <div style="font-size:28px;">{icons.get(table, '📊')}</div>
            <div style="font-size:28px;font-weight:700;color:#0f172a;">{count}</div>
            <div style="color:#64748b;font-size:13px;">{table.replace('_', ' ').title()}</div>
        </div>"""

    body = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px;">
        {cards}
    </div>

    <div class="card" style="margin-top:24px;">
        <h3 style="font-weight:600;margin-bottom:12px;">Quick Links</h3>
        <ul style="list-style:none;padding:0;">
            <li style="margin:8px 0;"><a href="/admin/eval-bench?key={_key_param()}" style="color:#0d9488;">Eval Bench</a> — Upload benchmark videos, run AI evaluations</li>
            <li style="margin:8px 0;"><a href="/admin/db?key={_key_param()}" style="color:#0d9488;">Database</a> — View table counts and recent data</li>
            <li style="margin:8px 0;"><a href="/health" style="color:#0d9488;">Health Check</a> — API status</li>
        </ul>
    </div>
    """

    resp = make_response(_html_page("Overview", body))
    # Set cookie for convenience
    resp.set_cookie("admin_key", _key_param(), max_age=86400, httponly=True, samesite="Lax")
    return resp


# ── Eval Bench ────────────────────────────────────────────────


@admin_bp.route("/eval-bench")
@require_admin_html
def eval_bench():
    key = _key_param()

    # Fetch benchmarks
    with get_db() as conn:
        with conn.cursor() as cur:
            # Get admin user
            cur.execute("SELECT id FROM users ORDER BY created_at LIMIT 1")
            user_row = cur.fetchone()
            if not user_row:
                return _html_page("Eval Bench", "<p>No users in database.</p>")
            admin_id = str(user_row[0])

            cur.execute("""
                SELECT id, name, question_text, job_title, language,
                       file_size_bytes, created_at
                FROM eval_benchmarks WHERE user_id = %s ORDER BY created_at DESC
            """, (admin_id,))
            benchmarks = cur.fetchall()

            cur.execute("""
                SELECT id, model_name, status, total_benchmarks,
                       completed_benchmarks, failed_benchmarks,
                       started_at, completed_at, created_at
                FROM eval_runs WHERE user_id = %s ORDER BY created_at DESC LIMIT 20
            """, (admin_id,))
            runs = cur.fetchall()

    # Benchmarks table
    bm_rows = ""
    for b in benchmarks:
        size_kb = (b[5] or 0) // 1024
        created = b[6].strftime("%Y-%m-%d %H:%M") if b[6] else ""
        bm_rows += f"""<tr>
            <td>{b[1]}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{b[2]}</td>
            <td>{b[3]}</td>
            <td>{b[4]}</td>
            <td>{size_kb} KB</td>
            <td>{created}</td>
            <td>
                <form method="post" action="/admin/eval-bench/delete/{b[0]}?key={key}" style="display:inline;"
                      onsubmit="return confirm('Delete this benchmark?')">
                    <button type="submit" class="btn btn-danger" style="padding:4px 10px;font-size:12px;">Delete</button>
                </form>
            </td>
        </tr>"""

    # Runs table
    run_rows = ""
    for r in runs:
        status_class = {
            "complete": "badge-green", "running": "badge-blue",
            "pending": "badge-gray", "failed": "badge-red",
            "partial": "badge-yellow",
        }.get(r[2], "badge-gray")
        created = r[8].strftime("%Y-%m-%d %H:%M") if r[8] else ""
        progress = f"{r[4] or 0}/{r[3] or 0}"
        if r[5] and r[5] > 0:
            progress += f" ({r[5]} failed)"
        run_rows += f"""<tr>
            <td>{r[1]}</td>
            <td><span class="badge {status_class}">{r[2]}</span></td>
            <td>{progress}</td>
            <td>{created}</td>
            <td><a href="/admin/eval-bench/run/{r[0]}?key={key}" style="color:#0d9488;">View Results</a></td>
        </tr>"""

    # Build conditional sections outside f-strings (Python 3.9 compat)
    if benchmarks:
        bm_section = (
            '<table>'
            '<thead><tr><th>Name</th><th>Question</th><th>Job Title</th><th>Lang</th><th>Size</th><th>Uploaded</th><th></th></tr></thead>'
            '<tbody>' + bm_rows + '</tbody></table>'
        )
    else:
        bm_section = '<p style="color:#94a3b8;">No benchmarks uploaded yet. Upload videos above.</p>'

    if runs:
        runs_section = (
            '<table>'
            '<thead><tr><th>Model</th><th>Status</th><th>Progress</th><th>Started</th><th></th></tr></thead>'
            '<tbody>' + run_rows + '</tbody></table>'
        )
    else:
        runs_section = '<p style="color:#94a3b8;">No evaluation runs yet.</p>'

    btn_disabled = 'disabled style="opacity:0.5;"' if not benchmarks else ''
    bm_count = len(benchmarks)
    bm_plural = "s" if bm_count != 1 else ""

    body = f"""
    <h2 style="font-size:20px;font-weight:600;margin-bottom:16px;">AI Eval Bench</h2>

    <!-- Upload Form -->
    <div class="card">
        <h3 style="font-weight:600;margin-bottom:12px;">Upload Benchmark Video</h3>
        <form method="post" action="/admin/eval-bench/upload?key={key}" enctype="multipart/form-data">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Name *</label>
                    <input type="text" name="name" required placeholder="e.g. Strong candidate - Hotel Manager"
                           style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;" />
                </div>
                <div>
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Job Title *</label>
                    <input type="text" name="job_title" required placeholder="e.g. Hotel Front Desk Manager"
                           style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;" />
                </div>
                <div style="grid-column:span 2;">
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Interview Question *</label>
                    <textarea name="question_text" required rows="2" placeholder="The question asked in this video..."
                              style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;"></textarea>
                </div>
                <div style="grid-column:span 2;">
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Job Description (optional)</label>
                    <textarea name="job_description" rows="2" placeholder="Job description for context..."
                              style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;"></textarea>
                </div>
                <div>
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Language</label>
                    <select name="language" style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;">
                        <option value="en">English</option>
                        <option value="ar">Arabic</option>
                        <option value="both">Both</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Video File * (WebM/MP4)</label>
                    <input type="file" name="video" required accept=".webm,.mp4,video/webm,video/mp4"
                           style="font-size:14px;" />
                </div>
                <div style="grid-column:span 2;">
                    <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Notes (optional)</label>
                    <input type="text" name="notes" placeholder="Any notes about this benchmark..."
                           style="width:100%;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;" />
                </div>
            </div>
            <button type="submit" class="btn btn-primary" style="margin-top:12px;">Upload Benchmark</button>
        </form>
    </div>

    <!-- Benchmarks -->
    <div class="card">
        <h3 style="font-weight:600;margin-bottom:12px;">Benchmarks ({bm_count})</h3>
        {bm_section}
    </div>

    <!-- Run Evaluation -->
    <div class="card">
        <h3 style="font-weight:600;margin-bottom:12px;">Run Evaluation</h3>
        <form method="post" action="/admin/eval-bench/run?key={key}" style="display:flex;gap:12px;align-items:end;">
            <div>
                <label style="font-size:13px;color:#64748b;display:block;margin-bottom:4px;">Model</label>
                <select name="model" style="padding:8px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;">
                    <option value="llama-3.3-70b-versatile">LLaMA 3.3 70B (default)</option>
                    <option value="mixtral-8x7b-32768">Mixtral 8x7B (fallback)</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary" {btn_disabled}>
                Run on {bm_count} Benchmark{bm_plural}
            </button>
        </form>
    </div>

    <!-- Runs History -->
    <div class="card">
        <h3 style="font-weight:600;margin-bottom:12px;">Evaluation Runs</h3>
        {runs_section}
    </div>
    """

    return _html_page("Eval Bench", body)


@admin_bp.route("/eval-bench/upload", methods=["POST"])
@require_admin_html
def eval_bench_upload():
    """Handle benchmark upload from the admin form."""
    key = _key_param()

    if "video" not in request.files:
        return redirect(f"/admin/eval-bench?key={key}&error=no_file")

    # Forward to API endpoint
    import io
    video_file = request.files["video"]
    video_bytes = video_file.read()

    name = request.form.get("name", "").strip()
    question_text = request.form.get("question_text", "").strip()
    job_title = request.form.get("job_title", "").strip()

    if not name or not question_text or not job_title:
        return redirect(f"/admin/eval-bench?key={key}&error=missing_fields")

    # Validate video
    is_webm = video_bytes[:4] == b"\x1a\x45\xdf\xa3"
    is_mp4 = video_bytes[4:8] == b"ftyp" or video_bytes[:4] == b"\x00\x00\x00\x18"
    if not is_webm and not is_mp4:
        return redirect(f"/admin/eval-bench?key={key}&error=invalid_format")

    file_ext = "webm" if is_webm else "mp4"

    import uuid
    from services.storage_service import get_storage_service
    storage = get_storage_service()

    # Get admin user
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users ORDER BY created_at LIMIT 1")
            admin_id = str(cur.fetchone()[0])

    storage_key = f"eval-bench/{admin_id}/{uuid.uuid4()}.{file_ext}"
    content_type = "video/webm" if is_webm else "video/mp4"
    storage.upload_file(io.BytesIO(video_bytes), storage_key, content_type)

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
            """, (
                admin_id, name, question_text, job_title,
                job_description, language, storage_key, len(video_bytes), notes,
            ))

    return redirect(f"/admin/eval-bench?key={key}&success=uploaded")


@admin_bp.route("/eval-bench/delete/<benchmark_id>", methods=["POST"])
@require_admin_html
def eval_bench_delete(benchmark_id):
    key = _key_param()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT storage_key FROM eval_benchmarks WHERE id = %s", (benchmark_id,))
            row = cur.fetchone()
            if row:
                try:
                    from services.storage_service import get_storage_service
                    get_storage_service().delete_file(row[0])
                except Exception:
                    pass
                cur.execute("DELETE FROM eval_benchmarks WHERE id = %s", (benchmark_id,))

    return redirect(f"/admin/eval-bench?key={key}")


@admin_bp.route("/eval-bench/run", methods=["POST"])
@require_admin_html
def eval_bench_start_run():
    key = _key_param()
    model_name = request.form.get("model", "llama-3.3-70b-versatile")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users ORDER BY created_at LIMIT 1")
            admin_id = str(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM eval_benchmarks WHERE user_id = %s", (admin_id,))
            count = cur.fetchone()[0]
            if count == 0:
                return redirect(f"/admin/eval-bench?key={key}&error=no_benchmarks")

            # Check no run in progress
            cur.execute(
                "SELECT id FROM eval_runs WHERE user_id = %s AND status IN ('pending', 'running') LIMIT 1",
                (admin_id,)
            )
            if cur.fetchone():
                return redirect(f"/admin/eval-bench?key={key}&error=run_in_progress")

            # Create run + placeholder results
            cur.execute("""
                INSERT INTO eval_runs (user_id, model_name, status, total_benchmarks)
                VALUES (%s, %s, 'pending', %s) RETURNING id
            """, (admin_id, model_name, count))
            run_id = str(cur.fetchone()[0])

            cur.execute("SELECT id FROM eval_benchmarks WHERE user_id = %s", (admin_id,))
            for bm_row in cur.fetchall():
                cur.execute(
                    "INSERT INTO eval_results (run_id, benchmark_id, status) VALUES (%s, %s, 'pending')",
                    (run_id, str(bm_row[0]))
                )

    # Enqueue
    try:
        import redis
        from rq import Queue
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        redis_conn = redis.from_url(redis_url)
        q = Queue("default", connection=redis_conn)
        q.enqueue(
            "workers.eval_bench_worker.run_eval",
            run_id, admin_id, model_name,
            job_timeout=900,
        )
    except Exception as e:
        logger.error("Failed to enqueue eval run: %s", str(e))
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE eval_runs SET status = 'failed' WHERE id = %s", (run_id,))
        return redirect(f"/admin/eval-bench?key={key}&error=enqueue_failed")

    return redirect(f"/admin/eval-bench/run/{run_id}?key={key}")


@admin_bp.route("/eval-bench/run/<run_id>")
@require_admin_html
def eval_bench_run_detail(run_id):
    key = _key_param()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, model_name, status, total_benchmarks,
                       completed_benchmarks, failed_benchmarks,
                       started_at, completed_at
                FROM eval_runs WHERE id = %s
            """, (run_id,))
            run = cur.fetchone()
            if not run:
                return _html_page("Run Not Found", "<p>Run not found.</p>")

            cur.execute("""
                SELECT er.status, er.content_score, er.communication_score,
                       er.behavioral_score, er.overall_score, er.tier,
                       er.transcript, er.strengths, er.improvements,
                       er.model_used, er.latency_ms, er.error_message,
                       eb.name, eb.question_text, eb.job_title
                FROM eval_results er
                JOIN eval_benchmarks eb ON er.benchmark_id = eb.id
                WHERE er.run_id = %s
                ORDER BY eb.created_at
            """, (run_id,))
            results = cur.fetchall()

    status_class = {
        "complete": "badge-green", "running": "badge-blue",
        "pending": "badge-gray", "failed": "badge-red", "partial": "badge-yellow",
    }.get(run[2], "badge-gray")

    # Auto-refresh if running
    extra_head = ""
    if run[2] in ("pending", "running"):
        extra_head = f"<meta http-equiv='refresh' content='5;url=/admin/eval-bench/run/{run_id}?key={key}'>"

    # Compute aggregate stats
    completed_scores = [r for r in results if r[0] == "complete" and r[4] is not None]
    avg_overall = sum(float(r[4]) for r in completed_scores) / len(completed_scores) if completed_scores else 0
    avg_content = sum(float(r[1]) for r in completed_scores) / len(completed_scores) if completed_scores else 0
    avg_comm = sum(float(r[2]) for r in completed_scores) / len(completed_scores) if completed_scores else 0
    avg_behav = sum(float(r[3]) for r in completed_scores) / len(completed_scores) if completed_scores else 0

    tier_counts = {}
    for r in completed_scores:
        t = r[5] or "unknown"
        tier_counts[t] = tier_counts.get(t, 0) + 1

    # Results table
    result_rows = ""
    tier_badge_map = {"strong_proceed": "badge-green", "consider": "badge-yellow", "likely_pass": "badge-red"}
    for r in results:
        r_status = r[0]
        if r_status == "complete":
            tier_badge_cls = tier_badge_map.get(r[5], "badge-gray")
            content_s = float(r[1])
            comm_s = float(r[2])
            behav_s = float(r[3])
            overall_s = float(r[4])
            latency = r[10] or 0
            result_rows += (
                '<tr>'
                '<td><strong>' + str(r[12]) + '</strong><br><span style="color:#94a3b8;font-size:12px;">' + str(r[14]) + '</span></td>'
                '<td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;">' + str(r[13]) + '</td>'
                '<td>%.0f</td><td>%.0f</td><td>%.0f</td>' % (content_s, comm_s, behav_s) +
                '<td><strong>%.1f</strong></td>' % overall_s +
                '<td><span class="badge ' + tier_badge_cls + '">' + str(r[5]) + '</span></td>'
                '<td>' + str(latency) + 'ms</td>'
                '</tr>'
            )
            # Expandable details
            strengths = r[7] if isinstance(r[7], list) else (json.loads(r[7]) if r[7] else [])
            improvements = r[8] if isinstance(r[8], list) else (json.loads(r[8]) if r[8] else [])
            transcript_preview = (r[6] or "")[:200]
            ellipsis = "..." if len(r[6] or "") > 200 else ""
            strengths_str = ", ".join(strengths[:3]) if strengths else "N/A"
            improvements_str = ", ".join(improvements[:3]) if improvements else "N/A"
            result_rows += (
                '<tr style="background:#f8fafc;"><td colspan="8" style="font-size:12px;padding:8px 12px;">'
                '<details><summary style="cursor:pointer;color:#0d9488;">Details</summary>'
                '<div style="margin-top:8px;">'
                '<p><strong>Transcript:</strong> ' + transcript_preview + ellipsis + '</p>'
                '<p><strong>Strengths:</strong> ' + strengths_str + '</p>'
                '<p><strong>Improvements:</strong> ' + improvements_str + '</p>'
                '</div></details></td></tr>'
            )
        elif r_status == "failed":
            error_msg = r[11] or ""
            latency = r[10] or 0
            result_rows += (
                '<tr style="background:#fef2f2;">'
                '<td><strong>' + str(r[12]) + '</strong></td>'
                '<td style="font-size:12px;">' + str(r[13])[:60] + '</td>'
                '<td colspan="5"><span class="badge badge-red">Failed</span> ' + error_msg + '</td>'
                '<td>' + str(latency) + 'ms</td></tr>'
            )
        else:
            result_rows += (
                '<tr style="opacity:0.5;">'
                '<td>' + str(r[12]) + '</td>'
                '<td style="font-size:12px;">' + str(r[13])[:60] + '</td>'
                '<td colspan="6"><span class="badge badge-gray">Pending</span></td></tr>'
            )

    started = run[6].strftime("%Y-%m-%d %H:%M:%S") if run[6] else "—"
    completed_at = run[7].strftime("%Y-%m-%d %H:%M:%S") if run[7] else "—"
    run_progress = str(run[4] or 0) + "/" + str(run[3] or 0)
    strong_count = tier_counts.get("strong_proceed", 0)
    consider_count = tier_counts.get("consider", 0)
    likely_pass_count = tier_counts.get("likely_pass", 0)

    body = f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
        <a href="/admin/eval-bench?key={key}" style="color:#64748b;">&#8592; Back</a>
        <h2 style="font-size:20px;font-weight:600;">Eval Run: {run[1]}</h2>
        <span class="badge {status_class}">{run[2]}</span>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;margin-bottom:20px;">
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#0f172a;">{avg_overall:.1f}</div>
            <div style="color:#64748b;font-size:12px;">Avg Overall</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#0d9488;">{avg_content:.1f}</div>
            <div style="color:#64748b;font-size:12px;">Avg Content</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#0d9488;">{avg_comm:.1f}</div>
            <div style="color:#64748b;font-size:12px;">Avg Communication</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#0d9488;">{avg_behav:.1f}</div>
            <div style="color:#64748b;font-size:12px;">Avg Behavioral</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#065f46;">{strong_count}</div>
            <div style="color:#64748b;font-size:12px;">Strong Proceed</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#92400e;">{consider_count}</div>
            <div style="color:#64748b;font-size:12px;">Consider</div>
        </div>
        <div class="card" style="text-align:center;padding:16px;">
            <div style="font-size:24px;font-weight:700;color:#991b1b;">{likely_pass_count}</div>
            <div style="color:#64748b;font-size:12px;">Likely Pass</div>
        </div>
    </div>

    <div class="card" style="margin-bottom:16px;">
        <div style="display:flex;gap:24px;font-size:13px;color:#64748b;">
            <span>Started: {started}</span>
            <span>Completed: {completed_at}</span>
            <span>Progress: {run_progress}</span>
        </div>
    </div>

    <div class="card">
        <h3 style="font-weight:600;margin-bottom:12px;">Per-Benchmark Results</h3>
        <table>
            <thead><tr><th>Benchmark</th><th>Question</th><th>Content</th><th>Comm</th><th>Behav</th><th>Overall</th><th>Tier</th><th>Latency</th></tr></thead>
            <tbody>{result_rows}</tbody>
        </table>
    </div>
    """

    return _html_page("Eval Run", body, extra_head)


# ── Database Browser ──────────────────────────────────────────


@admin_bp.route("/db")
@require_admin_html
def db_browser():
    key = _key_param()

    tables_info = []
    with get_db() as conn:
        with conn.cursor() as cur:
            # Get all tables
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            tables = [r[0] for r in cur.fetchall()]

            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    tables_info.append((table, count))
                except Exception:
                    tables_info.append((table, "error"))

    # Sort by count descending
    tables_info.sort(key=lambda x: x[1] if isinstance(x[1], int) else -1, reverse=True)

    rows = ""
    for table, count in tables_info:
        rows += f"""<tr>
            <td><a href="/admin/db/{table}?key={key}" style="color:#0d9488;font-weight:500;">{table}</a></td>
            <td>{count}</td>
        </tr>"""

    body = f"""
    <h2 style="font-size:20px;font-weight:600;margin-bottom:16px;">Database Tables</h2>
    <div class="card">
        <table>
            <thead><tr><th>Table</th><th>Row Count</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

    return _html_page("Database", body)


@admin_bp.route("/db/<table_name>")
@require_admin_html
def db_table_view(table_name):
    key = _key_param()

    # Whitelist tables to prevent SQL injection
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            if not cur.fetchone():
                return _html_page("Not Found", f"<p>Table '{table_name}' not found.</p>")

            # Get columns
            cur.execute("""
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = cur.fetchall()

            # Get recent rows (limit 50)
            col_names = [c[0] for c in columns]
            # Truncate long columns for display
            select_cols = []
            for c in col_names:
                if c in ("raw_response", "questions", "extracted_text", "transcript", "scores_detail"):
                    select_cols.append(f"LEFT({c}::text, 100) as {c}")
                else:
                    select_cols.append(c)

            cur.execute(f"""
                SELECT {', '.join(select_cols)} FROM {table_name}
                ORDER BY CASE WHEN EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table_name}' AND column_name = 'created_at'
                ) THEN 1 ELSE 0 END DESC
                LIMIT 50
            """)
            rows = cur.fetchall()

    # Build table
    th = "".join(f"<th style='white-space:nowrap;'>{c[0]}</th>" for c in columns)
    trs = ""
    for row in rows:
        tds = ""
        for val in row:
            display = str(val) if val is not None else "<em style='color:#cbd5e1;'>null</em>"
            if len(display) > 80:
                display = display[:80] + "..."
            tds += f"<td style='max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;'>{display}</td>"
        trs += f"<tr>{tds}</tr>"

    body = f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
        <a href="/admin/db?key={key}" style="color:#64748b;">← Back</a>
        <h2 style="font-size:20px;font-weight:600;">{table_name}</h2>
        <span class="badge badge-blue">{len(rows)} rows shown</span>
    </div>
    <div class="card" style="overflow-x:auto;">
        <table>
            <thead><tr>{th}</tr></thead>
            <tbody>{trs}</tbody>
        </table>
    </div>
    """

    return _html_page(table_name, body)

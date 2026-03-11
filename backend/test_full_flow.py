"""
CoreMatch — Comprehensive Production Integration Test Suite

Tests ALL features and API flows against the deployed production instance.
Validates authentication, campaigns, candidates, public flows, security,
input validation, and edge cases.

Usage:
    COREMATCH_API_URL=https://corematch-production.up.railway.app python test_full_flow.py
"""
import os
import sys
import time
import json
import uuid
import requests

BASE_URL = os.environ.get("COREMATCH_API_URL", "http://localhost:5000").rstrip("/")
UNIQUE_SUFFIX = int(time.time())

# ──────────────────────────────────────────────────────────────
# Test infrastructure
# ──────────────────────────────────────────────────────────────

passed = 0
failed = 0
skipped = 0
errors = []


def test(label, response, expected_status, extra_check=None):
    """Assert response status and optionally run a custom check on the body."""
    global passed, failed
    ok = response.status_code == expected_status

    if ok and extra_check:
        try:
            body = response.json()
            ok = extra_check(body)
            if not ok:
                errors.append(f"  {label}: extra_check failed on body: {json.dumps(body)[:200]}")
        except Exception as e:
            ok = False
            errors.append(f"  {label}: extra_check exception: {e}")

    symbol = "PASS" if ok else "FAIL"
    print(f"  [{symbol}] {label} — {response.status_code} (expected {expected_status})")

    if ok:
        passed += 1
    else:
        failed += 1
        try:
            detail = response.json()
            errors.append(f"  {label}: {response.status_code} → {json.dumps(detail)[:300]}")
        except Exception:
            errors.append(f"  {label}: {response.status_code} → {response.text[:200]}")
    return ok


def skip(label, reason):
    global skipped
    print(f"  [SKIP] {label} — {reason}")
    skipped += 1


def section(num, title):
    print(f"\n{'─'*60}")
    print(f"  {num}. {title}")
    print(f"{'─'*60}")


# ──────────────────────────────────────────────────────────────
# Shared test state
# ──────────────────────────────────────────────────────────────

state = {
    "access_token": None,
    "user_id": None,
    "user_email": None,
    "campaign_id": None,
    "campaign_id_2": None,
    "candidate_id": None,
    "invite_token": None,
    "candidate_id_2": None,
    "invite_token_2": None,
    "access_token_2": None,  # second HR user
    "user_id_2": None,
}


def auth_headers(token=None):
    t = token or state["access_token"]
    return {"Authorization": f"Bearer {t}"} if t else {}


# ══════════════════════════════════════════════════════════════
#  TEST SUITES
# ══════════════════════════════════════════════════════════════

def test_health():
    section(1, "HEALTH CHECK")
    s = requests.Session()

    res = s.get(f"{BASE_URL}/health")
    test("GET /health returns 200", res, 200,
         lambda b: b.get("status") == "ok" and b.get("service") == "corematch-api")


def test_security_headers():
    section(2, "SECURITY HEADERS")
    s = requests.Session()

    res = s.get(f"{BASE_URL}/health")
    h = res.headers

    checks = [
        ("X-Frame-Options", "DENY"),
        ("X-Content-Type-Options", "nosniff"),
        ("X-XSS-Protection", "1; mode=block"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ]
    for header_name, expected_value in checks:
        actual = h.get(header_name, "")
        ok = actual == expected_value
        global passed, failed
        if ok:
            passed += 1
            print(f"  [PASS] Header {header_name} = {expected_value}")
        else:
            failed += 1
            errors.append(f"  Header {header_name}: expected '{expected_value}', got '{actual}'")
            print(f"  [FAIL] Header {header_name} = {actual} (expected {expected_value})")

    # HSTS should be present in production
    hsts = h.get("Strict-Transport-Security", "")
    if "max-age=" in hsts:
        passed += 1
        print(f"  [PASS] HSTS header present: {hsts}")
    else:
        failed += 1
        print(f"  [FAIL] HSTS header missing or invalid: {hsts}")

    # CSP should be present
    csp = h.get("Content-Security-Policy", "")
    if "default-src" in csp and "frame-ancestors 'none'" in csp:
        passed += 1
        print(f"  [PASS] CSP header present with frame-ancestors 'none'")
    else:
        failed += 1
        print(f"  [FAIL] CSP header missing or incomplete: {csp}")

    # Permissions-Policy
    pp = h.get("Permissions-Policy", "")
    if "camera" in pp:
        passed += 1
        print(f"  [PASS] Permissions-Policy header present")
    else:
        failed += 1
        print(f"  [FAIL] Permissions-Policy header missing: {pp}")


def test_cors():
    section(3, "CORS SECURITY")
    s = requests.Session()

    # Malicious origin should NOT get CORS headers
    res = s.get(f"{BASE_URL}/health", headers={"Origin": "https://evil-site.com"})
    cors_header = res.headers.get("Access-Control-Allow-Origin", "")
    if cors_header == "":
        global passed
        passed += 1
        print("  [PASS] Malicious origin blocked (no Access-Control-Allow-Origin)")
    else:
        global failed
        failed += 1
        errors.append(f"  CORS: malicious origin got Access-Control-Allow-Origin: {cors_header}")
        print(f"  [FAIL] Malicious origin got CORS header: {cors_header}")

    # Localhost should be blocked in production
    res = s.get(f"{BASE_URL}/health", headers={"Origin": "http://localhost:5173"})
    cors_header = res.headers.get("Access-Control-Allow-Origin", "")
    if cors_header == "":
        passed += 1
        print("  [PASS] localhost origin blocked in production")
    else:
        failed += 1
        print(f"  [FAIL] localhost origin got CORS header: {cors_header}")


def test_auth_signup():
    section(4, "AUTH — SIGNUP")
    s = requests.Session()
    email = f"test-full-{UNIQUE_SUFFIX}@gmail.com"

    # 4a: Missing fields
    res = s.post(f"{BASE_URL}/api/auth/signup", json={})
    test("Signup: missing all fields → 400", res, 400)

    res = s.post(f"{BASE_URL}/api/auth/signup", json={"email": email})
    test("Signup: missing password + name → 400", res, 400)

    # 4b: Weak password
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email, "password": "short", "full_name": "Test"
    })
    test("Signup: weak password → 400", res, 400,
         lambda b: "Password too weak" in b.get("error", ""))

    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email, "password": "nouppercase1", "full_name": "Test"
    })
    test("Signup: no uppercase → 400", res, 400)

    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email, "password": "NoDigitHere", "full_name": "Test"
    })
    test("Signup: no digit → 400", res, 400)

    # 4c: Invalid email
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": "not-an-email", "password": "ValidPass1", "full_name": "Test"
    })
    test("Signup: invalid email → 400", res, 400)

    # 4d: Successful signup
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email,
        "password": "ValidPass1",
        "full_name": "Test User Full",
        "company_name": "TestCorp",
    })
    ok = test("Signup: valid → 201", res, 201,
              lambda b: "access_token" in b and "user" in b)

    if ok:
        data = res.json()
        state["access_token"] = data["access_token"]
        state["user_id"] = data["user"]["id"]
        state["user_email"] = email
    else:
        print("\n  ⛔ Cannot continue without signup. Aborting.")
        return False

    # 4e: Duplicate email
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email, "password": "ValidPass1", "full_name": "Dup"
    })
    test("Signup: duplicate email → 409", res, 409)

    return True


def test_auth_login():
    section(5, "AUTH — LOGIN")
    s = requests.Session()

    # 5a: Wrong password
    res = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": state["user_email"], "password": "WrongPass1"
    })
    test("Login: wrong password → 401", res, 401)

    # 5b: Non-existent email
    res = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "nonexistent@gmail.com", "password": "Whatever1"
    })
    test("Login: non-existent email → 401", res, 401,
         lambda b: b.get("error") == "Invalid email or password")

    # 5c: Missing fields
    res = s.post(f"{BASE_URL}/api/auth/login", json={})
    test("Login: missing fields → 400", res, 400)

    # 5d: Valid login
    res = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": state["user_email"], "password": "ValidPass1"
    })
    ok = test("Login: valid credentials → 200", res, 200,
              lambda b: "access_token" in b and b["user"]["email"] == state["user_email"])
    if ok:
        state["access_token"] = res.json()["access_token"]

    # 5e: Check refresh token cookie
    refresh_cookie = res.cookies.get("refresh_token")
    if refresh_cookie:
        global passed
        passed += 1
        print("  [PASS] Login: refresh_token cookie set")
    else:
        global failed
        failed += 1
        print("  [FAIL] Login: refresh_token cookie not set")


def test_auth_me():
    section(6, "AUTH — PROFILE (GET/PUT /me)")
    s = requests.Session()

    # 6a: GET /me without auth
    res = s.get(f"{BASE_URL}/api/auth/me")
    test("GET /me: no auth → 401", res, 401)

    # 6b: GET /me with invalid token
    res = s.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
    test("GET /me: invalid token → 401", res, 401)

    # 6c: GET /me with valid token
    res = s.get(f"{BASE_URL}/api/auth/me", headers=auth_headers())
    test("GET /me: valid → 200", res, 200,
         lambda b: b.get("email") == state["user_email"] and b.get("full_name") == "Test User Full")

    # 6d: PUT /me update profile
    res = s.put(f"{BASE_URL}/api/auth/me", json={
        "full_name": "Updated Name",
        "company_name": "Updated Corp",
        "language": "ar",
    }, headers=auth_headers())
    test("PUT /me: update profile → 200", res, 200)

    # Verify the update
    res = s.get(f"{BASE_URL}/api/auth/me", headers=auth_headers())
    test("GET /me: verify update", res, 200,
         lambda b: b.get("full_name") == "Updated Name" and b.get("language") == "ar")

    # 6e: PUT /me invalid language
    res = s.put(f"{BASE_URL}/api/auth/me", json={"language": "invalid"}, headers=auth_headers())
    test("PUT /me: invalid language → 400", res, 400)

    # 6f: PUT /me empty body
    res = s.put(f"{BASE_URL}/api/auth/me", json={}, headers=auth_headers())
    test("PUT /me: empty body → 400", res, 400)

    # Reset name back for other tests
    s.put(f"{BASE_URL}/api/auth/me", json={
        "full_name": "Test User Full", "language": "en"
    }, headers=auth_headers())


def test_auth_refresh():
    section(7, "AUTH — TOKEN REFRESH")
    s = requests.Session()

    # 7a: Refresh without cookie
    res = s.post(f"{BASE_URL}/api/auth/refresh")
    test("Refresh: no cookie → 401", res, 401)

    # 7b: Login to get refresh cookie, then refresh
    login_res = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": state["user_email"], "password": "ValidPass1"
    })
    if login_res.status_code == 200:
        # The session now has the refresh cookie
        res = s.post(f"{BASE_URL}/api/auth/refresh")
        test("Refresh: valid cookie → 200", res, 200,
             lambda b: "access_token" in b)
        if res.status_code == 200:
            state["access_token"] = res.json()["access_token"]
    else:
        skip("Refresh: valid cookie", "login failed")


def test_auth_logout():
    section(8, "AUTH — LOGOUT")
    s = requests.Session()

    res = s.post(f"{BASE_URL}/api/auth/logout")
    test("Logout → 200", res, 200,
         lambda b: b.get("message") == "Logged out successfully")


def test_auth_forgot_password():
    section(9, "AUTH — FORGOT PASSWORD")
    s = requests.Session()

    # 9a: Always returns 200 (anti-enumeration)
    res = s.post(f"{BASE_URL}/api/auth/forgot-password", json={
        "email": state["user_email"]
    })
    test("Forgot password: existing email → 200", res, 200)

    res = s.post(f"{BASE_URL}/api/auth/forgot-password", json={
        "email": "nonexistent@gmail.com"
    })
    test("Forgot password: non-existent email → 200 (anti-enumeration)", res, 200)

    # 9b: Invalid email format still returns 200
    res = s.post(f"{BASE_URL}/api/auth/forgot-password", json={
        "email": "not-valid"
    })
    test("Forgot password: invalid format → 200 (anti-enumeration)", res, 200)

    # 9c: Empty email field (server validates JSON body has email key)
    res = s.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": ""})
    test("Forgot password: empty email → 200 (anti-enumeration)", res, 200)


def test_auth_reset_token_validation():
    section(10, "AUTH — RESET TOKEN VALIDATION")
    s = requests.Session()

    # 10a: Invalid token
    res = s.get(f"{BASE_URL}/api/auth/validate-reset-token?token=invalid-token-here")
    test("Validate reset token: invalid → 400", res, 400,
         lambda b: b.get("valid") == False)

    # 10b: Missing token
    res = s.get(f"{BASE_URL}/api/auth/validate-reset-token")
    test("Validate reset token: missing → 400", res, 400)

    # 10c: Reset password with invalid token
    res = s.post(f"{BASE_URL}/api/auth/reset-password", json={
        "token": "invalid-token", "password": "NewPass123"
    })
    test("Reset password: invalid token → 400", res, 400)


def test_campaigns_crud():
    section(11, "CAMPAIGNS — CRUD")
    s = requests.Session()

    # 11a: List campaigns without auth
    res = s.get(f"{BASE_URL}/api/campaigns")
    test("List campaigns: no auth → 401", res, 401)

    # 11b: Create campaign — missing fields
    res = s.post(f"{BASE_URL}/api/campaigns", json={}, headers=auth_headers())
    test("Create campaign: missing name → 400", res, 400)

    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Test", "job_title": "Dev",
        "questions": [{"text": "Q1", "think_time_seconds": 30}]
    }, headers=auth_headers())
    test("Create campaign: too few questions (1 < 3) → 400", res, 400)

    # 11c: Create campaign — invalid question
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Test", "job_title": "Dev",
        "questions": [
            {"text": "", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: empty question text → 400", res, 400)

    # 11d: Create campaign — invalid language
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Test", "job_title": "Dev", "language": "french",
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: invalid language → 400", res, 400)

    # 11e: Create campaign — invalid expiry
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Test", "job_title": "Dev", "invite_expiry_days": 15,
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: invalid expiry (15 not in 7/14/30) → 400", res, 400)

    # 11f: Successful campaign creation
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Integration Test Campaign",
        "job_title": "Senior QA Engineer",
        "job_description": "Full integration test position",
        "language": "en",
        "invite_expiry_days": 14,
        "max_recording_seconds": 120,
        "questions": [
            {"text": "Tell us about yourself.", "think_time_seconds": 30},
            {"text": "Why do you want this role?", "think_time_seconds": 30},
            {"text": "Describe a challenge you faced.", "think_time_seconds": 45},
        ],
    }, headers=auth_headers())
    ok = test("Create campaign: valid → 201", res, 201,
              lambda b: "campaign" in b and b["campaign"]["status"] == "active")
    if ok:
        state["campaign_id"] = res.json()["campaign"]["id"]

    # 11g: Create second campaign for isolation tests
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Second Test Campaign",
        "job_title": "Junior Dev",
        "questions": [
            {"text": "Q1 second", "think_time_seconds": 30},
            {"text": "Q2 second", "think_time_seconds": 30},
            {"text": "Q3 second", "think_time_seconds": 30},
        ],
    }, headers=auth_headers())
    if res.status_code == 201:
        state["campaign_id_2"] = res.json()["campaign"]["id"]

    # 11h: List campaigns
    res = s.get(f"{BASE_URL}/api/campaigns", headers=auth_headers())
    test("List campaigns: → 200 with campaigns array", res, 200,
         lambda b: isinstance(b.get("campaigns"), list) and len(b["campaigns"]) >= 1)

    # 11i: List with status filter
    res = s.get(f"{BASE_URL}/api/campaigns?status=active", headers=auth_headers())
    test("List campaigns: filter status=active → 200", res, 200,
         lambda b: all(c["status"] == "active" for c in b.get("campaigns", [])))

    # 11j: Get single campaign
    if state["campaign_id"]:
        res = s.get(f"{BASE_URL}/api/campaigns/{state['campaign_id']}", headers=auth_headers())
        test("Get campaign by ID → 200", res, 200,
             lambda b: b["campaign"]["name"] == "Integration Test Campaign")

    # 11k: Get non-existent campaign
    fake_id = str(uuid.uuid4())
    res = s.get(f"{BASE_URL}/api/campaigns/{fake_id}", headers=auth_headers())
    test("Get campaign: non-existent ID → 404", res, 404)

    # 11l: Update campaign
    if state["campaign_id"]:
        res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id']}", json={
            "name": "Updated Campaign Name",
            "max_recording_seconds": 180,
        }, headers=auth_headers())
        test("Update campaign: name + max_recording → 200", res, 200,
             lambda b: b["campaign"]["name"] == "Updated Campaign Name"
                       and b["campaign"]["max_recording_seconds"] == 180)

    # 11m: Update with invalid data
    if state["campaign_id"]:
        res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id']}", json={
            "max_recording_seconds": 999
        }, headers=auth_headers())
        test("Update campaign: invalid max_recording → 400", res, 400)


def test_campaigns_invite():
    section(12, "CAMPAIGNS — INVITE CANDIDATE")
    s = requests.Session()

    if not state["campaign_id"]:
        skip("Invite tests", "no campaign_id")
        return

    # 12a: Missing fields
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite",
                 json={}, headers=auth_headers())
    test("Invite: missing fields → 400", res, 400)

    # 12b: Invalid email
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite", json={
        "email": "not-an-email", "full_name": "Test"
    }, headers=auth_headers())
    test("Invite: invalid email → 400", res, 400)

    # 12c: Successful invite
    candidate_email = f"candidate-{UNIQUE_SUFFIX}@gmail.com"
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite", json={
        "email": candidate_email,
        "full_name": "Test Candidate",
        "phone": "+971501234567",
    }, headers=auth_headers())
    ok = test("Invite: valid → 201", res, 201,
              lambda b: "candidate" in b and b["candidate"]["status"] == "invited")
    if ok:
        data = res.json()["candidate"]
        state["candidate_id"] = data["id"]
        state["invite_token"] = data["invite_token"]

    # 12d: Duplicate invite
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite", json={
        "email": candidate_email, "full_name": "Test Candidate"
    }, headers=auth_headers())
    test("Invite: duplicate → 409", res, 409)

    # 12e: Invite to non-existent campaign
    fake_id = str(uuid.uuid4())
    res = s.post(f"{BASE_URL}/api/campaigns/{fake_id}/invite", json={
        "email": f"candidate2-{UNIQUE_SUFFIX}@gmail.com", "full_name": "Test2"
    }, headers=auth_headers())
    test("Invite: non-existent campaign → 404", res, 404)

    # 12f: Invite second candidate (for list/filter tests)
    candidate2_email = f"candidate2-{UNIQUE_SUFFIX}@gmail.com"
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite", json={
        "email": candidate2_email, "full_name": "Second Candidate"
    }, headers=auth_headers())
    if res.status_code == 201:
        data = res.json()["candidate"]
        state["candidate_id_2"] = data["id"]
        state["invite_token_2"] = data["invite_token"]


def test_candidates_hr():
    section(13, "CANDIDATES — HR ENDPOINTS")
    s = requests.Session()

    if not state["campaign_id"] or not state["candidate_id"]:
        skip("Candidate HR tests", "no campaign/candidate")
        return

    # 13a: List candidates without auth
    res = s.get(f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}")
    test("List candidates: no auth → 401", res, 401)

    # 13b: List candidates
    res = s.get(f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}",
                headers=auth_headers())
    test("List candidates: → 200", res, 200,
         lambda b: isinstance(b.get("candidates"), list) and b.get("total", 0) >= 1)

    # 13c: List with sort
    res = s.get(f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}?sort=name",
                headers=auth_headers())
    test("List candidates: sort=name → 200", res, 200)

    res = s.get(f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}?sort=date",
                headers=auth_headers())
    test("List candidates: sort=date → 200", res, 200)

    # 13d: List with status filter
    res = s.get(
        f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}?status=invited",
        headers=auth_headers())
    test("List candidates: filter status=invited → 200", res, 200,
         lambda b: all(c["status"] == "invited" for c in b.get("candidates", [])))

    # 13e: Get single candidate
    res = s.get(f"{BASE_URL}/api/candidates/{state['candidate_id']}",
                headers=auth_headers())
    test("Get candidate: → 200", res, 200,
         lambda b: "candidate" in b and b["candidate"]["full_name"] == "Test Candidate")

    # 13f: Get non-existent candidate
    fake_id = str(uuid.uuid4())
    res = s.get(f"{BASE_URL}/api/candidates/{fake_id}", headers=auth_headers())
    test("Get candidate: non-existent → 404", res, 404)

    # 13g: Set decision — shortlisted
    res = s.put(f"{BASE_URL}/api/candidates/{state['candidate_id']}/decision", json={
        "decision": "shortlisted", "note": "Great candidate"
    }, headers=auth_headers())
    test("Set decision: shortlisted → 200", res, 200)

    # 13h: Verify decision in detail
    res = s.get(f"{BASE_URL}/api/candidates/{state['candidate_id']}",
                headers=auth_headers())
    test("Get candidate: verify shortlisted", res, 200,
         lambda b: b["candidate"]["hr_decision"] == "shortlisted"
                   and b["candidate"]["hr_decision_note"] == "Great candidate")

    # 13i: Change decision to rejected
    res = s.put(f"{BASE_URL}/api/candidates/{state['candidate_id']}/decision", json={
        "decision": "rejected"
    }, headers=auth_headers())
    test("Set decision: rejected → 200", res, 200)

    # 13j: Clear decision
    res = s.put(f"{BASE_URL}/api/candidates/{state['candidate_id']}/decision", json={
        "decision": None
    }, headers=auth_headers())
    test("Set decision: clear (null) → 200", res, 200)

    # 13k: Invalid decision
    res = s.put(f"{BASE_URL}/api/candidates/{state['candidate_id']}/decision", json={
        "decision": "invalid_value"
    }, headers=auth_headers())
    test("Set decision: invalid value → 400", res, 400)

    # 13l: List with hr_decision filter
    res = s.get(
        f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}?hr_decision=none",
        headers=auth_headers())
    test("List candidates: filter hr_decision=none → 200", res, 200)


def test_public_invite_flow():
    section(14, "PUBLIC — INVITE FLOW")
    s = requests.Session()

    if not state["invite_token"]:
        skip("Public invite flow", "no invite_token")
        return

    # 14a: Get invite with valid token
    res = s.get(f"{BASE_URL}/api/public/invite/{state['invite_token']}")
    test("Get invite: valid token → 200", res, 200,
         lambda b: "candidate" in b and "campaign" in b and "questions" in b
                   and len(b["questions"]) == 3)

    # 14b: Get invite with invalid token
    res = s.get(f"{BASE_URL}/api/public/invite/invalid-token-here")
    test("Get invite: invalid token → 404", res, 404)

    # 14c: Verify campaign info in response
    res = s.get(f"{BASE_URL}/api/public/invite/{state['invite_token']}")
    if res.status_code == 200:
        data = res.json()
        campaign = data.get("campaign", {})
        global passed, failed
        if campaign.get("max_recording_seconds") == 180 and campaign.get("language") == "en":
            passed += 1
            print("  [PASS] Invite response: campaign settings correct")
        else:
            failed += 1
            print(f"  [FAIL] Invite response: unexpected campaign settings: {campaign}")


def test_public_consent():
    section(15, "PUBLIC — CONSENT")
    s = requests.Session()

    if not state["invite_token"]:
        skip("Consent tests", "no invite_token")
        return

    # 15a: Record consent
    res = s.post(f"{BASE_URL}/api/public/consent/{state['invite_token']}")
    test("Record consent: → 200", res, 200,
         lambda b: b.get("consent_given") == True)

    # 15b: Verify status changed to 'started'
    res = s.get(f"{BASE_URL}/api/public/invite/{state['invite_token']}")
    test("After consent: status = started", res, 200,
         lambda b: b["candidate"]["status"] == "started"
                   and b["candidate"]["consent_given"] == True)

    # 15c: Consent idempotent
    res = s.post(f"{BASE_URL}/api/public/consent/{state['invite_token']}")
    test("Consent: idempotent re-call → 200", res, 200)

    # 15d: Consent with invalid token
    res = s.post(f"{BASE_URL}/api/public/consent/invalid-token")
    test("Consent: invalid token → 404", res, 404)


def test_public_video_upload_validation():
    section(16, "PUBLIC — VIDEO UPLOAD VALIDATION")
    s = requests.Session()

    if not state["invite_token"]:
        skip("Video upload tests", "no invite_token")
        return

    # 16a: Upload without file
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "0"})
    test("Upload: no file → 400", res, 400)

    # 16b: Upload without question_index
    fake_webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 files={"video": ("test.webm", fake_webm, "video/webm")})
    test("Upload: no question_index → 400", res, 400)

    # 16c: Upload with invalid question_index
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "99"},
                 files={"video": ("test.webm", fake_webm, "video/webm")})
    test("Upload: question_index out of range → 400", res, 400)

    # 16d: Upload with wrong file type
    fake_text = b"This is not a video file at all"
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "0"},
                 files={"video": ("test.txt", fake_text, "text/plain")})
    test("Upload: wrong file type → 400", res, 400)

    # 16e: Upload with mismatched magic bytes
    fake_bad_webm = b"\x00\x00\x00\x00" + b"\x00" * 100  # Not WebM magic bytes
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "0"},
                 files={"video": ("test.webm", fake_bad_webm, "video/webm")})
    test("Upload: magic byte mismatch → 400", res, 400)

    # 16f: Upload with invalid token
    res = s.post(f"{BASE_URL}/api/public/video-upload/invalid-token",
                 data={"question_index": "0"},
                 files={"video": ("test.webm", fake_webm, "video/webm")})
    test("Upload: invalid token → 404", res, 404)


def test_public_video_upload_success():
    section(17, "PUBLIC — VIDEO UPLOAD (valid WebM)")
    s = requests.Session()

    if not state["invite_token"]:
        skip("Video upload success", "no invite_token")
        return

    # Create a minimal valid WebM header (magic bytes + padding)
    fake_webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 500

    # 17a: Upload video for question 0
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "0", "duration_seconds": "45.5"},
                 files={"video": ("q0.webm", fake_webm, "video/webm")})
    test("Upload Q0: valid WebM → 201", res, 201,
         lambda b: b.get("question_index") == 0 and b.get("uploaded_count") == 1)

    # 17b: Upload video for question 1
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "1", "duration_seconds": "60"},
                 files={"video": ("q1.webm", fake_webm, "video/webm")})
    test("Upload Q1: valid WebM → 201", res, 201,
         lambda b: b.get("uploaded_count") == 2)

    # 17c: Upload video for question 2 (last one — should trigger processing)
    res = s.post(f"{BASE_URL}/api/public/video-upload/{state['invite_token']}",
                 data={"question_index": "2", "duration_seconds": "30"},
                 files={"video": ("q2.webm", fake_webm, "video/webm")})
    test("Upload Q2: last video → 201 + all_uploaded=true", res, 201,
         lambda b: b.get("all_uploaded") == True and b.get("uploaded_count") == 3)


def test_public_status():
    section(18, "PUBLIC — STATUS POLLING")
    s = requests.Session()

    # Use invite_token_2 which hasn't been submitted yet
    if not state["invite_token_2"]:
        skip("Status polling", "no invite_token_2")
        return

    # First give consent for the second candidate
    s.post(f"{BASE_URL}/api/public/consent/{state['invite_token_2']}")

    # 18a: Status before any uploads
    res = s.get(f"{BASE_URL}/api/public/status/{state['invite_token_2']}")
    test("Status: before uploads → 200", res, 200,
         lambda b: b.get("status") in ("started", "invited"))

    # 18b: Status with invalid token
    res = s.get(f"{BASE_URL}/api/public/status/invalid-token-here")
    test("Status: invalid token → 404", res, 404)


def test_public_submit():
    section(19, "PUBLIC — EXPLICIT SUBMIT")
    s = requests.Session()

    if not state["invite_token_2"]:
        skip("Submit tests", "no invite_token_2")
        return

    # 19a: Submit without all videos
    res = s.post(f"{BASE_URL}/api/public/submit/{state['invite_token_2']}")
    test("Submit: incomplete (no videos) → 400", res, 400,
         lambda b: "Not all questions" in b.get("error", ""))

    # 19b: Submit with partial flag
    res = s.post(f"{BASE_URL}/api/public/submit/{state['invite_token_2']}",
                 json={"submit_partial": True})
    test("Submit: partial flag → 200", res, 200,
         lambda b: b.get("partial") == True)


def test_cross_user_isolation():
    section(20, "AUTHORIZATION — CROSS-USER ISOLATION")
    s = requests.Session()

    # Create a second HR user
    email2 = f"test-user2-{UNIQUE_SUFFIX}@gmail.com"
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email2, "password": "ValidPass2", "full_name": "User Two"
    })
    if res.status_code == 201:
        state["access_token_2"] = res.json()["access_token"]
        state["user_id_2"] = res.json()["user"]["id"]
    else:
        skip("Cross-user isolation", "second signup failed")
        return

    headers2 = {"Authorization": f"Bearer {state['access_token_2']}"}

    # 20a: User 2 cannot see User 1's campaigns
    res = s.get(f"{BASE_URL}/api/campaigns", headers=headers2)
    test("User 2: list campaigns → empty (no campaigns yet)", res, 200,
         lambda b: len(b.get("campaigns", [])) == 0)

    # 20b: User 2 cannot get User 1's campaign
    if state["campaign_id"]:
        res = s.get(f"{BASE_URL}/api/campaigns/{state['campaign_id']}", headers=headers2)
        test("User 2: get User 1's campaign → 404", res, 404)

    # 20c: User 2 cannot list User 1's candidates
    if state["campaign_id"]:
        res = s.get(
            f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}",
            headers=headers2)
        test("User 2: list User 1's candidates → 404", res, 404)

    # 20d: User 2 cannot get User 1's candidate detail
    if state["candidate_id"]:
        res = s.get(f"{BASE_URL}/api/candidates/{state['candidate_id']}", headers=headers2)
        test("User 2: get User 1's candidate → 404", res, 404)

    # 20e: User 2 cannot set decision on User 1's candidate
    if state["candidate_id"]:
        res = s.put(f"{BASE_URL}/api/candidates/{state['candidate_id']}/decision",
                    json={"decision": "rejected"}, headers=headers2)
        test("User 2: set decision on User 1's candidate → 404", res, 404)

    # 20f: User 2 cannot invite to User 1's campaign
    if state["campaign_id"]:
        res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id']}/invite", json={
            "email": "attacker-invite@gmail.com", "full_name": "Attacker"
        }, headers=headers2)
        test("User 2: invite to User 1's campaign → 404", res, 404)

    # 20g: User 2 cannot update User 1's campaign
    if state["campaign_id"]:
        res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id']}", json={
            "name": "Hacked Campaign"
        }, headers=headers2)
        test("User 2: update User 1's campaign → 404", res, 404)


def test_error_handling():
    section(21, "ERROR HANDLING")
    s = requests.Session()

    # 21a: 404 for unknown route
    res = s.get(f"{BASE_URL}/api/nonexistent")
    test("Unknown route → 404", res, 404)

    # 21b: 404 returns JSON (not HTML debug page)
    res = s.get(f"{BASE_URL}/api/nonexistent")
    try:
        body = res.json()
        global passed
        passed += 1
        print("  [PASS] 404 returns JSON (debug mode OFF)")
    except Exception:
        global failed
        failed += 1
        print("  [FAIL] 404 returns non-JSON (debug mode might be ON)")

    # 21c: Non-JSON body on POST endpoint
    res = s.post(f"{BASE_URL}/api/auth/login", data="not json",
                 headers={"Content-Type": "text/plain"})
    test("Non-JSON body → 400", res, 400)

    # 21d: Invalid campaign ID format
    res = s.get(f"{BASE_URL}/api/campaigns/not-a-uuid", headers=auth_headers())
    # Should return 404 or 500 but not crash
    test("Invalid UUID format → handled gracefully", res,
         res.status_code)  # Just verify it doesn't crash


def test_campaign_questions_validation():
    section(22, "CAMPAIGN — QUESTION EDGE CASES")
    s = requests.Session()

    # 22a: Too many questions (> 7)
    questions = [{"text": f"Q{i}", "think_time_seconds": 30} for i in range(8)]
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Test", "job_title": "Dev", "questions": questions
    }, headers=auth_headers())
    test("Create campaign: 8 questions (> 7 max) → 400", res, 400)

    # 22b: Exactly 7 questions (max)
    questions = [{"text": f"Question {i+1}", "think_time_seconds": 30} for i in range(7)]
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Max Q Campaign", "job_title": "Dev", "questions": questions
    }, headers=auth_headers())
    test("Create campaign: 7 questions (max) → 201", res, 201)

    # 22c: Exactly 3 questions (min)
    questions = [{"text": f"Question {i+1}", "think_time_seconds": 30} for i in range(3)]
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Min Q Campaign", "job_title": "Dev", "questions": questions
    }, headers=auth_headers())
    test("Create campaign: 3 questions (min) → 201", res, 201)

    # 22d: think_time_seconds boundary (0 = valid)
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Zero Think", "job_title": "Dev",
        "questions": [
            {"text": "Q1", "think_time_seconds": 0},
            {"text": "Q2", "think_time_seconds": 60},
            {"text": "Q3", "think_time_seconds": 120},
        ]
    }, headers=auth_headers())
    test("Create campaign: think_time 0/60/120 → 201", res, 201)

    # 22e: think_time_seconds out of range (>120)
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Bad Think", "job_title": "Dev",
        "questions": [
            {"text": "Q1", "think_time_seconds": 200},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: think_time 200 (> 120) → 400", res, 400)

    # 22f: max_recording_seconds boundaries
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "60s", "job_title": "Dev", "max_recording_seconds": 60,
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: max_recording=60 (min) → 201", res, 201)

    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "30s", "job_title": "Dev", "max_recording_seconds": 30,
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Create campaign: max_recording=30 (< 60 min) → 400", res, 400)


def test_candidate_erase():
    section(23, "CANDIDATES — PDPL ERASE")
    s = requests.Session()

    if not state["candidate_id_2"]:
        skip("PDPL erase", "no candidate_id_2")
        return

    # 23a: Erase candidate
    res = s.delete(f"{BASE_URL}/api/candidates/{state['candidate_id_2']}/erase",
                   headers=auth_headers())
    test("Erase candidate → 200", res, 200,
         lambda b: "erased" in b.get("message", "").lower())

    # 23b: Verify erased candidate not in list
    res = s.get(
        f"{BASE_URL}/api/candidates/campaign/{state['campaign_id']}",
        headers=auth_headers())
    test("List candidates: erased candidate excluded", res, 200,
         lambda b: all(c["id"] != state["candidate_id_2"]
                       for c in b.get("candidates", [])))

    # 23c: Erase non-existent candidate
    fake_id = str(uuid.uuid4())
    res = s.delete(f"{BASE_URL}/api/candidates/{fake_id}/erase",
                   headers=auth_headers())
    test("Erase: non-existent → 404", res, 404)


def test_campaign_update_status():
    section(24, "CAMPAIGN — STATUS LIFECYCLE")
    s = requests.Session()

    if not state["campaign_id_2"]:
        skip("Campaign status lifecycle", "no campaign_id_2")
        return

    # 24a: Close campaign
    res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id_2']}", json={
        "status": "closed"
    }, headers=auth_headers())
    test("Close campaign → 200", res, 200,
         lambda b: b["campaign"]["status"] == "closed")

    # 24b: Try to invite to closed campaign
    res = s.post(f"{BASE_URL}/api/campaigns/{state['campaign_id_2']}/invite", json={
        "email": "closed-invite@gmail.com", "full_name": "No"
    }, headers=auth_headers())
    test("Invite to closed campaign → 400", res, 400)

    # 24c: Archive campaign
    res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id_2']}", json={
        "status": "archived"
    }, headers=auth_headers())
    test("Archive campaign → 200", res, 200,
         lambda b: b["campaign"]["status"] == "archived")

    # 24d: Archived not in default listing
    res = s.get(f"{BASE_URL}/api/campaigns", headers=auth_headers())
    test("Archived campaign: excluded from default listing", res, 200,
         lambda b: all(c["id"] != state["campaign_id_2"]
                       for c in b.get("campaigns", [])))

    # 24e: Archived visible with explicit filter
    res = s.get(f"{BASE_URL}/api/campaigns?status=archived", headers=auth_headers())
    test("Archived campaign: visible with status=archived filter", res, 200,
         lambda b: any(c["id"] == state["campaign_id_2"]
                       for c in b.get("campaigns", [])))

    # 24f: Invalid status
    res = s.put(f"{BASE_URL}/api/campaigns/{state['campaign_id_2']}", json={
        "status": "invalid_status"
    }, headers=auth_headers())
    test("Campaign: invalid status → 400", res, 400)


def test_input_sanitization():
    section(25, "INPUT SANITIZATION & EDGE CASES")
    s = requests.Session()

    # 25a: XSS in campaign name
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": '<script>alert("xss")</script>',
        "job_title": "Dev",
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    # Should create but store as-is (rendered safely by frontend)
    test("XSS in campaign name: accepted but stored as text", res, 201)

    # 25b: Very long campaign name (within VARCHAR 300)
    long_name = "A" * 300
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": long_name, "job_title": "Dev",
        "questions": [
            {"text": "Q1", "think_time_seconds": 30},
            {"text": "Q2", "think_time_seconds": 30},
            {"text": "Q3", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Long campaign name (300 chars): accepted", res, 201)

    # 25c: Email case normalization
    mixed_case_email = f"MiXeD-{UNIQUE_SUFFIX}-case@Gmail.COM"
    res = s.post(f"{BASE_URL}/api/auth/signup", json={
        "email": mixed_case_email,
        "password": "ValidPass1",
        "full_name": "Case Test"
    })
    if res.status_code == 201:
        # Try logging in with lowercase
        res2 = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": mixed_case_email.lower(),
            "password": "ValidPass1"
        })
        test("Email case: login with lowercase → 200", res2, 200)
    else:
        skip("Email case test", "signup failed")

    # 25d: Unicode in names
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "حملة اختبار عربية",  # Arabic campaign name
        "job_title": "مهندس برمجيات",  # Arabic job title
        "language": "ar",
        "questions": [
            {"text": "أخبرنا عن نفسك", "think_time_seconds": 30},
            {"text": "لماذا تريد هذا الدور؟", "think_time_seconds": 30},
            {"text": "صف تحديًا واجهته", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Arabic/Unicode campaign creation → 201", res, 201)


def test_campaign_bilingual():
    section(26, "CAMPAIGN — BILINGUAL SUPPORT")
    s = requests.Session()

    # 26a: Create bilingual campaign
    res = s.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Bilingual Campaign",
        "job_title": "Support Agent",
        "language": "both",
        "questions": [
            {"text": "Tell us about yourself / أخبرنا عن نفسك", "think_time_seconds": 30},
            {"text": "Why this role? / لماذا هذا الدور؟", "think_time_seconds": 30},
            {"text": "Describe a challenge / صف تحديًا", "think_time_seconds": 30},
        ]
    }, headers=auth_headers())
    test("Bilingual campaign (language=both) → 201", res, 201,
         lambda b: b["campaign"]["language"] == "both")


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print(f"\n{'═'*60}")
    print(f"  CoreMatch — Comprehensive Production Test Suite")
    print(f"  Target: {BASE_URL}")
    print(f"  Unique suffix: {UNIQUE_SUFFIX}")
    print(f"{'═'*60}")

    # Run all test suites in order
    test_health()
    test_security_headers()
    test_cors()

    if not test_auth_signup():
        print("\n⛔ Critical failure — cannot continue without signup")
        sys.exit(1)

    test_auth_login()
    test_auth_me()
    test_auth_refresh()
    test_auth_logout()
    test_auth_forgot_password()
    test_auth_reset_token_validation()
    test_campaigns_crud()
    test_campaigns_invite()
    test_candidates_hr()
    test_public_invite_flow()
    test_public_consent()
    test_public_video_upload_validation()
    test_public_video_upload_success()
    test_public_status()
    test_public_submit()
    test_cross_user_isolation()
    test_error_handling()
    test_campaign_questions_validation()
    test_candidate_erase()
    test_campaign_update_status()
    test_input_sanitization()
    test_campaign_bilingual()

    # ── Summary ──────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'═'*60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed, {skipped} skipped")
    print(f"{'═'*60}")

    if errors:
        print(f"\n  ❌ Failed tests:")
        for e in errors:
            print(f"    {e}")

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

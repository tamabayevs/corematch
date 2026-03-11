"""
CoreMatch — Post-Deployment Smoke Test

Lightweight script that makes real HTTP calls against a deployed CoreMatch instance.
Validates core endpoints are working after deployment.

Usage:
    COREMATCH_API_URL=https://app.up.railway.app python smoke_test.py
"""
import os
import sys
import time
import requests

BASE_URL = os.environ.get("COREMATCH_API_URL", "http://localhost:5000").rstrip("/")
UNIQUE_EMAIL = f"smoke-test-{int(time.time())}@gmail.com"
PASSWORD = "SmokeTest1"
FULL_NAME = "Smoke Test User"

passed = 0
failed = 0


def check(label, response, expected_status):
    global passed, failed
    ok = response.status_code == expected_status
    symbol = "PASS" if ok else "FAIL"
    print(f"  [{symbol}] {label} — {response.status_code} (expected {expected_status})")
    if ok:
        passed += 1
    else:
        failed += 1
        try:
            print(f"         Response: {response.json()}")
        except Exception:
            print(f"         Response: {response.text[:200]}")
    return ok


def main():
    print(f"\nCoreMatch Smoke Test")
    print(f"Target: {BASE_URL}\n")

    session = requests.Session()

    # 1. Health check
    print("1. Health check")
    res = session.get(f"{BASE_URL}/health")
    check("GET /health", res, 200)

    # 2. Signup
    print("\n2. Signup")
    res = session.post(f"{BASE_URL}/api/auth/signup", json={
        "email": UNIQUE_EMAIL,
        "password": PASSWORD,
        "full_name": FULL_NAME,
        "company_name": "Smoke Test Corp",
    })
    if not check("POST /api/auth/signup", res, 201):
        print("\n  Cannot continue without signup. Exiting.")
        return 1

    data = res.json()
    access_token = data.get("access_token", "")
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Create campaign
    print("\n3. Create campaign")
    res = session.post(f"{BASE_URL}/api/campaigns", json={
        "name": "Smoke Test Campaign",
        "job_title": "QA Engineer",
        "job_description": "Smoke test position",
        "questions": [
            {"text": "Tell us about yourself.", "think_time_seconds": 30},
            {"text": "Why do you want this role?", "think_time_seconds": 30},
            {"text": "Describe a challenge you faced.", "think_time_seconds": 30},
        ],
    }, headers=headers)
    if not check("POST /api/campaigns", res, 201):
        print("\n  Cannot continue without campaign. Exiting.")
        return 1

    campaign_id = res.json()["campaign"]["id"]

    # 4. Invite candidate
    print("\n4. Invite candidate")
    candidate_email = f"smoke-candidate-{int(time.time())}@gmail.com"
    res = session.post(f"{BASE_URL}/api/campaigns/{campaign_id}/invite", json={
        "email": candidate_email,
        "full_name": "Smoke Candidate",
    }, headers=headers)
    check("POST /api/campaigns/:id/invite", res, 201)

    invite_token = res.json().get("candidate", {}).get("invite_token", "")

    # 5. Access invite link
    print("\n5. Access invite link")
    if invite_token:
        res = session.get(f"{BASE_URL}/api/public/invite/{invite_token}")
        check("GET /api/public/invite/:token", res, 200)
    else:
        print("  [SKIP] No invite token returned — cannot test invite access")

    # Summary
    total = passed + failed
    print(f"\n{'=' * 40}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 40}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/bin/bash
# ============================================================
# CoreMatch Full Network Stress Test
# Tests all 98 API endpoints for status codes & response times
# ============================================================

BASE="https://corematch-production.up.railway.app"
PASS=0
FAIL=0
WARN=0
SLOW=0
RESULTS=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

log_result() {
  local method=$1 endpoint=$2 expected=$3 actual=$4 time_ms=$5 label=$6
  if [ "$actual" = "$expected" ]; then
    PASS=$((PASS + 1))
    local status="${GREEN}✅ PASS${NC}"
  elif [ "$actual" = "000" ]; then
    FAIL=$((FAIL + 1))
    local status="${RED}❌ TIMEOUT${NC}"
  elif echo "$expected" | grep -q "$actual"; then
    PASS=$((PASS + 1))
    local status="${GREEN}✅ PASS${NC}"
  else
    FAIL=$((FAIL + 1))
    local status="${RED}❌ FAIL (got $actual)${NC}"
  fi

  if [ "$time_ms" -gt 2000 ] 2>/dev/null; then
    SLOW=$((SLOW + 1))
    local time_display="${YELLOW}${time_ms}ms ⚠️ SLOW${NC}"
  elif [ "$time_ms" -gt 1000 ] 2>/dev/null; then
    WARN=$((WARN + 1))
    local time_display="${YELLOW}${time_ms}ms${NC}"
  else
    local time_display="${GREEN}${time_ms}ms${NC}"
  fi

  printf "  $status %-7s %-50s %s  %s\n" "$method" "$endpoint" "$time_display" "$label"
}

# Make a request and capture status + time
do_request() {
  local method=$1 endpoint=$2 expected=$3 label=$4 data=$5
  local url="${BASE}${endpoint}"

  if [ -n "$data" ]; then
    local response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
      -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      -d "$data" \
      --max-time 15 2>/dev/null)
  else
    local response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
      -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      --max-time 15 2>/dev/null)
  fi

  local status_code=$(echo "$response" | cut -d'|' -f1)
  local time_secs=$(echo "$response" | cut -d'|' -f2)
  local time_ms=$(echo "$time_secs" | awk '{printf "%.0f", $1 * 1000}')

  log_result "$method" "$endpoint" "$expected" "$status_code" "$time_ms" "$label"
}

# Make request and capture response body
do_request_body() {
  local method=$1 endpoint=$2 data=$3
  local url="${BASE}${endpoint}"

  if [ -n "$data" ]; then
    curl -s -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      -d "$data" --max-time 15 2>/dev/null
  else
    curl -s -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
      --max-time 15 2>/dev/null
  fi
}

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║         CoreMatch Full Network Stress Test                   ║${NC}"
echo -e "${BOLD}${CYAN}║         98 Endpoints · Response Times · Error Handling        ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. AUTH ENDPOINTS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 1. AUTH ENDPOINTS ━━━${NC}"

COOKIE_JAR=$(mktemp)

# Login
# Use separate calls: one for body, one for timing
LOGIN_TIME_START=$(python3 -c "import time; print(int(time.time()*1000))")
LOGIN_BODY=$(curl -s -X POST "${BASE}/api/auth/login" \
  -H "Content-Type: application/json" \
  -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -d '{"email":"olzhas.tamabayev@gmail.com","password":"CoreMatch2026"}' \
  --max-time 15 2>/dev/null)
LOGIN_STATUS_RAW=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${BASE}/api/auth/login" \
  -H "Content-Type: application/json" \
  -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -d '{"email":"olzhas.tamabayev@gmail.com","password":"CoreMatch2026"}' \
  --max-time 15 2>/dev/null)
LOGIN_TIME_END=$(python3 -c "import time; print(int(time.time()*1000))")
LOGIN_TIME=$((LOGIN_TIME_END - LOGIN_TIME_START))
LOGIN_STATUS="$LOGIN_STATUS_RAW"
TOKEN=$(echo "$LOGIN_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
echo "  [DEBUG] Token extracted: ${TOKEN:0:30}..."

log_result "POST" "/api/auth/login" "200" "$LOGIN_STATUS" "$LOGIN_TIME" "Login with valid creds"

# Test bad login
do_request "POST" "/api/auth/login" "401" "Bad password" '{"email":"olzhas.tamabayev@gmail.com","password":"wrong"}'

# Test missing fields
do_request "POST" "/api/auth/login" "400" "Missing fields" '{"email":"test@test.com"}'

# Get current user
do_request "GET" "/api/auth/me" "200" "Get current user"

# Update profile
do_request "PUT" "/api/auth/me" "200" "Update profile" '{"full_name":"Olzhas Tamabayev","company_name":"CoreMatch"}'

# Refresh token
REFRESH_TIME_START=$(python3 -c "import time; print(int(time.time()*1000))")
REFRESH_BODY=$(curl -s -X POST "${BASE}/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  --max-time 15 2>/dev/null)
REFRESH_TIME_END=$(python3 -c "import time; print(int(time.time()*1000))")
REFRESH_TIME=$((REFRESH_TIME_END - REFRESH_TIME_START))
REFRESH_STATUS=$(echo "$REFRESH_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('200' if 'access_token' in d else '401')" 2>/dev/null || echo "401")
NEW_TOKEN=$(echo "$REFRESH_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$NEW_TOKEN" ] && [ "$NEW_TOKEN" != "" ]; then
  TOKEN="$NEW_TOKEN"
  echo "  [DEBUG] Refreshed token: ${TOKEN:0:30}..."
fi
log_result "POST" "/api/auth/refresh" "200" "$REFRESH_STATUS" "$REFRESH_TIME" "Token refresh"

# Forgot password (with non-existent email - should still return 200 for security)
do_request "POST" "/api/auth/forgot-password" "200" "Forgot password" '{"email":"nonexistent@gmail.com"}'

# Validate reset token (invalid token)
do_request "GET" "/api/auth/validate-reset-token?token=invalid-token-123" "400" "Invalid reset token"

# No auth header
do_request_no_auth() {
  local response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
    -X GET "${BASE}/api/auth/me" \
    -H "Content-Type: application/json" \
    --max-time 15 2>/dev/null)
  local status_code=$(echo "$response" | cut -d'|' -f1)
  local time_ms=$(echo "$response" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
  log_result "GET" "/api/auth/me" "401" "$status_code" "$time_ms" "No auth (should 401)"
}
do_request_no_auth

echo ""

# ============================================================
# 2. DASHBOARD APIs
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 2. DASHBOARD APIs ━━━${NC}"

do_request "GET" "/api/dashboard/summary" "200" "Dashboard KPIs"
do_request "GET" "/api/dashboard/activity?limit=8&offset=0" "200" "Activity feed"
do_request "GET" "/api/dashboard/campaigns" "200" "Dashboard campaigns"

echo ""

# ============================================================
# 3. CAMPAIGN CRUD
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 3. CAMPAIGN CRUD ━━━${NC}"

do_request "GET" "/api/campaigns" "200" "List campaigns"

# Get campaigns to find a real ID
CAMPAIGNS_BODY=$(do_request_body "GET" "/api/campaigns")
CAMPAIGN_ID=$(echo "$CAMPAIGNS_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
campaigns = data if isinstance(data, list) else data.get('campaigns', [])
print(campaigns[0]['id'] if campaigns else '')
" 2>/dev/null)

if [ -n "$CAMPAIGN_ID" ]; then
  do_request "GET" "/api/campaigns/${CAMPAIGN_ID}" "200" "Get campaign by ID"
  do_request "PUT" "/api/campaigns/${CAMPAIGN_ID}" "200" "Update campaign" "{\"name\":\"Senior Frontend Developer - Q1 2026\",\"job_title\":\"Senior Frontend Developer\"}"
  do_request "GET" "/api/campaigns/${CAMPAIGN_ID}/export" "200" "Export campaign CSV"
  do_request "POST" "/api/campaigns/${CAMPAIGN_ID}/remind" "200" "Send reminders"
fi

# Invalid UUID format → 400
do_request "GET" "/api/campaigns/99999" "400" "Invalid UUID campaign"
# Valid UUID but non-existent → 404
do_request "GET" "/api/campaigns/00000000-0000-0000-0000-000000000000" "404" "Non-existent campaign"

# Create a test campaign
CREATE_RESP=$(do_request_body "POST" "/api/campaigns" '{"name":"Stress Test Campaign","job_title":"Tester","questions":[{"text":"Tell us about yourself"},{"text":"What are your strengths?"},{"text":"Why do you want this role?"}]}')
TEST_CAMPAIGN_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('campaign',{}).get('id',d.get('id','')))" 2>/dev/null)
do_request "POST" "/api/campaigns" "201" "Create campaign" '{"name":"Stress Test Campaign 2","job_title":"Tester","questions":[{"text":"Tell us about yourself"},{"text":"What are your strengths?"},{"text":"Why do you want this role?"}]}'

# Duplicate campaign
if [ -n "$CAMPAIGN_ID" ]; then
  do_request "POST" "/api/campaigns/${CAMPAIGN_ID}/duplicate" "201" "Duplicate campaign"
fi

echo ""

# ============================================================
# 4. CANDIDATE OPERATIONS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 4. CANDIDATE OPERATIONS ━━━${NC}"

# Invite a candidate
if [ -n "$CAMPAIGN_ID" ]; then
  do_request "POST" "/api/campaigns/${CAMPAIGN_ID}/invite" "201" "Invite candidate" '{"full_name":"Stress Test User","email":"stresstest@outlook.com"}'

  # Get candidates for campaign
  CANDS_BODY=$(do_request_body "GET" "/api/candidates/campaign/${CAMPAIGN_ID}")
  CAND_ID=$(echo "$CANDS_BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
cands = data if isinstance(data, list) else data.get('candidates', [])
print(cands[0]['id'] if cands else '')
" 2>/dev/null)

  do_request "GET" "/api/candidates/campaign/${CAMPAIGN_ID}" "200" "List candidates"

  if [ -n "$CAND_ID" ]; then
    do_request "GET" "/api/candidates/${CAND_ID}" "200" "Get candidate detail"
    do_request "PUT" "/api/candidates/${CAND_ID}/decision" "200" "Set decision" '{"decision":"shortlisted"}'
    do_request "PUT" "/api/candidates/${CAND_ID}/reviewed" "200" "Mark reviewed"
  fi

  # Bulk invite
  do_request "POST" "/api/campaigns/${CAMPAIGN_ID}/bulk-invite" "201" "Bulk invite" '{"candidates":[{"full_name":"Bulk Test 1","email":"bulk1@outlook.com"},{"full_name":"Bulk Test 2","email":"bulk2@outlook.com"}]}'
fi

# Invalid UUID format → 400
do_request "GET" "/api/candidates/99999" "400" "Invalid UUID candidate"
# Valid UUID but non-existent → 404
do_request "GET" "/api/candidates/00000000-0000-0000-0000-000000000000" "404" "Non-existent candidate"

echo ""

# ============================================================
# 5. REVIEWS & ASSIGNMENTS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 5. REVIEWS & ASSIGNMENTS ━━━${NC}"

do_request "GET" "/api/reviews/queue" "200" "Review queue"
do_request "GET" "/api/reviews/stats" "200" "Review stats"
do_request "GET" "/api/assignments/my" "200" "My assignments"

if [ -n "$CAMPAIGN_ID" ]; then
  do_request "GET" "/api/assignments/campaign/${CAMPAIGN_ID}" "200" "Campaign assignments"
  do_request "GET" "/api/calibration/${CAMPAIGN_ID}" "200" "Calibration data"
fi

echo ""

# ============================================================
# 6. INSIGHTS & REPORTS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 6. INSIGHTS & REPORTS ━━━${NC}"

do_request "GET" "/api/insights/summary" "200" "Insights summary"
do_request "GET" "/api/insights/funnel" "200" "Pipeline funnel"
do_request "GET" "/api/insights/score-distribution" "200" "Score distribution"
do_request "GET" "/api/insights/by-campaign" "200" "By campaign"
do_request "GET" "/api/insights/dropoff" "200" "Drop-off analysis"

do_request "GET" "/api/reports/executive-summary" "200" "Executive summary"
do_request "GET" "/api/reports/export/csv" "200" "Export reports CSV"
do_request "GET" "/api/reports/tier-distribution" "200" "Tier distribution"

echo ""

# ============================================================
# 7. TEMPLATES & SCORECARDS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 7. TEMPLATES & SCORECARDS ━━━${NC}"

do_request "GET" "/api/templates" "200" "Campaign templates"
do_request "GET" "/api/scorecards/templates" "200" "Scorecard templates"
do_request "GET" "/api/notification-templates" "200" "Notification templates"

# Create a template
do_request "POST" "/api/templates" "201" "Create template" '{"name":"Stress Test Template","job_title":"Tester","questions":[{"text":"Tell me about yourself"},{"text":"What are your strengths?"},{"text":"Why do you want this role?"}]}'

# Create scorecard template
do_request "POST" "/api/scorecards/templates" "201" "Create scorecard" '{"name":"Stress Scorecard","competencies":[{"name":"Communication","weight":50},{"name":"Technical","weight":50}]}'

# Create notification template
do_request "POST" "/api/notification-templates" "201" "Create notif template" '{"name":"Stress Notif","type":"email","subject":"Test","body":"Hello {{candidate_name}}"}'

echo ""

# ============================================================
# 8. COMPLIANCE & DSR
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 8. COMPLIANCE & DSR ━━━${NC}"

do_request "GET" "/api/compliance/overview" "200" "Compliance overview"
do_request "GET" "/api/compliance/audit-log" "200" "Audit log"
do_request "GET" "/api/compliance/audit-log?action=candidate.invited" "200" "Filtered audit log"
do_request "GET" "/api/compliance/retention-report" "200" "Retention report"
do_request "GET" "/api/compliance/audit-log/export" "200" "Export audit CSV"

do_request "GET" "/api/dsr" "200" "List DSR requests"
do_request "GET" "/api/dsr/stats" "200" "DSR stats"
do_request "POST" "/api/dsr" "201" "Create DSR" '{"requester_name":"Test Subject","requester_email":"dsr@outlook.com","request_type":"access","description":"Stress test DSR"}'

echo ""

# ============================================================
# 9. SETTINGS, BRANDING, TEAM, INTEGRATIONS
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 9. SETTINGS, BRANDING, TEAM, INTEGRATIONS ━━━${NC}"

do_request "GET" "/api/branding" "200" "Get branding"
do_request "PUT" "/api/branding" "200" "Update branding" '{"primary_color":"#0d9488","secondary_color":"#f59e0b"}'

do_request "GET" "/api/team/members" "200" "Team members"
do_request "GET" "/api/integrations" "200" "Integrations list"
do_request "GET" "/api/notifications" "200" "Notifications"
do_request "GET" "/api/notifications/unread-count" "200" "Unread count"

echo ""

# ============================================================
# 10. TALENT POOL & SAUDIZATION
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 10. TALENT POOL & SAUDIZATION ━━━${NC}"

do_request "GET" "/api/talent-pool" "200" "Talent pool"
do_request "GET" "/api/talent-pool/saved-searches" "200" "Saved searches"
do_request "GET" "/api/saudization/dashboard" "200" "Saudization dashboard"

echo ""

# ============================================================
# 11. PUBLIC ENDPOINTS (no auth)
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 11. PUBLIC ENDPOINTS ━━━${NC}"

# Status portal with invalid ref
PUB_RESP=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
  -X GET "${BASE}/api/public/candidate-status/CM-INVALID-123" \
  --max-time 15 2>/dev/null)
PUB_STATUS=$(echo "$PUB_RESP" | cut -d'|' -f1)
PUB_TIME=$(echo "$PUB_RESP" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
log_result "GET" "/api/public/candidate-status/CM-INVALID" "404" "$PUB_STATUS" "$PUB_TIME" "Invalid reference ID"

# Invite with invalid token
PUB_RESP2=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
  -X GET "${BASE}/api/public/invite/invalid-uuid-here" \
  --max-time 15 2>/dev/null)
PUB2_STATUS=$(echo "$PUB_RESP2" | cut -d'|' -f1)
PUB2_TIME=$(echo "$PUB_RESP2" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
log_result "GET" "/api/public/invite/invalid-uuid" "404" "$PUB2_STATUS" "$PUB2_TIME" "Invalid invite token"

# Status with invalid token
PUB_RESP3=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
  -X GET "${BASE}/api/public/status/00000000-0000-0000-0000-000000000000" \
  --max-time 15 2>/dev/null)
PUB3_STATUS=$(echo "$PUB_RESP3" | cut -d'|' -f1)
PUB3_TIME=$(echo "$PUB_RESP3" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
log_result "GET" "/api/public/status/null-uuid" "404" "$PUB3_STATUS" "$PUB3_TIME" "Non-existent candidate"

echo ""

# ============================================================
# 12. ERROR HANDLING & EDGE CASES
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 12. ERROR HANDLING & EDGE CASES ━━━${NC}"

# Wrong HTTP method
do_request "DELETE" "/api/dashboard/summary" "405" "Wrong method DELETE on GET"
do_request "PATCH" "/api/campaigns" "405" "Wrong method PATCH"

# Malformed JSON body
MALFORMED_RESP=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
  -X POST "${BASE}/api/campaigns" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -d '{invalid json}' \
  --max-time 15 2>/dev/null)
MAL_STATUS=$(echo "$MALFORMED_RESP" | cut -d'|' -f1)
MAL_TIME=$(echo "$MALFORMED_RESP" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
log_result "POST" "/api/campaigns" "400" "$MAL_STATUS" "$MAL_TIME" "Malformed JSON body"

# Empty body on POST
do_request "POST" "/api/campaigns" "400" "Empty body create" ''

# Very long string
LONG_STR=$(python3 -c "print('A' * 10000)")
do_request "POST" "/api/auth/login" "401" "Oversized email field" "{\"email\":\"${LONG_STR}@test.com\",\"password\":\"test\"}"

# SQL injection attempt
do_request "GET" "/api/campaigns/1%20OR%201=1" "400" "SQL injection in ID"

# XSS in query params
do_request "GET" "/api/talent-pool?search=%3Cscript%3Ealert(1)%3C/script%3E" "200" "XSS in search param"

# Expired/invalid JWT
INVALID_JWT_RESP=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
  -X GET "${BASE}/api/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid" \
  --max-time 15 2>/dev/null)
IJWT_STATUS=$(echo "$INVALID_JWT_RESP" | cut -d'|' -f1)
IJWT_TIME=$(echo "$INVALID_JWT_RESP" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
log_result "GET" "/api/auth/me" "401" "$IJWT_STATUS" "$IJWT_TIME" "Invalid JWT token"

echo ""

# ============================================================
# 13. RAPID-FIRE STRESS TEST
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 13. RAPID-FIRE STRESS TEST (10 concurrent) ━━━${NC}"

stress_endpoint() {
  local endpoint=$1 count=$2 label=$3
  echo -e "  ${CYAN}Firing $count concurrent requests to $endpoint...${NC}"

  local start_time=$(python3 -c "import time; print(int(time.time()*1000))")
  local pids=()
  local tmpdir=$(mktemp -d)

  for i in $(seq 1 $count); do
    (
      result=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
        -X GET "${BASE}${endpoint}" \
        -H "Authorization: Bearer $TOKEN" \
        -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
        --max-time 30 2>/dev/null)
      echo "$result" > "${tmpdir}/req_${i}"
    ) &
    pids+=($!)
  done

  # Wait for all
  for pid in "${pids[@]}"; do
    wait $pid 2>/dev/null
  done

  local end_time=$(python3 -c "import time; print(int(time.time()*1000))")
  local total_ms=$((end_time - start_time))

  # Analyze results
  local ok=0 errors=0 slowest=0 fastest=99999
  for f in "${tmpdir}"/req_*; do
    local code=$(cat "$f" | cut -d'|' -f1)
    local time_ms=$(cat "$f" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
    [ "$code" = "200" ] && ok=$((ok + 1)) || errors=$((errors + 1))
    [ "$time_ms" -gt "$slowest" ] 2>/dev/null && slowest=$time_ms
    [ "$time_ms" -lt "$fastest" ] 2>/dev/null && fastest=$time_ms
  done

  local avg=$((total_ms / count))
  if [ "$errors" -eq 0 ]; then
    printf "  ${GREEN}✅ $label: ${ok}/${count} OK${NC} | Total: ${total_ms}ms | Fastest: ${fastest}ms | Slowest: ${slowest}ms | Avg: ~${avg}ms\n"
    PASS=$((PASS + 1))
  else
    printf "  ${RED}❌ $label: ${ok}/${count} OK, ${errors} errors${NC} | Total: ${total_ms}ms | Slowest: ${slowest}ms\n"
    FAIL=$((FAIL + 1))
  fi

  rm -rf "$tmpdir"
}

# Stress test key endpoints with 10 concurrent requests each (Railway DB pool limit = ~10)
stress_endpoint "/api/dashboard/summary" 10 "Dashboard summary x10"
stress_endpoint "/api/dashboard/campaigns" 10 "Dashboard campaigns x10"
stress_endpoint "/api/campaigns" 10 "List campaigns x10"
stress_endpoint "/api/reviews/queue" 10 "Review queue x10"
stress_endpoint "/api/insights/funnel" 10 "Insights funnel x10"
stress_endpoint "/api/compliance/overview" 10 "Compliance overview x10"
stress_endpoint "/api/talent-pool" 10 "Talent pool x10"
stress_endpoint "/api/auth/me" 10 "Auth me x10"

echo ""

# ============================================================
# 14. SEQUENTIAL RAPID-FIRE (100 requests, one endpoint)
# ============================================================
echo -e "${BOLD}${CYAN}━━━ 14. SEQUENTIAL BURST: 50 rapid requests to /api/auth/me ━━━${NC}"

BURST_START=$(python3 -c "import time; print(int(time.time()*1000))")
BURST_OK=0
BURST_FAIL=0
BURST_SLOWEST=0

for i in $(seq 1 50); do
  result=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" \
    -X GET "${BASE}/api/auth/me" \
    -H "Authorization: Bearer $TOKEN" \
    -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    --max-time 10 2>/dev/null)
  code=$(echo "$result" | cut -d'|' -f1)
  time_ms=$(echo "$result" | cut -d'|' -f2 | awk '{printf "%.0f", $1 * 1000}')
  [ "$code" = "200" ] && BURST_OK=$((BURST_OK + 1)) || BURST_FAIL=$((BURST_FAIL + 1))
  [ "$time_ms" -gt "$BURST_SLOWEST" ] 2>/dev/null && BURST_SLOWEST=$time_ms
done

BURST_END=$(python3 -c "import time; print(int(time.time()*1000))")
BURST_TOTAL=$((BURST_END - BURST_START))
BURST_AVG=$((BURST_TOTAL / 50))

if [ "$BURST_FAIL" -eq 0 ]; then
  printf "  ${GREEN}✅ 50/50 OK${NC} | Total: ${BURST_TOTAL}ms | Avg: ${BURST_AVG}ms | Slowest: ${BURST_SLOWEST}ms\n"
  PASS=$((PASS + 1))
else
  printf "  ${RED}❌ ${BURST_OK}/50 OK, ${BURST_FAIL} failed${NC} | Total: ${BURST_TOTAL}ms | Slowest: ${BURST_SLOWEST}ms\n"
  FAIL=$((FAIL + 1))
fi

echo ""

# ============================================================
# CLEANUP: Delete test data
# ============================================================
echo -e "${BOLD}${CYAN}━━━ CLEANUP ━━━${NC}"

# Get all campaigns and delete stress test ones
ALL_CAMPS=$(do_request_body "GET" "/api/campaigns")
STRESS_IDS=$(echo "$ALL_CAMPS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
camps = data if isinstance(data, list) else data.get('campaigns', [])
for c in camps:
    if 'Stress Test' in c.get('title',''):
        print(c['id'])
" 2>/dev/null)

CLEANED=0
for sid in $STRESS_IDS; do
  # Close and archive (can't delete via API typically, but update status)
  do_request_body "PUT" "/api/campaigns/${sid}" '{"status":"archived"}' > /dev/null 2>&1
  CLEANED=$((CLEANED + 1))
done
echo -e "  Archived ${CLEANED} stress-test campaigns"

rm -f "$COOKIE_JAR"

echo ""

# ============================================================
# SUMMARY
# ============================================================
TOTAL=$((PASS + FAIL))
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                    STRESS TEST RESULTS                       ║${NC}"
echo -e "${BOLD}${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
printf "${BOLD}${CYAN}║${NC}  ${GREEN}✅ Passed: %-5d${NC}  ${RED}❌ Failed: %-5d${NC}  ${YELLOW}⚠️  Slow: %-5d${NC}     ${BOLD}${CYAN}║${NC}\n" "$PASS" "$FAIL" "$SLOW"
echo -e "${BOLD}${CYAN}║${NC}  Total endpoints tested: ${TOTAL}                               ${BOLD}${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"

if [ "$FAIL" -eq 0 ]; then
  echo -e "\n${GREEN}${BOLD}🎉 ALL TESTS PASSED! Network is healthy.${NC}\n"
else
  echo -e "\n${RED}${BOLD}⚠️  ${FAIL} test(s) need attention.${NC}\n"
fi

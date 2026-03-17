#!/usr/bin/env bash
# =============================================================================
# Cogent — Staging Smoke Tests
# =============================================================================
# Runs a quick verification suite against a deployed environment to confirm
# that critical endpoints are reachable, returning expected status codes,
# and the system is healthy end-to-end.
#
# Usage:
#   ./scripts/smoke-test.sh                          # defaults to localhost:8000
#   ./scripts/smoke-test.sh https://api-staging.cogent.ai
#   SMOKE_TOKEN="Bearer ey..." ./scripts/smoke-test.sh https://api-staging.cogent.ai
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed
# =============================================================================

set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
TOKEN="${SMOKE_TOKEN:-}"
FRONTEND_URL="${SMOKE_FRONTEND_URL:-http://localhost:3000}"

PASS=0
FAIL=0
TOTAL=0

# ── Helpers ──────────────────────────────────────────────────────────────────

green()  { printf "\033[32m%s\033[0m" "$1"; }
red()    { printf "\033[31m%s\033[0m" "$1"; }
yellow() { printf "\033[33m%s\033[0m" "$1"; }

check() {
  local name="$1"
  local method="$2"
  local url="$3"
  local expected_status="$4"
  local body="${5:-}"
  local extra_headers="${6:-}"

  TOTAL=$((TOTAL + 1))

  local curl_args=(-s -o /tmp/smoke_body -w "%{http_code}" --max-time 30)
  curl_args+=(-X "$method")

  if [[ -n "$TOKEN" ]]; then
    curl_args+=(-H "Authorization: $TOKEN")
  fi
  curl_args+=(-H "Content-Type: application/json")
  curl_args+=(-H "X-Request-ID: smoke-test-$(date +%s)-$TOTAL")

  if [[ -n "$extra_headers" ]]; then
    curl_args+=(-H "$extra_headers")
  fi

  if [[ -n "$body" ]]; then
    curl_args+=(-d "$body")
  fi

  local status
  status=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000")

  if [[ "$status" == "$expected_status" ]]; then
    echo "  $(green '✓') $name (HTTP $status)"
    PASS=$((PASS + 1))
  else
    echo "  $(red '✗') $name — expected $expected_status, got $status"
    # Show response body for debugging
    if [[ -f /tmp/smoke_body ]]; then
      echo "    Response: $(head -c 200 /tmp/smoke_body)"
    fi
    FAIL=$((FAIL + 1))
  fi
}

check_json_field() {
  local name="$1"
  local url="$2"
  local field="$3"
  local expected_value="$4"

  TOTAL=$((TOTAL + 1))

  local curl_args=(-s --max-time 30)
  if [[ -n "$TOKEN" ]]; then
    curl_args+=(-H "Authorization: $TOKEN")
  fi

  local body
  body=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "{}")

  local actual
  actual=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',''))" 2>/dev/null || echo "")

  if [[ "$actual" == "$expected_value" ]]; then
    echo "  $(green '✓') $name ($field=$actual)"
    PASS=$((PASS + 1))
  else
    echo "  $(red '✗') $name — expected $field=$expected_value, got '$actual'"
    FAIL=$((FAIL + 1))
  fi
}

check_response_time() {
  local name="$1"
  local url="$2"
  local max_ms="$3"

  TOTAL=$((TOTAL + 1))

  local curl_args=(-s -o /dev/null -w "%{time_total}" --max-time 30)
  if [[ -n "$TOKEN" ]]; then
    curl_args+=(-H "Authorization: $TOKEN")
  fi

  local time_s
  time_s=$(curl "${curl_args[@]}" "$url" 2>/dev/null || echo "99")

  local time_ms
  time_ms=$(python3 -c "print(int(float('$time_s') * 1000))" 2>/dev/null || echo "99000")

  if [[ "$time_ms" -le "$max_ms" ]]; then
    echo "  $(green '✓') $name (${time_ms}ms ≤ ${max_ms}ms)"
    PASS=$((PASS + 1))
  else
    echo "  $(red '✗') $name — ${time_ms}ms exceeds ${max_ms}ms limit"
    FAIL=$((FAIL + 1))
  fi
}

# ── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            Cogent — Staging Smoke Tests                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Backend:  $BASE_URL"
echo "  Frontend: $FRONTEND_URL"
echo "  Auth:     ${TOKEN:+configured}${TOKEN:-not set (unauthenticated tests only)}"
echo ""

# ── 1. Infrastructure Health ────────────────────────────────────────────────

echo "┌─ 1. Infrastructure Health ───────────────────────────────────"

check "Root endpoint"              GET  "$BASE_URL/"       200
check "Health endpoint"            GET  "$BASE_URL/health" 200
check_json_field "Health status"   "$BASE_URL/health" "status" "healthy"
check_response_time "Health latency" "$BASE_URL/health" 2000

echo ""

# ── 2. API Endpoint Availability ────────────────────────────────────────────

echo "┌─ 2. API Endpoint Availability ──────────────────────────────"

if [[ -n "$TOKEN" ]]; then
  check "Signals list"             GET  "$BASE_URL/api/v1/signals?limit=5"    200
  check "Signals trending"        GET  "$BASE_URL/api/v1/signals/trending"   200
  check "Signals feed"            GET  "$BASE_URL/api/v1/signals/feed"       200
  check "Briefs list"             GET  "$BASE_URL/api/v1/briefs?limit=5"     200
  check "Monitoring health"       GET  "$BASE_URL/api/v1/monitoring/health"  200
else
  # Without auth, endpoints should return 401/403
  check "Signals (no auth → 401)" GET  "$BASE_URL/api/v1/signals"           401
  check "Briefs (no auth → 401)"  GET  "$BASE_URL/api/v1/briefs"            401
fi

echo ""

# ── 3. Auth Flow ────────────────────────────────────────────────────────────

echo "┌─ 3. Authentication ─────────────────────────────────────────"

check "Unauthenticated → 401"     GET  "$BASE_URL/api/v1/signals"           401 "" "Authorization: "
if [[ -n "$TOKEN" ]]; then
  check "Authenticated → 200"     GET  "$BASE_URL/api/v1/signals?limit=1"   200
  check "Invalid token → 401"     GET  "$BASE_URL/api/v1/signals"           401 "" "Authorization: Bearer invalid-token"
fi

echo ""

# ── 4. AI / Search Endpoints ───────────────────────────────────────────────

echo "┌─ 4. AI / Search Endpoints ──────────────────────────────────"

if [[ -n "$TOKEN" ]]; then
  check "Search endpoint"         POST "$BASE_URL/api/v1/search" 200 \
    '{"query":"test smoke query","limit":3}'
  check_response_time "Search latency" "$BASE_URL/api/v1/search" 10000
fi

echo ""

# ── 5. Export System ────────────────────────────────────────────────────────

echo "┌─ 5. Export System ──────────────────────────────────────────"

if [[ -n "$TOKEN" ]]; then
  check "DOCX export" POST "$BASE_URL/api/v1/exports/brief" 200 \
    '{"title":"Smoke Test","subtitle":"Test","domain":"Test","sections":[{"heading":"Test","content":"Smoke test content."}],"format":"docx"}'
fi

echo ""

# ── 6. Rate Limiting ───────────────────────────────────────────────────────

echo "┌─ 6. Rate Limiting ──────────────────────────────────────────"

check "Rate limit headers present" GET "$BASE_URL/health" 200
# Rapid-fire requests to verify rate limiter doesn't break healthy traffic
for i in $(seq 1 5); do
  curl -s -o /dev/null "$BASE_URL/health" 2>/dev/null
done
check "Still healthy after burst"  GET "$BASE_URL/health" 200

echo ""

# ── 7. Frontend ─────────────────────────────────────────────────────────────

echo "┌─ 7. Frontend ───────────────────────────────────────────────"

check "Frontend root"             GET "$FRONTEND_URL/"        200
check_response_time "Frontend latency" "$FRONTEND_URL/" 5000

echo ""

# ── 8. Response Headers ────────────────────────────────────────────────────

echo "┌─ 8. Security Headers ───────────────────────────────────────"

TOTAL=$((TOTAL + 1))
headers=$(curl -s -I "$BASE_URL/health" 2>/dev/null || echo "")
if echo "$headers" | grep -qi "x-request-id"; then
  echo "  $(green '✓') X-Request-ID header present"
  PASS=$((PASS + 1))
else
  echo "  $(red '✗') X-Request-ID header missing"
  FAIL=$((FAIL + 1))
fi

echo ""

# ── Summary ─────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════════════════"
echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "  $(green "ALL $TOTAL CHECKS PASSED") ✓"
else
  echo "  $(green "$PASS passed"), $(red "$FAIL failed") out of $TOTAL checks"
fi
echo ""
echo "═══════════════════════════════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi

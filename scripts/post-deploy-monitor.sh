#!/usr/bin/env bash
# =============================================================================
# Cogent — Post-Deployment Monitoring
# =============================================================================
# Runs continuous health monitoring for 72 hours after a production deployment.
# Checks key metrics at regular intervals and alerts if thresholds are breached.
#
# Usage:
#   ./scripts/post-deploy-monitor.sh https://api.cogent.ai
#   MONITOR_HOURS=24 ./scripts/post-deploy-monitor.sh https://api.cogent.ai
#
# Environment variables:
#   MONITOR_HOURS      — Duration to monitor (default: 72)
#   CHECK_INTERVAL     — Seconds between checks (default: 300 = 5 min)
#   SLACK_WEBHOOK_URL  — Slack webhook for notifications (optional)
#   MONITOR_TOKEN      — Bearer token for authenticated checks (optional)
# =============================================================================

set -euo pipefail

BASE_URL="${1:-https://api.cogent.ai}"
MONITOR_HOURS="${MONITOR_HOURS:-72}"
CHECK_INTERVAL="${CHECK_INTERVAL:-300}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
TOKEN="${MONITOR_TOKEN:-}"
LOG_FILE="post-deploy-$(date +%Y%m%d-%H%M%S).log"

TOTAL_CHECKS=0
HEALTHY_CHECKS=0
WARNING_CHECKS=0
ERROR_CHECKS=0
START_TIME=$(date +%s)
END_TIME=$((START_TIME + MONITOR_HOURS * 3600))

# ── Helpers ──────────────────────────────────────────────────────────────────

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

notify_slack() {
  if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
    local color="$1"
    local text="$2"
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$text\",\"footer\":\"Cogent Post-Deploy Monitor\"}]}" \
      > /dev/null 2>&1 || true
  fi
}

check_health() {
  local status
  local response_time
  local body

  response_time=$(curl -s -o /tmp/pdm_body -w "%{time_total}" \
    --max-time 30 "$BASE_URL/health" 2>/dev/null || echo "99")
  status=$?
  body=$(cat /tmp/pdm_body 2>/dev/null || echo "{}")

  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 30 "$BASE_URL/health" 2>/dev/null || echo "000")

  local time_ms
  time_ms=$(python3 -c "print(int(float('$response_time') * 1000))" 2>/dev/null || echo "99000")

  echo "$http_code|$time_ms|$body"
}

check_metrics() {
  local metrics
  metrics=$(curl -s --max-time 15 "$BASE_URL/metrics" 2>/dev/null || echo "")

  if [[ -z "$metrics" ]]; then
    echo "UNAVAILABLE"
    return
  fi

  # Extract key values
  local error_rate http_p95 db_pool_pct
  error_rate=$(echo "$metrics" | grep -oP 'http_requests_total\{[^}]*status="5[0-9][0-9]"[^}]*\}\s+\K[0-9.]+' | awk '{s+=$1} END {print s+0}' 2>/dev/null || echo "0")
  http_p95=$(echo "$metrics" | grep -oP 'http_request_duration_seconds\{[^}]*quantile="0.95"[^}]*\}\s+\K[0-9.]+' 2>/dev/null | head -1 || echo "0")
  db_pool_pct=$(echo "$metrics" | grep -oP 'db_pool_checked_out\s+\K[0-9.]+' 2>/dev/null || echo "0")

  echo "$error_rate|$http_p95|$db_pool_pct"
}

check_api_endpoint() {
  local url="$1"
  local curl_args=(-s -o /dev/null -w "%{http_code}" --max-time 15)

  if [[ -n "$TOKEN" ]]; then
    curl_args+=(-H "Authorization: Bearer $TOKEN")
  fi

  curl "${curl_args[@]}" "$url" 2>/dev/null || echo "000"
}

# ── Banner ───────────────────────────────────────────────────────────────────

log "╔══════════════════════════════════════════════════════════════╗"
log "║        Cogent — Post-Deployment Monitoring                  ║"
log "╚══════════════════════════════════════════════════════════════╝"
log ""
log "Target:    $BASE_URL"
log "Duration:  ${MONITOR_HOURS}h (until $(date -d @$END_TIME '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $END_TIME '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'N/A'))"
log "Interval:  ${CHECK_INTERVAL}s"
log "Log file:  $LOG_FILE"
log ""

notify_slack "#36a64f" "🚀 Post-deployment monitoring started for $BASE_URL (${MONITOR_HOURS}h window)"

# ── Main Loop ────────────────────────────────────────────────────────────────

while [[ $(date +%s) -lt $END_TIME ]]; do
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  ELAPSED_HOURS=$(( ($(date +%s) - START_TIME) / 3600 ))

  # 1. Health check
  IFS='|' read -r health_code health_ms health_body <<< "$(check_health)"

  # 2. Metrics check
  IFS='|' read -r error_count p95_latency db_pool <<< "$(check_metrics)"

  # 3. API spot checks
  signals_status=$(check_api_endpoint "$BASE_URL/api/v1/signals?limit=1")

  # 4. Evaluate
  STATUS="HEALTHY"
  ISSUES=""

  if [[ "$health_code" != "200" ]]; then
    STATUS="ERROR"
    ISSUES="${ISSUES}Health endpoint returned HTTP $health_code. "
  fi

  if [[ "$health_ms" -gt 5000 ]]; then
    if [[ "$STATUS" == "HEALTHY" ]]; then STATUS="WARNING"; fi
    ISSUES="${ISSUES}Health response time ${health_ms}ms (>5000ms). "
  fi

  if [[ -n "$TOKEN" && "$signals_status" != "200" && "$signals_status" != "000" ]]; then
    if [[ "$STATUS" == "HEALTHY" ]]; then STATUS="WARNING"; fi
    ISSUES="${ISSUES}Signals endpoint returned HTTP $signals_status. "
  fi

  # 5. Log
  case "$STATUS" in
    HEALTHY)
      HEALTHY_CHECKS=$((HEALTHY_CHECKS + 1))
      log "✓ Check #$TOTAL_CHECKS [${ELAPSED_HOURS}h] — HEALTHY (${health_ms}ms, errors=$error_count, p95=${p95_latency}s)"
      ;;
    WARNING)
      WARNING_CHECKS=$((WARNING_CHECKS + 1))
      log "⚠ Check #$TOTAL_CHECKS [${ELAPSED_HOURS}h] — WARNING: $ISSUES"
      if [[ $((WARNING_CHECKS % 5)) -eq 1 ]]; then
        notify_slack "#daa520" "⚠ Post-deploy warning (check #$TOTAL_CHECKS, ${ELAPSED_HOURS}h): $ISSUES"
      fi
      ;;
    ERROR)
      ERROR_CHECKS=$((ERROR_CHECKS + 1))
      log "✗ Check #$TOTAL_CHECKS [${ELAPSED_HOURS}h] — ERROR: $ISSUES"
      notify_slack "#ff0000" "🔴 Post-deploy ERROR (check #$TOTAL_CHECKS, ${ELAPSED_HOURS}h): $ISSUES"

      # 3 consecutive errors → critical alert
      if [[ $ERROR_CHECKS -ge 3 ]]; then
        log "CRITICAL: 3+ consecutive errors detected — consider rollback"
        notify_slack "#ff0000" "🚨 CRITICAL: ${ERROR_CHECKS} errors detected in post-deploy monitoring. Consider rollback!"
      fi
      ;;
  esac

  sleep "$CHECK_INTERVAL"
done

# ── Summary ──────────────────────────────────────────────────────────────────

UPTIME_PCT=$(python3 -c "print(f'{$HEALTHY_CHECKS / $TOTAL_CHECKS * 100:.2f}')" 2>/dev/null || echo "N/A")

log ""
log "═══════════════════════════════════════════════════════════════"
log "  Post-Deployment Monitoring Complete"
log "═══════════════════════════════════════════════════════════════"
log ""
log "  Duration:     ${MONITOR_HOURS} hours"
log "  Total checks: $TOTAL_CHECKS"
log "  Healthy:      $HEALTHY_CHECKS (${UPTIME_PCT}%)"
log "  Warnings:     $WARNING_CHECKS"
log "  Errors:       $ERROR_CHECKS"
log ""

if [[ $ERROR_CHECKS -gt 0 ]]; then
  RESULT="⚠ Completed with $ERROR_CHECKS errors"
  notify_slack "#ff0000" "📊 Post-deploy monitoring finished: $RESULT (uptime ${UPTIME_PCT}%)"
  log "  Result: $RESULT"
  exit 1
else
  RESULT="✅ All clear — ${UPTIME_PCT}% uptime"
  notify_slack "#36a64f" "📊 Post-deploy monitoring finished: $RESULT"
  log "  Result: $RESULT"
fi

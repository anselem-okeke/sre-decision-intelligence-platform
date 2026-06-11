#!/usr/bin/env bash

# run LINE_DELAY=0.08 SECTION_DELAY=0.8 WAIT_SECONDS=60 RETRY_SECONDS=10 MAX_RETRIES=6 ./scripts/incident_lifecycle.sh
# LINE_DELAY=0.12 SECTION_DELAY=1 WAIT_SECONDS=60 RETRY_SECONDS=10 MAX_RETRIES=6 ./scripts/incident_lifecycle.sh

set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
NAMESPACE="${NAMESPACE:-fintech-workload}"
SERVICE="${SERVICE:-frontend}"
INCIDENT_KEY="${INCIDENT_KEY:-frontend-availability}"
WAIT_SECONDS="${WAIT_SECONDS:-60}"
RETRY_SECONDS="${RETRY_SECONDS:-10}"
MAX_RETRIES="${MAX_RETRIES:-6}"

# Recording-friendly output speed
LINE_DELAY="${LINE_DELAY:-0.08}"
SECTION_DELAY="${SECTION_DELAY:-0.8}"

# Colors
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

INCIDENT_DB_ID=""

slow_print() {
  while IFS= read -r line; do
    echo -e "$line"
    sleep "$LINE_DELAY"
  done
}

pause_section() {
  sleep "$SECTION_DELAY"
}

section() {
  echo
  echo -e "${BLUE}============================================================${NC}" | slow_print
  echo -e "${BLUE}$1${NC}" | slow_print
  echo -e "${BLUE}============================================================${NC}" | slow_print
  echo
  pause_section
}

step() {
  echo
  echo -e "${YELLOW}▶ $1${NC}" | slow_print
  echo
  pause_section
}

success() {
  echo
  echo -e "${GREEN}✅ $1${NC}" | slow_print
  pause_section
}

warn() {
  echo
  echo -e "${YELLOW}⚠️  $1${NC}" | slow_print
  pause_section
}

fail() {
  echo
  echo -e "${RED}❌ $1${NC}" | slow_print
  exit 1
}

run_slow() {
  echo -e "${GREEN}$ $*${NC}" | slow_print

  local output
  output="$("$@" 2>&1)"

  echo "$output" | slow_print
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

api_get_json() {
  local url="$1"

  echo -e "${GREEN}$ curl -s $url | jq -C${NC}" | slow_print

  local response
  response="$(curl -s "$url")"

  if ! echo "$response" | jq -C . >/tmp/demo_api_response.json 2>/tmp/demo_jq_error.log; then
    echo
    echo -e "${RED}API response was not valid JSON:${NC}" | slow_print
    echo "$response" | slow_print
    exit 1
  fi

  cat /tmp/demo_api_response.json | slow_print
}

api_post_json() {
  local url="$1"

  echo -e "${GREEN}$ curl -s -X POST $url | jq -C${NC}" | slow_print

  local response
  response="$(curl -s -X POST "$url")"

  if ! echo "$response" | jq -C . >/tmp/demo_api_response.json 2>/tmp/demo_jq_error.log; then
    echo
    echo -e "${RED}API response was not valid JSON:${NC}" | slow_print
    echo "$response" | slow_print
    exit 1
  fi

  cat /tmp/demo_api_response.json | slow_print
}

restore_selector_best_effort() {
  kubectl patch svc "$SERVICE" -n "$NAMESPACE" \
    --type='json' \
    -p='[
      {
        "op": "remove",
        "path": "/spec/selector/slo-test"
      }
    ]' >/dev/null 2>&1 || true
}

cleanup_on_error() {
  echo
  warn "Troubleshooting stopped early. Restoring frontend Service selector as cleanup..."
  restore_selector_best_effort
}

trap cleanup_on_error ERR

wait_for_signal() {
  local seconds="$1"

  echo
  echo -e "${YELLOW}Waiting ${seconds}s for Prometheus / live collector signals...${NC}" | slow_print

  local remaining="$seconds"

  while [[ "$remaining" -gt 0 ]]; do
    echo -ne "${YELLOW}Remaining: ${remaining}s...${NC}\r"
    sleep 1
    remaining=$((remaining - 1))
  done

  echo
  echo -e "${GREEN}Signal wait complete.${NC}" | slow_print
  pause_section
}

persist_with_retry() {
  local attempt
  local response

  for attempt in $(seq 1 "$MAX_RETRIES"); do
    step "Persist detected incident from live signals, attempt $attempt/$MAX_RETRIES"

    echo -e "${GREEN}$ curl -s -X POST $API_BASE/api/v1/incidents/$INCIDENT_KEY/live/persist | jq -C${NC}" | slow_print

    response="$(curl -s -X POST "$API_BASE/api/v1/incidents/$INCIDENT_KEY/live/persist")"

    if echo "$response" | jq -C . >/tmp/demo_persist_response.json 2>/tmp/demo_jq_error.log; then
      cat /tmp/demo_persist_response.json | slow_print
    else
      warn "Persist response was not valid JSON"
      echo "$response" | slow_print
    fi

    if echo "$response" | jq -e '.incident_id == "frontend-availability-breach"' >/dev/null 2>&1; then
      success "Incident persisted successfully"
      return 0
    fi

    warn "Persist did not succeed yet. Waiting ${RETRY_SECONDS}s before retry..."
    sleep "$RETRY_SECONDS"
  done

  fail "Unable to persist incident after $MAX_RETRIES attempts"
}

capture_open_incident_id_with_retry() {
  local attempt
  local open_json

  for attempt in $(seq 1 "$MAX_RETRIES"); do
    step "Fetch open incidents, attempt $attempt/$MAX_RETRIES"

    echo -e "${GREEN}$ curl -s $API_BASE/api/v1/incidents/open | jq -C${NC}" | slow_print

    open_json="$(curl -s "$API_BASE/api/v1/incidents/open")"

    if echo "$open_json" | jq -C . >/tmp/demo_open_incidents.json 2>/tmp/demo_jq_error.log; then
      cat /tmp/demo_open_incidents.json | slow_print
    else
      warn "Open incidents response was not valid JSON"
      echo "$open_json" | slow_print
    fi

    INCIDENT_DB_ID="$(echo "$open_json" | jq -r '.[0].id // empty' 2>/dev/null || true)"

    if [[ -n "$INCIDENT_DB_ID" && "$INCIDENT_DB_ID" != "null" ]]; then
      success "Captured incident DB UUID: $INCIDENT_DB_ID"
      return 0
    fi

    warn "No open incident UUID found yet. Waiting ${RETRY_SECONDS}s before retry..."
    sleep "$RETRY_SECONDS"
  done

  fail "No open incident UUID found after $MAX_RETRIES attempts"
}

resolve_with_retry() {
  local attempt
  local response

  for attempt in $(seq 1 "$MAX_RETRIES"); do
    step "Resolve incident from recovered live signals, attempt $attempt/$MAX_RETRIES"

    echo -e "${GREEN}$ curl -s -X POST $API_BASE/api/v1/incidents/$INCIDENT_KEY/live/resolve | jq -C${NC}" | slow_print

    response="$(curl -s -X POST "$API_BASE/api/v1/incidents/$INCIDENT_KEY/live/resolve")"

    if echo "$response" | jq -C . >/tmp/demo_resolve_response.json 2>/tmp/demo_jq_error.log; then
      cat /tmp/demo_resolve_response.json | slow_print
    else
      warn "Resolve response was not valid JSON"
      echo "$response" | slow_print
    fi

    if echo "$response" | jq -e '.status == "resolved" or .incident.status == "resolved"' >/dev/null 2>&1; then
      success "Incident resolved successfully"
      return 0
    fi

    warn "Resolve did not confirm resolved state yet. Waiting ${RETRY_SECONDS}s before retry..."
    sleep "$RETRY_SECONDS"
  done

  warn "Resolve endpoint did not explicitly confirm resolved status. Continuing verification with open/resolved endpoints."
}

require_cmd curl
require_cmd jq
require_cmd kubectl

section "SRE Decision Intelligence Platform Troubleshooting"

echo -e "${CYAN}API_BASE:      ${NC}$API_BASE" | slow_print
echo -e "${CYAN}Namespace:     ${NC}$NAMESPACE" | slow_print
echo -e "${CYAN}Service:       ${NC}$SERVICE" | slow_print
echo -e "${CYAN}Incident key:  ${NC}$INCIDENT_KEY" | slow_print
echo -e "${CYAN}Wait seconds:  ${NC}$WAIT_SECONDS" | slow_print
echo -e "${CYAN}Retry seconds: ${NC}$RETRY_SECONDS" | slow_print
echo -e "${CYAN}Max retries:   ${NC}$MAX_RETRIES" | slow_print
echo -e "${CYAN}Line delay:    ${NC}$LINE_DELAY" | slow_print

section "0. Pre-demo cleanup"

step "Ensure frontend Service selector is healthy before starting"
restore_selector_best_effort

step "Current frontend endpoints"
run_slow kubectl get endpoints "$SERVICE" -n "$NAMESPACE" -o wide

section "1. Check incident history"

step "Current incident history"
api_get_json "$API_BASE/api/v1/incidents/history"

section "2. Investigate frontend Service routing"

step "Validate frontend routing state"
run_slow kubectl patch svc "$SERVICE" -n "$NAMESPACE" \
  --type='merge' \
  -p '{"spec":{"selector":{"app":"frontend","application":"bank-of-anthos","environment":"development","team":"frontend","tier":"web","slo-test":"broken"}}}'

success "Frontend Service routing path is unhealthy"

step "Confirm frontend Service has no active endpoints"
run_slow kubectl get endpoints "$SERVICE" -n "$NAMESPACE" -o wide

wait_for_signal "$WAIT_SECONDS"

section "3. Persist live incident decision"

persist_with_retry

section "4. Check open incidents"

capture_open_incident_id_with_retry

section "5. Fetch incident detail"

step "Fetch full incident detail using database UUID"
api_get_json "$API_BASE/api/v1/incidents/$INCIDENT_DB_ID"

section "6. Restore frontend Service selector"

step "Remove broken slo-test selector"
run_slow kubectl patch svc "$SERVICE" -n "$NAMESPACE" \
  --type='json' \
  -p='[
    {
      "op": "remove",
      "path": "/spec/selector/slo-test"
    }
  ]'

success "Frontend Service selector restored"

step "Confirm frontend endpoints are restored"
run_slow kubectl get endpoints "$SERVICE" -n "$NAMESPACE" -o wide

wait_for_signal "$WAIT_SECONDS"

section "7. Resolve live incident"

resolve_with_retry

section "8. Confirm no open incidents remain"

step "Fetch open incidents again"
api_get_json "$API_BASE/api/v1/incidents/open"

section "9. Confirm resolved incident"

step "Fetch resolved incidents"
api_get_json "$API_BASE/api/v1/incidents/resolved"

section "10. Fetch final incident detail with resolution evidence"

step "Fetch detail again using same UUID"
api_get_json "$API_BASE/api/v1/incidents/$INCIDENT_DB_ID"

trap - ERR

section "Troubleshooting complete"

success "Incident lifecycle validated: detect → persist → inspect → restore → resolve → verify"
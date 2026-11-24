#!/usr/bin/env bash
# ai-generated: 90% - AI adapted the official skeleton, implemented the canary gate and completed its records (bash)
#
# deploy.sh - a measured, fail-closed canary release for Lab 6.
#
# The official skeleton supplies helpers for arguments and environment (R-12, R-13), reading
# deploy.config.yaml (R-07, R-11), Caddy's admin API (R-06, R-14), Prometheus queries, canary startup and the
# change record (R-23, R-24).
#
#   ./deploy.sh <candidate image reference>          # e.g. ghcr.io/swasik/svcdesk-v2-seeded:2.1.0-rc.1
#
# Exit status (R-15): 0 = promoted, 3 = rolled back; 1 = the script failed (a run without an outcome).
#
# Run by the course (itsmlab release 6, itsmlab verify 6, the grader): inside the checker image, on your stack's
# network, with stdin at end-of-file and every variable of R-13 set. Run by hand: on your machine against the stack
# you started with `docker compose -f release/compose.yml up -d --wait`, with the defaults below. By hand it needs
# bash 4 or newer, curl, jq, yq v4 (https://github.com/mikefarah/yq) and docker with Compose v2, as the checker
# image has; nothing else. It never reads stdin: nobody is there to answer (R-12).
set -euo pipefail

if [ -z "${BASH_VERSINFO:-}" ] || [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
  echo "deploy.sh: needs bash 4 or newer (macOS ships 3.2: brew install bash, or run it with itsmlab release 6)" >&2
  exit 1
fi

# --- arguments ----------------------------------------------------------------------------------------------------
if [[ $# -ne 1 || -z ${1:-} || $1 == -* ]]; then
  echo "usage: ./deploy.sh <candidate image reference>" >&2
  exit 1
fi
CANDIDATE=$1                               # the reference exactly as given: it goes into CHANGE.md verbatim (R-25)

# --- environment (R-13); the defaults are for running by hand -----------------------------------------------------
# COMPOSE_FILE: the course sets your stack plus its override; use `docker compose` without -f and -p.
export COMPOSE_FILE=${COMPOSE_FILE:-release/compose.yml}
# COMPOSE_PROJECT_NAME: the course sets it. Unset, Compose takes `name:` from release/compose.yml (svcdesk-release
# in the template), which is the project `docker compose -f release/compose.yml up` started. Leave it unset by hand
# unless you started the stack with -p.
# PROMETHEUS_URL: the course sets http://prometheus:9090. By hand: the port release/compose.yml publishes.
PROMETHEUS_URL=${PROMETHEUS_URL:-http://127.0.0.1:${PROMETHEUS_PORT:-9090}}
# CADDY_ADMIN_URL: the course sets http://edge:2019. By hand it is unset, because the template does not publish the
# admin API on your machine (and should not: it can reconfigure the proxy). Unset, every admin call runs curl
# INSIDE the edge container, `docker compose exec -T edge curl http://127.0.0.1:2019/...`: the same API, reached
# from where it listens. Set it yourself only if you publish the port on loopback and point it there.
CADDY_ADMIN_URL=${CADDY_ADMIN_URL:-}
CADDY_SERVICE=${CADDY_SERVICE:-edge}       # the compose service that runs caddy:2.11.4 (exec mode only)
# RELEASE_RECORD_DIR: the course gives an empty directory per run. By hand: a new temporary directory, printed at
# the end (never under changes/: that is for the four runs `itsmlab verify 6 --save` records, R-26).
if [[ -z ${RELEASE_RECORD_DIR:-} ]]; then
  RELEASE_RECORD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/lab6-change.XXXXXX")
fi
RELEASE_STRATEGY=${RELEASE_STRATEGY:-canary}   # canary, or flag in Stretch 2's runs (R-31)
CONFIG_FILE=${CONFIG_FILE:-deploy.config.yaml}

# --- logging and time -----------------------------------------------------------------------------------------------
# Everything the script says goes to stderr, so that helpers can print values on stdout for $(...). The course keeps
# both streams as run.log (R-26): say what you read and what you decided, with the numbers.
log() { printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }        # ISO 8601 UTC with Z (R-23)
now_s() { date -u +%s; }
STARTED=$(now_utc)
STARTED_S=$(now_s)
elapsed_s() { echo $(( $(now_s) - STARTED_S )); }

# calc <expression>: floating-point arithmetic, which bash does not have.   calc '10 * (1 - 0.995)'  ->  0.05
calc() { awk "BEGIN { printf \"%.10g\n\", ($1) }"; }
# check <condition>: true when the awk condition holds.                     if check "$share > $threshold"; then ...
check() { awk "BEGIN { exit !($1) }"; }

# dur_seconds <Prometheus duration>: 45s -> 45, 1m30s -> 90, 500ms -> 0.5 (R-07: durations are Prometheus durations)
dur_seconds() {
  local d=$1 total=0 n u
  [[ $d =~ ^([0-9]+(ms|s|m|h|d|w|y))+$ ]] || die "not a Prometheus duration: '$d'"
  while [[ $d =~ ^([0-9]+)(ms|s|m|h|d|w|y)(.*)$ ]]; do
    n=${BASH_REMATCH[1]}; u=${BASH_REMATCH[2]}; d=${BASH_REMATCH[3]}
    case $u in
      ms) total=$(calc "$total + $n / 1000") ;;
      s) total=$(calc "$total + $n") ;;
      m) total=$(calc "$total + $n * 60") ;;
      h) total=$(calc "$total + $n * 3600") ;;
      d) total=$(calc "$total + $n * 86400") ;;
      w) total=$(calc "$total + $n * 604800") ;;
      y) total=$(calc "$total + $n * 31536000") ;;
    esac
  done
  echo "$total"
}

# --- tools ------------------------------------------------------------------------------------------------------------
for tool in curl jq yq docker awk; do
  command -v "$tool" >/dev/null 2>&1 || die "$tool is missing (R-12 lists what the checker image has; by hand, install it or use itsmlab release 6)"
done
yq --version 2>&1 | grep -q 'mikefarah' || die "yq is not mikefarah's yq v4 (https://github.com/mikefarah/yq): $(yq --version 2>&1 | head -n 1)"
docker compose version >/dev/null 2>&1 || die "docker compose (Compose v2) is missing"

# --- deploy.config.yaml (R-07, R-11) ----------------------------------------------------------------------------------
[[ -f $CONFIG_FILE ]] || die "$CONFIG_FILE not found: copy deploy.config.example.yaml to deploy.config.yaml and fill it in"

# cfg <path below lab6_deploy>: one value of the file, or an error when it is missing or null.
cfg() {
  local v
  v=$(yq -e ".lab6_deploy.$1" "$CONFIG_FILE" 2>/dev/null) || die "$CONFIG_FILE: lab6_deploy.$1 is missing or null (R-07)"
  printf '%s\n' "$v"
}

SLO_WINDOW=$(cfg slo.window)
AVAILABILITY_OBJECTIVE=$(cfg slo.availability.objective)
LATENCY_OBJECTIVE=$(cfg slo.latency.objective)
LATENCY_THRESHOLD_S=$(cfg slo.latency.threshold_seconds)
AVAILABILITY_MAX_BURN=$(cfg gate.availability.max_burn_rate)
LATENCY_MAX_BURN=$(cfg gate.latency.max_burn_rate)
MIN_REQUESTS=$(cfg gate.min_requests)
interval=$(cfg gate.interval)
INTERVAL_S=$(dur_seconds "$interval")
timeout=$(cfg timeout)
TIMEOUT_S=$(dur_seconds "$timeout")
SHADOW_ENABLED=false
if [[ $(yq -r '.lab6_deploy.shadow != null' "$CONFIG_FILE") == true ]]; then
  SHADOW_ENABLED=true
  SHADOW_TOOL=$(cfg shadow.tool)
  SHADOW_MIN_REQUESTS=$(cfg shadow.min_requests)
  [[ $SHADOW_TOOL == nginx ]] || die "$CONFIG_FILE: shadow.tool must be nginx for this release stack"
  [[ $SHADOW_MIN_REQUESTS =~ ^[0-9]+$ ]] || die "$CONFIG_FILE: shadow.min_requests must be an integer"
  (( SHADOW_MIN_REQUESTS > 120 )) || die "$CONFIG_FILE: shadow.min_requests must exceed the hang ceiling of 120 requests"
fi
case $RELEASE_STRATEGY in
  canary)
    mapfile -t STEP_WEIGHTS < <(yq '.lab6_deploy.steps[].weight' "$CONFIG_FILE")
    mapfile -t step_durations < <(yq '.lab6_deploy.steps[].min_duration' "$CONFIG_FILE")
    ;;
  flag)
    [[ $(cfg flag.name) == svcdesk-2-1 ]] || die "unsupported flag name"
    mapfile -t STEP_WEIGHTS < <(yq '.lab6_deploy.flag.steps[].percent' "$CONFIG_FILE")
    mapfile -t step_durations < <(yq '.lab6_deploy.flag.steps[].min_duration' "$CONFIG_FILE")
    ;;
  *) die "unknown release strategy: $RELEASE_STRATEGY" ;;
esac
(( ${#STEP_WEIGHTS[@]} > 0 )) || die "$CONFIG_FILE: lab6_deploy.steps is empty (R-10)"
STEP_MIN_S=()                              # STEP_WEIGHTS[i] per cent for at least STEP_MIN_S[i] seconds
for d in "${step_durations[@]}"; do
  STEP_MIN_S+=("$(dur_seconds "$d")")
done

# time_left_s: seconds until your own deadline (lab6_deploy.timeout). The course kills the script at 180 s, and a
# killed run has no outcome (R-15): leave yourself the time to roll back and write the record.
time_left_s() { calc "$TIMEOUT_S - $(elapsed_s)"; }

# --- the stack ----------------------------------------------------------------------------------------------------------
# stack_curl <curl arguments...>: curl as seen from inside the stack's network. Run by the course the script is on
# that network already; by hand (CADDY_ADMIN_URL unset) it runs inside the edge container, which has curl.
stack_curl() {
  if [[ -n $CADDY_ADMIN_URL ]]; then
    curl "$@"
  else
    docker compose exec -T "$CADDY_SERVICE" curl "$@"
  fi
}

# caddy_admin <METHOD> <path> [<content type> <body>]: one call of Caddy's admin API; prints the answer.
caddy_admin() {
  local method=$1 path=$2 base=${CADDY_ADMIN_URL:-http://127.0.0.1:2019}
  local args=(-sS --fail-with-body --max-time 10 -X "$method")
  if [[ $# -ge 4 ]]; then
    args+=(-H "Content-Type: $3" --data-binary "$4")
  fi
  stack_curl "${args[@]}" "${base%/}$path"
}

# The stack as Compose resolves it (with the course's override, when the course runs the script).
STACK_JSON=$(docker compose config --format json) || die "docker compose config failed for COMPOSE_FILE=$COMPOSE_FILE"

# The Caddyfile is the one in release/compose.yml (the config named $CADDYFILE_CONFIG, as `docker compose config`
# resolves it); set_weights changes the numbers after weighted_round_robin and nothing else, so the stack's file
# and what the script loads never drift apart. Keep `admin 0.0.0.0:2019` in it: POST /load replaces the WHOLE
# configuration, the admin listener included, and without that line the admin API moves to the container's own
# localhost, where the course's runner no longer reaches it.
CADDYFILE_CONFIG=${CADDYFILE_CONFIG:-caddyfile}
CADDYFILE_TEMPLATE=$(jq -er --arg c "$CADDYFILE_CONFIG" '.configs[$c].content' <<<"$STACK_JSON") \
  || die "no config '$CADDYFILE_CONFIG' with inline content in the stack (R-01: configuration goes in through configs: content:)"
n=$(grep -cE 'weighted_round_robin([[:space:]]+[0-9]+)+' <<<"$CADDYFILE_TEMPLATE" || true)
[[ $n == 1 ]] || die "the Caddyfile must have exactly one 'lb_policy weighted_round_robin <weights>' line (it has $n)"

# caddyfile_with_weights <w1> <w2> ...: the stack's Caddyfile with these weights.
caddyfile_with_weights() {
  sed -E "s/weighted_round_robin([[:space:]]+[0-9]+)+/weighted_round_robin $*/" <<<"$CADDYFILE_TEMPLATE"
}

# get_weights: the weights Caddy runs now, space-separated in upstream order, e.g. "90 10".
# weights_by_upstream: the same as lines "<upstream> <weight>", e.g. "svcdesk-canary:8080 10".
WRR='[.. | objects | select(.handler? == "reverse_proxy" and .load_balancing.selection_policy.policy? == "weighted_round_robin")] | first // empty'
get_weights() {
  caddy_admin GET /config/ | jq -r "$WRR"' | .load_balancing.selection_policy.weights | map(tostring) | join(" ")'
}
weights_by_upstream() {
  caddy_admin GET /config/ \
    | jq -r "$WRR"' | [.upstreams, .load_balancing.selection_policy.weights] | transpose[] | "\(.[0].dial) \(.[1])"'
}

# set_weights <stable> <canary>: load the Caddyfile with these weights (whole numbers, in upstream order; a stack
# with a third upstream, such as Stretch 1's recipe, passes three). Refuses all-zero weights (R-06: Caddy 2.11.4
# then answers no request at all), then reads the weights back and fails unless Caddy runs exactly these.
set_weights() {
  local w sum=0 got body
  (( $# >= 2 )) || die "set_weights needs one weight per upstream, e.g. set_weights 90 10"
  for w in "$@"; do
    [[ $w =~ ^[0-9]+$ ]] || die "set_weights: '$w' is not a whole number"
    sum=$(( sum + w ))
  done
  (( sum > 0 )) || die "set_weights $*: refused - with every weight at 0 Caddy 2.11.4 answers no request at all (R-06)"
  body=$(caddyfile_with_weights "$@")
  [[ -n $body ]] || die "set_weights: empty Caddyfile"
  caddy_admin POST /load text/caddyfile "$body" >/dev/null \
    || { log "set_weights $*: Caddy refused the configuration"; return 1; }
  got=$(get_weights) || { log "set_weights $*: could not read the weights back"; return 1; }
  [[ $got == "$*" ]] || { log "set_weights $*: Caddy runs '$got'"; return 1; }
  log "weights now $*"
}

set_flag_percent() {
  local p=$1 f value expected
  [[ $p =~ ^[0-9]+$ ]] && (( p <= 100 )) || { log "invalid flag percentage: $p"; return 1; }
  f=$(mktemp) || return 1
  jq -n --argjson p "$p" '{flags: {"svcdesk-2-1": {state: "ENABLED", variants: {on: true, off: false},
    defaultVariant: "off", targeting: {fractional: [["on", $p], ["off", (100 - $p)]]}}}}' >"$f"
  chmod 644 "$f"
  if ! docker compose cp "$f" flagd:/etc/flagd/flags.json; then
    rm -f "$f"
    log "failed to update flagd"
    return 1
  fi
  rm -f "$f"
  sleep 2
  if (( p == 0 || p == 100 )); then
    expected=false
    (( p == 100 )) && expected=true
    value=$(stack_curl -fsS --max-time 3 -H 'Content-Type: application/json' \
      -d '{"context":{"targetingKey":"release-verification"}}' \
      http://flagd:8016/ofrep/v1/evaluate/flags/svcdesk-2-1 | jq -r '.value') || return 1
    [[ $value == "$expected" ]] || { log "flagd returned $value, expected $expected"; return 1; }
  fi
  log "flag svcdesk-2-1 set to $p%"
}

# start_canary <image>: put an image into svcdesk-canary, the one command R-14 allows for it. Only svcdesk-canary is
# recreated; it keeps whatever weight Caddy gives it (put it at 0 first). Waits until the new container answers
# /health. Your own requests to svcdesk-canary are not the users' (R-14), but a search you send counts towards the
# hang's onset like any other (RELEASE-SPEC.md R-30).
start_canary() {
  local image=$1 i
  CANARY_IMAGE=$image docker compose up -d --no-deps --wait svcdesk-canary >&2 \
    || { log "start_canary: compose could not start svcdesk-canary with $image"; return 1; }
  for i in $(seq 1 30); do
    if stack_curl -fsS --max-time 2 http://svcdesk-canary:8080/health >/dev/null 2>&1; then
      log "svcdesk-canary runs $image"
      return 0
    fi
    sleep 1
  done
  log "start_canary: svcdesk-canary did not answer /health within 30 s"
  return 1
}

# --- Prometheus -----------------------------------------------------------------------------------------------------
# prom_query <PromQL> [<time>]: one instant query against your Prometheus, evaluated now or at <time> (Unix seconds).
# The query must return exactly one number (use sum(...) around a vector). Prints it and returns:
#   0  a number (possibly +Inf);
#   1  Prometheus did not answer, refused the query, or returned more than one series;
#   2  NO DATA: an empty result, or NaN (0 divided by 0: nothing to count yet).
# 2 is not a pass and not a failure: what it means for your gate is your decision (the empty-data case, R-28).
# Under set -e, call it inside `if` or with `||`, never bare:
#   if share=$(prom_query "$q"); then ...; else rc=$?; ...; fi
# Two numbers that belong together - a count and its 5xx or its le bucket - must come from the same scrape: read them
# in one query, or give every query of one look the same <time>, a second or two in the past (trap 4):
#   at=$(( $(now_s) - 2 )); n=$(prom_query "$q_all" "$at") && bad=$(prom_query "$q_5xx" "$at") || ...
prom_query() {
  local body n value
  local -a at=()
  [[ -n ${2:-} ]] && at=(--data-urlencode "time=$2")
  body=$(curl -sS --fail-with-body --max-time 5 "${PROMETHEUS_URL%/}/api/v1/query" --data-urlencode "query=$1" \
    ${at[@]+"${at[@]}"} 2>&1) \
    || { log "prom_query: no answer from $PROMETHEUS_URL, or an error: ${body:0:300}"; return 1; }
  [[ $(jq -r '.status' <<<"$body" 2>/dev/null) == success ]] \
    || { log "prom_query: ${body:0:300}"; return 1; }
  case $(jq -r '.data.resultType' <<<"$body") in
    scalar) value=$(jq -r '.data.result[1]' <<<"$body") ;;
    vector)
      n=$(jq '.data.result | length' <<<"$body")
      (( n == 0 )) && return 2
      (( n == 1 )) || { log "prom_query: $n series, expected one (aggregate with sum): $1"; return 1; }
      value=$(jq -r '.data.result[0].value[1]' <<<"$body") ;;
    *) log "prom_query: a range or string result, expected one number: $1"; return 1 ;;
  esac
  [[ $value == NaN ]] && return 2
  printf '%s\n' "$value"
}

# --- the change record (R-23, R-24, R-27) ---------------------------------------------------------------------------
# Your decisions about this change, the same for every run. The record check accepts only the values listed.
CHANGE_TYPE=standard
RISK=low
ROLLBACK_PLAN="Restore Caddy weights to 100/0/0 through its admin API; stable stays running."
if [[ $RELEASE_STRATEGY == flag ]]; then
  ROLLBACK_PLAN="Disable the feature flag, then restore Caddy weights to 100/0/0; stable stays running."
fi

STABLE_IMAGE=$(jq -r '.services["svcdesk-stable"].image // empty' <<<"$STACK_JSON")
[[ -n $STABLE_IMAGE ]] || die "the stack has no service svcdesk-stable (R-01)"

ACTIONS=()
RECORD_WRITTEN=0
CANARY_STARTED=0

# yaml_str <text>: a quoted YAML string (a JSON string is one).
yaml_str() { jq -Rn --arg s "$1" '$s'; }

# record_action <autonomy> <what the script did> [<approval>]: one entry of `actions`, stamped now. The autonomy
# ladder of Lecture 6: read-only, suggest, approve-then-act, closed-loop. approve-then-act needs the approval that
# existed before the run (a change ticket, a CAB decision): nobody can approve during it (R-24).
record_action() {
  local autonomy=$1 text=$2 approval=${3:-} entry
  case $autonomy in
    read-only|suggest|approve-then-act|closed-loop) ;;
    *) die "record_action: autonomy '$autonomy' is not one of read-only, suggest, approve-then-act, closed-loop" ;;
  esac
  entry="{at: $(now_utc), action: $(yaml_str "$text"), autonomy: $autonomy"
  if [[ $autonomy == approve-then-act ]]; then
    [[ ${#approval} -ge 5 ]] || die "record_action: approve-then-act needs the approval it acts on (R-24)"
    entry+=", approval: $(yaml_str "$approval")"
  fi
  ACTIONS+=("$entry}")
  log "action [$autonomy] $text"
}

# record_body: the prose below the front matter, read by the lecturer (R-27). Write yours: it is the same reasoning
# for every run, and you may add what this run saw (the variables of the script are in scope).
record_body() {
  if [[ $RELEASE_STRATEGY == flag ]]; then
    cat <<'EOF'
# Change record

## Why this change type

This is a standard change only within the documented, pre-authorised feature-flag procedure. The candidate starts
dark and is exposed in configured stages, with Prometheus observations and automatic rollback. A new service,
changed SLO or untested procedure needs normal change assessment instead.

## Risk and what bounds it

The flag starts off, then enables candidate behaviour for 10% and 50% of searches. The gate reads only the on
variant and requires the configured observation minimum before passing; a stopped counter is treated as a hang.
Rollback disables the flag and restores stable routing. The runner independently measures the actual blast radius.
EOF
    return
  fi
  cat <<'EOF'
# Change record

## Why this change type

This is a standard change only within the documented, pre-authorised release procedure: nginx first mirrors live
searches to the candidate while serving users from the stable build, then a weighted canary begins only after the
shadow gate passes. Both phases read the candidate's SLIs from Prometheus, and promotion is automatic only after
the configured observation minimums and SLO-derived limits pass. An unattended release is not automatically low
risk; a new service, changed SLO, untested gate, or candidate outside this procedure needs normal change
assessment instead. The gate's decisions are closed-loop; its Prometheus observations are read-only.

## Risk and what bounds it

Users receive stable answers throughout shadowing: nginx mirrors each search to the candidate and discards its
response. Before routing users to the candidate, the gate requires at least 200 stable-track searches to have
passed through the shadow proxy and 200 completed candidate observations to evaluate error and latency shares.
A hang stops producing completed candidate observations; the 10-second no-progress watchdog rolls back after the
proxy has continued to serve stable traffic. Missing or inconsistent monitoring data also fails closed. Only after
shadow passes does the 10% weighted step begin; the 50% step follows only after that passes. Weighted steps reject
a bad-share above the configured 20% ceiling after five bad observations and require at least 150 requests before
passing. Rollback restores 100/0/0 through the admin API without stopping stable. The actual blast radius is
measured by the runner for each run, not asserted here.
EOF
}

# write_record <promoted|rolled-back> <reason>: $RELEASE_RECORD_DIR/CHANGE.md with R-23's front matter.
write_record() {
  local outcome=$1 reason=$2 finished a
  finished=$(now_utc)
  case $CHANGE_TYPE in standard|normal|emergency) ;; *) log "WARNING: change_type '$CHANGE_TYPE' is not standard, normal or emergency" ;; esac
  case $RISK in low|medium|high) ;; *) log "WARNING: risk '$RISK' is not low, medium or high" ;; esac
  (( ${#ROLLBACK_PLAN} >= 20 )) || log "WARNING: rollback_plan is shorter than 20 characters"
  (( ${#reason} >= 10 )) || log "WARNING: reason is shorter than 10 characters"
  (( ${#ACTIONS[@]} >= 3 )) || log "WARNING: ${#ACTIONS[@]} actions recorded; R-24 wants at least three"
  mkdir -p "$RELEASE_RECORD_DIR"
  {
    echo "---"
    echo "lab6_change:"
    echo "  id: CHG-${STARTED//[-:]/}"
    echo "  candidate: $(yaml_str "$CANDIDATE")"
    echo "  stable: $(yaml_str "$STABLE_IMAGE")"
    echo "  strategy: $RELEASE_STRATEGY"
    echo "  change_type: $CHANGE_TYPE"
    echo "  risk: $RISK"
    echo "  rollback_plan: $(yaml_str "$ROLLBACK_PLAN")"
    echo "  started: $STARTED"
    echo "  finished: $finished"
    echo "  outcome: $outcome"
    echo "  reason: $(yaml_str "$reason")"
    echo "  actions:"
    for a in "${ACTIONS[@]}"; do
      echo "    - $a"
    done
    echo "---"
    record_body
  } >"$RELEASE_RECORD_DIR/CHANGE.md"
  RECORD_WRITTEN=1
  log "record: $RELEASE_RECORD_DIR/CHANGE.md"
}

# finish <promoted|rolled-back> <reason>: write the record and exit 0 or 3 (R-15). Call it only once the routing it
# reports is in place. In a canary run it checks Caddy first - promoted: every upstream but svcdesk-canary at 0;
# rolled back: svcdesk-canary at 0 - and exits 1, a run without an outcome, when the weights disagree.
finish() {
  local outcome=$1 reason=$2 weights canary others
  case $outcome in promoted|rolled-back) ;; *) die "finish: the outcome is promoted or rolled-back, not '$outcome'" ;; esac
  if [[ $RELEASE_STRATEGY == canary ]]; then
    weights=$(weights_by_upstream) || die "finish: could not read Caddy's weights"
    canary=$(awk '$1 == "svcdesk-canary:8080" { print $2 }' <<<"$weights")
    others=$(awk '$1 != "svcdesk-canary:8080" { s += $2 } END { print s + 0 }' <<<"$weights")
    if [[ $outcome == promoted ]] && ! (( ${canary:-0} > 0 && others == 0 )); then
      die "finish promoted, but Caddy's weights are: $(tr '\n' ' ' <<<"$weights")- the stable build still takes requests"
    fi
    if [[ $outcome == rolled-back ]] && (( ${canary:-0} != 0 )); then
      die "finish rolled-back, but Caddy's weights are: $(tr '\n' ' ' <<<"$weights")- the candidate still takes requests"
    fi
  fi
  write_record "$outcome" "$reason"
  log "outcome: $outcome - $reason ($(elapsed_s) s)"
  if [[ $outcome == promoted ]]; then exit 0; else exit 3; fi
}

on_exit() {
  local rc=$?
  if (( RECORD_WRITTEN == 0 )); then
    log "exited with status $rc before finish: no record, no outcome (R-15, R-23)"
    if (( CANARY_STARTED == 1 )); then
      trap - EXIT
      set +e
      if set_weights 100 0 0; then
        record_action closed-loop "fail-safe restored weights 100/0/0 after unexpected exit status $rc"
        write_record rolled-back "unexpected deploy.sh failure status $rc; fail-safe restored stable-only routing"
        log "outcome: rolled-back by the unexpected-exit fail-safe"
        exit 3
      fi
      log "ERROR: the unexpected-exit fail-safe could not restore stable-only routing"
    fi
  fi
}
trap on_exit EXIT

log "candidate $CANDIDATE, stable $STABLE_IMAGE, strategy $RELEASE_STRATEGY"
log "config: SLO window $SLO_WINDOW; availability $AVAILABILITY_OBJECTIVE (max burn $AVAILABILITY_MAX_BURN);" \
    "latency $LATENCY_OBJECTIVE under ${LATENCY_THRESHOLD_S}s (max burn $LATENCY_MAX_BURN);" \
    "min_requests $MIN_REQUESTS; interval ${INTERVAL_S}s; timeout ${TIMEOUT_S}s;" \
    "steps ${STEP_WEIGHTS[*]} % for ${STEP_MIN_S[*]} s"
if [[ $SHADOW_ENABLED == true ]]; then
  log "shadow: nginx, at least $SHADOW_MIN_REQUESTS ingress searches and completed candidate observations before weighted traffic; hangs use the progress watchdog"
fi
log "Prometheus $PROMETHEUS_URL; Caddy admin ${CADDY_ADMIN_URL:-via docker compose exec $CADDY_SERVICE}"

# =====================================================================================================================
# Canary gate: SLO-derived bad-share checks plus a no-progress watchdog for unobserved hangs.
# The gate uses raw monotonic counters. Each poll evaluates all four counters at one Prometheus timestamp, so a
# bucket and its count cannot straddle a scrape. Deltas are reset at every weight step.
AVAILABILITY_LIMIT=$(calc "$AVAILABILITY_MAX_BURN * (1 - $AVAILABILITY_OBJECTIVE)")
LATENCY_LIMIT=$(calc "$LATENCY_MAX_BURN * (1 - $LATENCY_OBJECTIVE)")
PROGRESS_TIMEOUT_S=$(calc "$INTERVAL_S * 2")
if check "$PROGRESS_TIMEOUT_S < 10"; then PROGRESS_TIMEOUT_S=10; fi

BASE_SELECTOR='job="svcdesk", track="canary", http_route="/kb/search"'
if [[ $RELEASE_STRATEGY == flag ]]; then
  BASE_SELECTOR+=', feature_flag_variant="on"'
fi
TOTAL_QUERY="sum(http_server_request_duration_seconds_count{$BASE_SELECTOR}) or vector(0)"
ERROR_QUERY="sum(http_server_request_duration_seconds_count{$BASE_SELECTOR, http_response_status_code=~\"5..\"}) or vector(0)"
GOOD_QUERY="sum(http_server_request_duration_seconds_bucket{$BASE_SELECTOR, le=\"$LATENCY_THRESHOLD_S\"}) or vector(0)"
UP_QUERY='sum(up{job="svcdesk", track="canary"}) or vector(0)'
STABLE_TOTAL_QUERY='sum(http_server_request_duration_seconds_count{job="svcdesk", track="stable", http_route="/kb/search"}) or vector(0)'

read_gate_point() {
  local at=$(( $(now_s) - 2 ))
  POINT_UP=$(prom_query "$UP_QUERY" "$at") || return $?
  POINT_TOTAL=$(prom_query "$TOTAL_QUERY" "$at") || return $?
  POINT_ERRORS=$(prom_query "$ERROR_QUERY" "$at") || return $?
  POINT_GOOD=$(prom_query "$GOOD_QUERY" "$at") || return $?
  POINT_STABLE_TOTAL=$(prom_query "$STABLE_TOTAL_QUERY" "$at") || return $?
}

rollback() {
  local reason=$1 recovery
  log "gate decision: roll back - $reason"
  if [[ $RELEASE_STRATEGY == flag ]]; then
    set_flag_percent 0 || die "could not disable feature flag after: $reason"
    record_action closed-loop "set feature flag to 0 percent to roll back"
  fi
  set_weights 100 0 0 || die "could not restore stable-only weights after: $reason"
  record_action closed-loop "release automation owns rollback and set weights 100/0/0: $reason"
  if recovery=$(stack_curl -fsS --max-time 2 http://svcdesk-stable:8080/health 2>&1); then
    record_action read-only "recovery evidence: stable health endpoint answered successfully after rollback"
  else
    log "WARNING: stable health check after rollback failed: $recovery"
    record_action read-only "recovery evidence: stable health check failed after rollback; operator investigation required"
  fi
  finish rolled-back "$reason"
}

if ! set_weights 100 0 0; then
  die "could not establish stable-only routing before starting the candidate"
fi
record_action closed-loop "set weights 100/0/0 before candidate startup"

if [[ $RELEASE_STRATEGY == flag ]]; then
  set_flag_percent 0 || die "could not disable flag before candidate startup"
  record_action closed-loop "set feature flag to 0 percent before candidate startup"
fi
CANARY_STARTED=1
if ! start_canary "$CANDIDATE"; then
  rollback "candidate failed to start or answer health checks"
fi
record_action closed-loop "start svcdesk-canary with the candidate at weight 0"

if [[ $SHADOW_ENABLED == true && $RELEASE_STRATEGY == canary ]]; then
  if read_gate_point; then
    :
  else
    rc=$?
    rollback "Prometheus returned no usable baseline counters before shadowing (status $rc)"
  fi
  SHADOW_BASE_TOTAL=$POINT_TOTAL
  SHADOW_BASE_ERRORS=$POINT_ERRORS
  SHADOW_BASE_GOOD=$POINT_GOOD
  SHADOW_BASE_STABLE_TOTAL=$POINT_STABLE_TOTAL

  if ! set_weights 0 0 100; then
    rollback "could not route stable user traffic through the nginx shadow"
  fi
  record_action closed-loop "enable nginx shadow at weights 0/0/100; users continue to receive stable responses"
  SHADOW_STARTED_S=$(now_s)
  LAST_PROGRESS_S=$SHADOW_STARTED_S
  PREVIOUS_TOTAL=$SHADOW_BASE_TOTAL
  PREVIOUS_STABLE_TOTAL=$SHADOW_BASE_STABLE_TOTAL
  log "shadow phase: nginx mirrors candidate searches; requiring $SHADOW_MIN_REQUESTS stable ingress searches and completed candidate observations before user canary"

  while :; do
    remaining=$(time_left_s)
    if check "$remaining <= $PROGRESS_TIMEOUT_S"; then
      rollback "release deadline reached before the shadow gate could decide"
    fi

    if read_gate_point; then
      :
    else
      rc=$?
      rollback "Prometheus query failed during shadow validation (status $rc)"
    fi
    record_action read-only "read candidate shadow counters from Prometheus"

    if check "$POINT_TOTAL + 0.0001 < $PREVIOUS_TOTAL || $POINT_TOTAL + 0.0001 < $SHADOW_BASE_TOTAL"; then
      rollback "candidate shadow request counter reset; gate evidence is no longer comparable"
    fi
    if check "$POINT_STABLE_TOTAL + 0.0001 < $PREVIOUS_STABLE_TOTAL || $POINT_STABLE_TOTAL + 0.0001 < $SHADOW_BASE_STABLE_TOTAL"; then
      rollback "stable shadow-ingress counter reset; gate evidence is no longer comparable"
    fi
    if check "$POINT_ERRORS + 0.0001 < $SHADOW_BASE_ERRORS || $POINT_GOOD + 0.0001 < $SHADOW_BASE_GOOD"; then
      rollback "candidate shadow SLI counter reset; gate evidence is no longer comparable"
    fi

    shadow_requests=$(calc "$POINT_TOTAL - $SHADOW_BASE_TOTAL")
    shadow_errors=$(calc "$POINT_ERRORS - $SHADOW_BASE_ERRORS")
    shadow_good=$(calc "$POINT_GOOD - $SHADOW_BASE_GOOD")
    shadow_slow=$(calc "$shadow_requests - $shadow_good")
    shadow_ingress=$(calc "$POINT_STABLE_TOTAL - $SHADOW_BASE_STABLE_TOTAL")
    if check "$shadow_slow < -0.001 || $shadow_errors < -0.001"; then
      rollback "Prometheus returned inconsistent shadow counters"
    fi
    if check "$shadow_slow < 0"; then shadow_slow=0; fi

    if check "$POINT_TOTAL > $PREVIOUS_TOTAL"; then
      LAST_PROGRESS_S=$(now_s)
    fi
    PREVIOUS_TOTAL=$POINT_TOTAL
    PREVIOUS_STABLE_TOTAL=$POINT_STABLE_TOTAL
    log "shadow: stable ingress=$shadow_ingress/$SHADOW_MIN_REQUESTS candidate completed=$shadow_requests/$SHADOW_MIN_REQUESTS 5xx=$shadow_errors slow=$shadow_slow; users remain on stable"

    now=$(now_s)
    if check "$shadow_ingress >= $SHADOW_MIN_REQUESTS && $shadow_requests >= $SHADOW_MIN_REQUESTS"; then
      break
    fi
    if check "$shadow_ingress >= $SHADOW_MIN_REQUESTS && $(( now - LAST_PROGRESS_S )) >= $PROGRESS_TIMEOUT_S"; then
      rollback "shadow candidate stopped completing searches: $shadow_requests completed observations after at least $shadow_ingress stable searches passed through nginx; treating absent observations as a hang"
    fi

    sleep_for=$INTERVAL_S
    if check "$remaining < $sleep_for"; then sleep_for=$remaining; fi
    sleep "$sleep_for"
  done

  # Slow candidates finish up to 2.1 s after the mirrored request; drain them before fixing the
  # shadow sample's final histogram counters and before collecting weighted-canary baselines.
  sleep 3
  if read_gate_point; then
    :
  else
    rc=$?
    rollback "Prometheus could not read the completed shadow sample (status $rc)"
  fi
  shadow_requests=$(calc "$POINT_TOTAL - $SHADOW_BASE_TOTAL")
  shadow_errors=$(calc "$POINT_ERRORS - $SHADOW_BASE_ERRORS")
  shadow_good=$(calc "$POINT_GOOD - $SHADOW_BASE_GOOD")
  shadow_slow=$(calc "$shadow_requests - $shadow_good")
  if check "$shadow_slow < -0.001 || $shadow_errors < -0.001 || $shadow_requests < $SHADOW_MIN_REQUESTS"; then
    rollback "shadow counters were inconsistent or below the required $SHADOW_MIN_REQUESTS completed searches after draining"
  fi
  if check "$shadow_slow < 0"; then shadow_slow=0; fi
  shadow_availability_share=$(calc "$shadow_errors / $shadow_requests")
  shadow_latency_share=$(calc "$shadow_slow / $shadow_requests")
  log "shadow result: $shadow_requests completed searches, availability bad share $shadow_availability_share (limit $AVAILABILITY_LIMIT), latency bad share $shadow_latency_share (limit $LATENCY_LIMIT)"

  if check "$shadow_errors >= 5 && $shadow_availability_share > $AVAILABILITY_LIMIT"; then
    rollback "shadow availability: $shadow_errors of $shadow_requests candidate searches failed against a $AVAILABILITY_LIMIT bad-share limit"
  fi
  if check "$shadow_slow >= 5 && $shadow_latency_share > $LATENCY_LIMIT"; then
    rollback "shadow latency: $shadow_slow of $shadow_requests candidate searches exceeded ${LATENCY_THRESHOLD_S}s against a $LATENCY_LIMIT bad-share limit"
  fi

  if ! set_weights 100 0 0; then
    rollback "could not disable nginx shadow after the candidate passed shadow validation"
  fi
  record_action closed-loop "disable nginx shadow after $shadow_requests candidate searches passed"
  # Let in-flight mirrored searches finish and reach a scrape before taking the first step baseline.
  sleep 10
  log "shadow gate passed; starting the weighted canary with users still routed to stable"
fi

if [[ $RELEASE_STRATEGY == flag ]]; then
  set_weights 0 100 0 || rollback "could not route traffic to the dark candidate"
  record_action closed-loop "route traffic to candidate with feature flag disabled"
fi

for step_index in "${!STEP_WEIGHTS[@]}"; do
  weight=${STEP_WEIGHTS[$step_index]}
  stable_weight=$(( 100 - weight ))
  min_duration=${STEP_MIN_S[$step_index]}

  if read_gate_point; then
    :
  else
    rc=$?
    rollback "Prometheus returned no usable baseline counters (status $rc)"
  fi
  STEP_BASE_TOTAL=$POINT_TOTAL
  STEP_BASE_ERRORS=$POINT_ERRORS
  STEP_BASE_GOOD=$POINT_GOOD

  if [[ $RELEASE_STRATEGY == flag ]]; then
    set_flag_percent "$weight" || rollback "could not apply feature flag percentage $weight"
    record_action closed-loop "set feature flag to $weight percent"
  else
    set_weights "$stable_weight" "$weight" 0 || rollback "could not apply canary weights $stable_weight/$weight"
    record_action closed-loop "set weights $stable_weight/$weight/0 for step $(( step_index + 1 ))"
  fi
  STEP_STARTED_S=$(now_s)
  LAST_PROGRESS_S=$STEP_STARTED_S
  PREVIOUS_TOTAL=$STEP_BASE_TOTAL
  log "step $(( step_index + 1 )): weight $weight%, minimum ${min_duration}s and $MIN_REQUESTS requests"

  while :; do
    elapsed_step=$(calc "$(now_s) - $STEP_STARTED_S")
    remaining=$(time_left_s)
    if check "$remaining <= $PROGRESS_TIMEOUT_S"; then
      rollback "release deadline reached before a safe decision"
    fi

    if read_gate_point; then
      :
    else
      rc=$?
      rollback "Prometheus query failed during the gate (status $rc)"
    fi
    record_action read-only "read canary counters at weight $weight%"

    if check "$elapsed_step >= $PROGRESS_TIMEOUT_S && $POINT_UP < 0.5"; then
      rollback "canary Prometheus target is not up"
    fi
    if check "$POINT_TOTAL + 0.0001 < $PREVIOUS_TOTAL || $POINT_TOTAL + 0.0001 < $STEP_BASE_TOTAL"; then
      rollback "canary request counter reset; gate evidence is no longer comparable"
    fi
    if check "$POINT_ERRORS + 0.0001 < $STEP_BASE_ERRORS || $POINT_GOOD + 0.0001 < $STEP_BASE_GOOD"; then
      rollback "canary SLI counter reset; gate evidence is no longer comparable"
    fi

    requests=$(calc "$POINT_TOTAL - $STEP_BASE_TOTAL")
    errors=$(calc "$POINT_ERRORS - $STEP_BASE_ERRORS")
    good=$(calc "$POINT_GOOD - $STEP_BASE_GOOD")
    slow=$(calc "$requests - $good")
    if check "$slow < -0.001 || $errors < -0.001"; then
      rollback "Prometheus returned inconsistent canary counters"
    fi
    if check "$slow < 0"; then slow=0; fi

    if check "$POINT_TOTAL > $PREVIOUS_TOTAL"; then
      LAST_PROGRESS_S=$(now_s)
    fi
    PREVIOUS_TOTAL=$POINT_TOTAL
    if check "$requests > 0"; then
      bad_availability_share=$(calc "$errors / $requests")
      bad_latency_share=$(calc "$slow / $requests")
    else
      bad_availability_share=0
      bad_latency_share=0
    fi
    log "step $(( step_index + 1 )) weight ${weight}%: requests=$requests 5xx=$errors (${bad_availability_share}, limit $AVAILABILITY_LIMIT) slow=$slow (${bad_latency_share}, limit $LATENCY_LIMIT), target_up=$POINT_UP"

    if check "$requests >= 20 && $errors >= 5 && $bad_availability_share > $AVAILABILITY_LIMIT"; then
      rollback "availability: $errors of $requests requests failed against a $AVAILABILITY_LIMIT bad-share limit at weight $weight%"
    fi
    if check "$requests >= 20 && $slow >= 5 && $bad_latency_share > $LATENCY_LIMIT"; then
      rollback "latency: $slow of $requests requests exceeded ${LATENCY_THRESHOLD_S}s against a $LATENCY_LIMIT bad-share limit at weight $weight%"
    fi

    now=$(now_s)
    if check "$elapsed_step >= $PROGRESS_TIMEOUT_S && $(( now - LAST_PROGRESS_S )) >= $PROGRESS_TIMEOUT_S"; then
      rollback "canary produced no completed search for ${PROGRESS_TIMEOUT_S}s at weight $weight%; treating absent observations as a hang"
    fi
    if check "$elapsed_step >= $min_duration && $requests >= $MIN_REQUESTS"; then
      log "step $(( step_index + 1 )) passed with $requests canary searches"
      break
    fi

    sleep_for=$INTERVAL_S
    if check "$remaining < $sleep_for"; then sleep_for=$remaining; fi
    sleep "$sleep_for"
  done
done

if [[ $RELEASE_STRATEGY == flag ]]; then
  set_flag_percent 100 || rollback "could not enable feature flag for promotion"
  record_action closed-loop "set feature flag to 100 percent to promote the candidate"
else
  set_weights 0 100 0 || rollback "candidate passed the gate but promotion routing failed"
  record_action closed-loop "set weights 0/100/0 to promote the candidate"
fi
finish promoted "all configured canary steps passed their SLO-derived gates"

#!/usr/bin/env bash
# Mission P6 - verification script. Prints PASS/FAIL per check; exits 1 if any FAIL.
# Usage: SMS_TEST_TOKEN=<token> ORIGIN_IP=<ip> bash tools/verify-hiding.sh
#   SMS_TEST_TOKEN : any valid DRF token (for authenticated API body checks)
#   ORIGIN_IP     : public IP of the origin host (for the direct-access check)
set -u

ORIGIN="https://sms.darkzhub.asia"
HOSTS="sms.darkzhub.asia sms2-api.darkzhub.asia gw.darkzhub.asia dashboard.darkzhub.asia"
TOKEN="${SMS_TEST_TOKEN:-}"
ORIGIN_IP="${ORIGIN_IP:-}"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1${2:+ ($2)}"; FAIL=1; }
check() { if [ "$2" -eq 0 ]; then pass "$1"; else fail "$1" "${3:-}"; fi; }

echo "=== 1. No absolute backend URLs in /api/* response bodies ==="
if [ -z "$TOKEN" ]; then
  fail "authenticated API body check (SMS_TEST_TOKEN not set)"
else
  for path in "/api/students/?page_size=2" "/api/school-config/current/" "/api/students/statistics/"; do
    body=$(curl -s --max-time 20 -H "Authorization: Token $TOKEN" "$ORIGIN$path" 2>/dev/null)
    echo "$body" | grep -Eq 'https?://(sms2-api|gw|api)\.darkzhub\.asia' && rc=1 || rc=0
    check "no backend host in $path" "$rc"
    echo "$body" | grep -Eq '"next":"https?://' && rc=1 || rc=0
    check "pagination links relative in $path" "$rc"
  done
fi

echo "=== 2. Required security headers on all four hosts ==="
for host in $HOSTS; do
  hdr=$(curl -sI --max-time 15 "https://$host/" 2>/dev/null)
  for pair in \
    'strict-transport-security:HSTS' \
    'content-security-policy:CSP' \
    'x-content-type-options:nosniff' \
    'x-frame-options:X-Frame-Options'; do
    needle="${pair%%:*}"; label="${pair##*:}"
    echo "$hdr" | grep -qi "^$needle:" && rc=0 || rc=1
    check "$host has $label" "$rc"
  done
done

echo "=== 3. Fingerprint headers absent ==="
for host in $HOSTS; do
  hdr=$(curl -sI --max-time 15 "https://$host/" 2>/dev/null)
  echo "$hdr" | grep -qiE '^(x-powered-by|via):' && rc=1 || rc=0
  check "$host has no X-Powered-By/Via" "$rc"
  echo "$hdr" | grep -qi '^server:' && rc=1 || rc=0
  check "$host has no Server header" "$rc" "Cloudflare edge adds Server: cloudflare; cannot be removed by origin"
done

echo "=== 4. No public DNS A/CAA records for legacy backend hosts ==="
for host in gw.darkzhub.asia sms2-api.darkzhub.asia; do
  if command -v dig >/dev/null 2>&1; then
    answers=$(dig +short "$host" A 2>/dev/null | grep -c .)
    [ "$answers" -eq 0 ] && rc=0 || rc=1
    check "$host has no A records" "$rc" "$answers answer(s)"
  else
    fail "$host DNS check (dig not installed)"
  fi
done

echo "=== 5. Direct access to origin port 8000 ==="
if [ -z "$ORIGIN_IP" ]; then
  fail "direct origin check (ORIGIN_IP not set)"
else
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 6 \
    -H 'Host: sms2-api.darkzhub.asia' "http://$ORIGIN_IP:8000/api/health/" 2>/dev/null || echo 000)
  [ "$code" = "000" ] && rc=0 || rc=1
  check "origin port 8000 unreachable externally" "$rc" "got $code"
fi

echo
if [ "$FAIL" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
exit "$FAIL"

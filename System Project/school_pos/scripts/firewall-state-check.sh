#!/usr/bin/env bash
# Mission P4 — firewall/tunnel state check. Read-only; exits 1 on any failure.
# Usage: firewall-state-check.sh <origin-public-ip> [cf-test-ip]
set -u
fail=0
check() { if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1 (${3:-})"; fail=1; fi; }

ORIGIN_IP="${1:-}"
CF_TEST_IP="${2:-}"
[ -n "$ORIGIN_IP" ] || { echo "FAIL: origin public IP argument required"; exit 1; }

# 1. Direct access to the origin port must NOT succeed from a non-Cloudflare IP.
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
  -H 'Host: sms2-api.darkzhub.asia' "http://${ORIGIN_IP}:8000/api/health/" 2>/dev/null || echo 000)
[ "$code" = "000" ] || [ "$code" = "403" ] || [ "$code" = "404" ]
check "origin port 8000 not publicly reachable (got $code)" $?

# 2. From a Cloudflare IP (or via the tunnel), Django must answer.
if [ -n "$CF_TEST_IP" ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    -H "CF-Connecting-IP: ${CF_TEST_IP}" \
    -H 'Host: sms2-api.darkzhub.asia' \
    "https://sms.darkzhub.asia/api/health/" 2>/dev/null || echo 000)
  [ "$code" = "200" ]
  check "Django responds through Cloudflare (got $code)" $?
fi

# 3. ufw ruleset, if present, must not expose 8000 to the world.
if command -v ufw >/dev/null 2>&1; then
  ufw status numbered | grep -E '8000.*(Anywhere|0\.0\.0\.0/0|::/0)' >/dev/null 2>&1
  if [ $? -eq 0 ]; then check "ufw exposes port 8000 to the world" 1; else check "ufw has no world-wide 8000 rule" 0; fi
fi

exit $fail

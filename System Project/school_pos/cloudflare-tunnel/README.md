# Cloudflare Tunnel + firewall lockdown (mission P4)

All values below are placeholders. Nothing in this directory is applied
automatically — applying it changes production DNS/firewall and must be done
in a maintenance window with the rollback steps at the end.

## 1. Create the tunnel (Cloudflare API or dashboard)

```bash
# Requires CLOUDFLARE_API_TOKEN with Tunnel:Edit and DNS:Edit (CI secret, never in source)
curl -X POST "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/cfd_tunnel" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name":"sms-origin-tunnel","config":{"warp-routing":{"enabled":false}}}'
# Store the returned id/token in the secret manager. Copy config.yml to
# config.local.yml and fill tunnel + credentials-file.
```

Add DNS records for **gw.darkzhub.asia** and **dashboard.darkzhub.asia** to
the tunnel (`CNAME <tunnel-id>.cfargotunnel.com`) if those hosts must stay
reachable for installed desktop clients. Do the same for
**sms2-api.darkzhub.asia** only if old updater clients still depend on it;
otherwise remove it (see DNS removal below).

## 2. Firewall — allow ONLY Cloudflare IP ranges to port 8000

Fetch the current ranges from `https://api.cloudflare.com/client/v4/ips`
(never hardcode them; they change). Linux example (ufw):

```bash
CF_V4=$(curl -s https://api.cloudflare.com/client/v4/ips | jq -r '.result.ipv4_cidrs[]')
CF_V6=$(curl -s https://api.cloudflare.com/client/v4/ips | jq -r '.result.ipv6_cidrs[]')
sudo ufw default deny incoming
for c in $CF_V4; do sudo ufw allow from "$c" to any port 8000 proto tcp; done
for c in $CF_V6; do sudo ufw allow from "$c" to any port 8000 proto tcp; done
sudo ufw enable
```

Windows (this origin) equivalent — run in an elevated PowerShell:

```powershell
# Repeat for each CIDR from the /ips endpoint; netsh uses masked addresses.
# netsh advfirewall firewall add rule name="CF to SMS 8000" dir=in action=allow `
#   protocol=TCP localport=8000 remoteip=<CF_CIDR>
# Plus a blocking rule with remoteip=any placed AFTER the allow rules.
```

The backend listens on **127.0.0.1:8000** (Waitress) and the tunnel connects
outbound; inbound TCP 8000 should be refused from everywhere by default.

## 3. Verify

```bash
bash school_pos/scripts/firewall-state-check.sh <origin-public-ip> <cf-test-ip>
bash tools/verify-hiding.sh
```

## 4. DNS removal order (only after the Worker + tunnel are verified)

1. Confirm `/api/*`, `/media/*`, `/releases/*` all 200 through
   `https://sms.darkzhub.asia` and that installed desktop clients still work
   via `gw.darkzhub.asia`.
2. Delete the public **A/AAAA** records for `sms2-api.darkzhub.asia`
   (and `gw.darkzhub.asia` only if the tunnel CNAME already routes it).
3. Wait 5 minutes; re-run both verification scripts.
4. Remove any CAA records that authorize a different CA for those hosts.

## 5. Rollback (<10 minutes)

- Restore the deleted DNS A records (old values in the change ticket).
- Remove the firewall allow rules / re-enable the previous ruleset.
- Restart `DarkZSMS-Backend` if settings were changed.
- Flip the Worker to bypass (remove the routes in `wrangler.proxy.jsonc` and
  `npx wrangler deploy --config wrangler.proxy.jsonc`), or remove its route.
- `git revert` the branch and `git push` the revert.

// In-memory sliding-window rate limiter.
//
// WARNING: this state lives in a single process's memory. It is fine for a
// single dev/staging instance, but MUST be replaced with a shared store
// (Redis/Upstash) before running multiple instances or on serverless,
// since each instance/cold-start gets its own map and limits can be bypassed.

const hits = new Map<string, number[]>();

/**
 * Client-identifying key for rate limiting.
 *
 * Client-supplied headers (x-forwarded-for, x-real-ip, cf-connecting-ip) are
 * spoofable when the app is directly reachable, so they are only consulted
 * when TRUST_PROXY=1 — which must only be set when the app sits behind a proxy
 * (Cloudflare/nginx/Vercel edge) that OVERWRITES those headers from the real
 * connection. Otherwise all clients share a single "local" bucket, which
 * throttles the whole server but cannot be bypassed by header-spoofing.
 */
export function rateLimitKey(req: Request): string {
  if (process.env.TRUST_PROXY === "1") {
    return (
      req.headers.get("cf-connecting-ip") ??
      req.headers.get("x-real-ip") ??
      req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
      "unknown"
    );
  }
  return "local";
}

export function checkRateLimit(
  key: string,
  maxAttempts: number,
  windowMs: number,
): { allowed: boolean; retryAfterMs?: number } {
  const now = Date.now();
  const recent = (hits.get(key) ?? []).filter((t) => now - t < windowMs);

  if (recent.length >= maxAttempts) {
    const retryAfterMs = windowMs - (now - recent[0]);
    hits.set(key, recent);
    return { allowed: false, retryAfterMs };
  }

  recent.push(now);
  hits.set(key, recent);
  return { allowed: true };
}

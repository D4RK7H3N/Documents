/**
 * Minimal Cloudflare Worker proxy (mission P2) — /api/* -> ORIGIN.
 *
 * Forwards every /api/* request to the Django backend:
 *   - Host:                <origin host>
 *   - X-Forwarded-Host:    sms.darkzhub.asia
 *   - X-Forwarded-Proto:   https
 * Passes through the method, path+query and an allowlist of headers.
 * Strips Server / X-Powered-By / Via from responses so no backend
 * fingerprint leaks to browsers.
 *
 * Deploy:
 *   npx wrangler deploy --config wrangler.proxy.jsonc
 *   npx wrangler secret put ORIGIN --config wrangler.proxy.jsonc
 *   # value: the Django backend origin, e.g. https://sms2-api.darkzhub.asia
 */
const FORWARD_HEADERS = new Set([
  'accept',
  'accept-encoding',
  'accept-language',
  'authorization',
  'content-type',
  'user-agent',
  'x-device-id',
  'x-device-previous-id',
  // Cross-origin dev/Electron shell (http://localhost:5173) needs its Origin
  // and CORS preflight headers forwarded so Django can answer the preflight.
  'origin',
  'access-control-request-method',
  'access-control-request-headers',
])
const STRIP_RESPONSE_HEADERS = new Set(['server', 'x-powered-by', 'via'])

// The Cloudflare tunnel occasionally drops its edge connection for a moment;
// the edge answers 502 while the backend itself is fine. Retry idempotent
// reads only - a payment POST whose response was lost must never be repeated.
const READ_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

async function fetchWithRetry(target, init, method) {
  const attempts = READ_METHODS.has(method) ? 3 : 1
  let lastError
  for (let i = 0; i < attempts; i += 1) {
    try {
      const response = await fetch(target, init)
      if (!READ_METHODS.has(method) || ![502, 503, 504].includes(response.status)) {
        return response
      }
      lastError = new Error(`upstream ${response.status}`)
      if (i + 1 < attempts) {
        await new Promise((resolve) => setTimeout(resolve, 400 * (i + 1)))
      }
    } catch (error) {
      lastError = error
      if (i + 1 < attempts) {
        await new Promise((resolve) => setTimeout(resolve, 400 * (i + 1)))
      }
    }
  }
  throw lastError
}

export default {
  async fetch(request, env) {
    // Module Workers: `env` is a fetch-handler parameter, not a global.
    const ORIGIN = (env.ORIGIN || '').replace(/\/+$/, '')
    if (!ORIGIN) {
      return new Response('ORIGIN is not configured', { status: 500 })
    }
    const url = new URL(request.url)
    // /api/* for the SPA + Electron, /media/* for school logos and documents,
    // /releases/* for the Electron auto-updater feed - all same-origin.
    const FORWARDED_PREFIXES = ['/api/', '/media/', '/releases/']
    if (!FORWARDED_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) {
      return new Response('Not found', { status: 404 })
    }
    const target = new URL(url.pathname + url.search, ORIGIN)

    const headers = new Headers()
    for (const [name, value] of request.headers) {
      if (FORWARD_HEADERS.has(name.toLowerCase())) {
        headers.set(name, value)
      }
    }
    headers.set('host', target.hostname)
    headers.set('x-forwarded-host', 'sms.darkzhub.asia')
    headers.set('x-forwarded-proto', 'https')

    const init = { method: request.method, headers }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      init.body = await request.arrayBuffer()
    }

    const response = await fetchWithRetry(target, init, request.method)

    const responseHeaders = new Headers(response.headers)
    for (const name of STRIP_RESPONSE_HEADERS) {
      responseHeaders.delete(name)
    }
    // Mission P5 - the public origin must always present the baseline
    // security headers, including on proxied API/asset responses.
    responseHeaders.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    responseHeaders.set('X-Content-Type-Options', 'nosniff')
    responseHeaders.set('X-Frame-Options', 'DENY')

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    })
  },
}

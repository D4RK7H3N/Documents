/**
 * Static-asset Worker for sms-3 (sms.darkzhub.asia).
 *
 * Why this exists: the SPA HTML was being cached while the hashed files under
 * /assets/ are pruned on every deploy. A user with the tab open across a
 * deploy then held an index.html pointing at chunks that no longer existed,
 * and the SPA fallback answered with text/html, producing "Expected a
 * JavaScript-or-Wasm module script but the server responded with a MIME type
 * of text/html".
 *
 * Two separate caches are in play:
 *   - the browser, controlled by Cache-Control
 *   - Cloudflare's edge, controlled by Cloudflare-CDN-Cache-Control
 * Setting only Cache-Control left the edge serving a stale index.html
 * (CF-Cache-Status: HIT on a no-store response), so both are set explicitly.
 *
 * Content-hashed assets stay immutable and long-lived, and a missing asset now
 * returns a real 404 instead of being masked by the SPA fallback.
 */
const IMMUTABLE = /\/assets\/.+-[A-Za-z0-9_-]{6,}\.(js|css|woff2?|ttf|png|jpe?g|svg|webp|ico)$/i
const NO_STORE = 'no-store, no-cache, must-revalidate, max-age=0'
const ONE_YEAR = 'public, max-age=31536000, immutable'

export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request)
    const { pathname } = new URL(request.url)

    const contentType = response.headers.get('content-type') || ''
    const isDocument =
      pathname === '/' ||
      pathname.endsWith('.html') ||
      contentType.includes('text/html')

    // A hashed asset that resolves to HTML means it was pruned and the SPA
    // fallback swallowed the miss. Return a real 404 so the browser reports a
    // clear "chunk not found" instead of a confusing MIME type error.
    if (pathname.startsWith('/assets/') && contentType.includes('text/html')) {
      return new Response('Not found', {
        status: 404,
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Cache-Control': NO_STORE,
          'Cloudflare-CDN-Cache-Control': NO_STORE,
          'X-Content-Type-Options': 'nosniff',
        },
      })
    }

    if (isDocument) {
      const headers = new Headers(response.headers)
      headers.set('Cache-Control', NO_STORE)
      headers.set('Cloudflare-CDN-Cache-Control', NO_STORE)
      headers.set('X-Content-Type-Options', 'nosniff')
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      })
    }

    if (IMMUTABLE.test(pathname)) {
      const headers = new Headers(response.headers)
      headers.set('Cache-Control', ONE_YEAR)
      headers.set('Cloudflare-CDN-Cache-Control', ONE_YEAR)
      headers.set('X-Content-Type-Options', 'nosniff')
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      })
    }

    return response
  },
}

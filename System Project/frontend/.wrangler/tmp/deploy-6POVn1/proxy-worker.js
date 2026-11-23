// proxy-worker.js
var FORWARD_HEADERS = /* @__PURE__ */ new Set([
  "accept",
  "accept-encoding",
  "accept-language",
  "authorization",
  "content-type",
  "user-agent",
  "x-device-id",
  "x-device-previous-id"
]);
var STRIP_RESPONSE_HEADERS = /* @__PURE__ */ new Set(["server", "x-powered-by", "via"]);
var proxy_worker_default = {
  async fetch(request, env) {
    const ORIGIN = (env.ORIGIN || "").replace(/\/+$/, "");
    if (!ORIGIN) {
      return new Response("ORIGIN is not configured", { status: 500 });
    }
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) {
      return new Response("Not found", { status: 404 });
    }
    const target = new URL(url.pathname + url.search, ORIGIN);
    const headers = new Headers();
    for (const [name, value] of request.headers) {
      if (FORWARD_HEADERS.has(name.toLowerCase())) {
        headers.set(name, value);
      }
    }
    headers.set("host", target.hostname);
    headers.set("x-forwarded-host", "sms.darkzhub.asia");
    headers.set("x-forwarded-proto", "https");
    const init = { method: request.method, headers };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }
    const response = await fetch(target, init);
    const responseHeaders = new Headers(response.headers);
    for (const name of STRIP_RESPONSE_HEADERS) {
      responseHeaders.delete(name);
    }
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  }
};
export {
  proxy_worker_default as default
};
//# sourceMappingURL=proxy-worker.js.map

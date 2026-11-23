// ============================================================================
// middleware.js — Auth & CORS Middleware
// Cloudflare Workers runtime: no Express/Connect patterns — these are
// higher-order functions that wrap request handlers.
// ============================================================================

import { verifyToken } from './auth.js';

// ============================================================================
// CORS HEADERS
// ============================================================================
export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

/**
 * Handle CORS preflight (OPTIONS) request.
 */
export function handleOptions(request) {
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: CORS_HEADERS,
    });
  }
  return null;
}

/**
 * Wrap a response with CORS headers.
 */
export function withCORS(response) {
  const newHeaders = new Headers(response.headers);
  for (const [key, value] of Object.entries(CORS_HEADERS)) {
    newHeaders.set(key, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

/**
 * Create a JSON response with consistent shape.
 * { success: boolean, data?: any, error?: string }
 */
export function jsonResponse(data, status = 200) {
  const body = data.error
    ? { success: false, error: data.error }
    : { success: true, data };
  return withCORS(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

// ============================================================================
// AUTHENTICATION MIDDLEWARE
// ============================================================================

/**
 * Require a valid JWT token.
 * Extracts from Authorization: Bearer <token>
 * Attaches user info to request via the `env` using a closure pattern.
 *
 * Usage: wrap your handler: requireAuth(handler, env)
 */
export function requireAuth(handler) {
  return async (request, env, ctx) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return jsonResponse({ error: 'Missing or invalid authorization header' }, 401);
    }
    const token = authHeader.slice(7);
    try {
      const { payload } = await verifyToken(token, env.JWT_SECRET);
      // Attach user info to the request context
      request.user = {
        id: parseInt(payload.sub, 10),
        role: payload.role,
        name: payload.name,
      };
      return handler(request, env, ctx);
    } catch (err) {
      return jsonResponse({ error: 'Invalid or expired token' }, 401);
    }
  };
}

/**
 * Require specific role(s) for a route.
 * Must be used AFTER requireAuth.
 *
 * Usage: wrap your handler: requireRole('admin', 'cashier')(handler)
 */
export function requireRole(...roles) {
  return (handler) => {
    return (request, env, ctx) => {
      if (!request.user) {
        return jsonResponse({ error: 'Authentication required' }, 401);
      }
      if (!roles.includes(request.user.role)) {
        return jsonResponse({ error: 'Insufficient permissions' }, 403);
      }
      return handler(request, env, ctx);
    };
  };
}

/**
 * Parse JSON body from a request.
 */
export async function parseBody(request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}

/**
 * Parse URL query parameters.
 */
export function parseQuery(url) {
  const params = new URL(url).searchParams;
  const result = {};
  for (const [key, value] of params.entries()) {
    result[key] = value;
  }
  return result;
}

/**
 * Extract path parameter from URL pattern.
 * E.g. pattern '/api/enrollment/:studentId' matches '/api/enrollment/5'
 * Returns { studentId: '5' }
 */
export function matchRoute(pattern, url) {
  const patternParts = pattern.split('/');
  const urlParts = new URL(url).pathname.split('/');
  if (patternParts.length !== urlParts.length) return null;
  const params = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = urlParts[i];
    } else if (patternParts[i] !== urlParts[i]) {
      return null;
    }
  }
  return params;
}

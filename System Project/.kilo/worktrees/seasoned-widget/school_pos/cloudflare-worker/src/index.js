// ============================================================================
// SMS-2 Cloudflare Worker — Main Entry Point
// Sagay City College Inc. — School Management System
//
// RUNTIME NOTES:
//   - NO Node.js APIs (no fs, no buffer, no process.env at runtime)
//   - Use env.XYZ for environment variables / bindings
//   - Use Web Crypto API (crypto.subtle) not Node's crypto
//   - D1 binding available as env.DB
//   - R2 binding available as env.STORAGE
// ============================================================================

import { handleOptions, withCORS, jsonResponse, requireAuth, requireRole, matchRoute } from './middleware.js';
import { createEnrollment, getEnrollmentHistory, updateEnrollmentStatus } from './routes/enrollment.js';
import { recordPayment, getTuitionBreakdown, dailyReport } from './routes/tuition.js';
import { revenueSummary, revenueByCourse } from './routes/revenue.js';
import { checkin, checkout, getOccupancy } from './routes/dorm.js';
import { createToken, verifyPassword, hashPassword } from './auth.js';
import { queryOne, execute } from './db.js';

// ============================================================================
// REQUEST HANDLER — Main entry point for all requests
// ============================================================================
export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    const optionsResponse = handleOptions(request);
    if (optionsResponse) return optionsResponse;

    const url = new URL(request.url);
    const method = request.method;
    const path = url.pathname;

    try {
      // ======================================================================
      // AUTH ROUTES (no token required)
      // ======================================================================

      // POST /api/auth/login
      if (method === 'POST' && path === '/api/auth/login') {
        return await loginHandler(request, env);
      }

      // POST /api/auth/refresh
      if (method === 'POST' && path === '/api/auth/refresh') {
        return await refreshHandler(request, env);
      }

      // POST /api/auth/logout
      if (method === 'POST' && path === '/api/auth/logout') {
        return jsonResponse({ message: 'Logged out successfully. Discard your token.' });
      }

      // ======================================================================
      // ENROLLMENT ROUTES
      // ======================================================================

      // POST /api/enrollment/create
      if (method === 'POST' && path === '/api/enrollment/create') {
        return requireAuth(createEnrollment)(request, env, ctx);
      }

      // GET /api/enrollment/:studentId
      const enrollHistoryMatch = matchRoute('/api/enrollment/:studentId', request.url);
      if (method === 'GET' && enrollHistoryMatch) {
        request.params = enrollHistoryMatch;
        return requireAuth(getEnrollmentHistory)(request, env, ctx);
      }

      // PATCH /api/enrollment/:id/status
      const enrollStatusMatch = matchRoute('/api/enrollment/:id/status', request.url);
      if (method === 'PATCH' && enrollStatusMatch) {
        request.params = enrollStatusMatch;
        return requireAuth(updateEnrollmentStatus)(request, env, ctx);
      }

      // ======================================================================
      // TUITION / CASHIER ROUTES
      // ======================================================================

      // POST /api/tuition/payment
      if (method === 'POST' && path === '/api/tuition/payment') {
        return requireAuth(recordPayment)(request, env, ctx);
      }

      // GET /api/tuition/:studentId
      const tuitionMatch = matchRoute('/api/tuition/:studentId', request.url);
      if (method === 'GET' && tuitionMatch) {
        request.params = tuitionMatch;
        return requireAuth(getTuitionBreakdown)(request, env, ctx);
      }

      // GET /api/cashier/daily-report
      if (method === 'GET' && path === '/api/cashier/daily-report') {
        return requireAuth(dailyReport)(request, env, ctx);
      }

      // ======================================================================
      // REVENUE / REPORTING ROUTES
      // ======================================================================

      // GET /api/revenue/summary
      if (method === 'GET' && path === '/api/revenue/summary') {
        return requireAuth(revenueSummary)(request, env, ctx);
      }

      // GET /api/revenue/by-course
      if (method === 'GET' && path === '/api/revenue/by-course') {
        return requireAuth(revenueByCourse)(request, env, ctx);
      }

      // ======================================================================
      // DORM MANAGEMENT ROUTES
      // ======================================================================

      // POST /api/dorm/checkin
      if (method === 'POST' && path === '/api/dorm/checkin') {
        return requireAuth(requireRole('admin', 'dorm_manager')(checkin))(request, env, ctx);
      }

      // POST /api/dorm/checkout
      if (method === 'POST' && path === '/api/dorm/checkout') {
        return requireAuth(requireRole('admin', 'dorm_manager')(checkout))(request, env, ctx);
      }

      // GET /api/dorm/occupancy
      if (method === 'GET' && path === '/api/dorm/occupancy') {
        return requireAuth(getOccupancy)(request, env, ctx);
      }

      // ======================================================================
      // HEALTH CHECK
      // ======================================================================
      if (method === 'GET' && path === '/api/health') {
        return jsonResponse({
          status: 'ok',
          school: env.SCHOOL_NAME || 'Sagay City College Inc.',
          timestamp: new Date().toISOString(),
        });
      }

      // ======================================================================
      // 404 — Not Found
      // ======================================================================
      return jsonResponse({ error: `Route not found: ${method} ${path}` }, 404);

    } catch (err) {
      console.error('Unhandled error:', err);
      return jsonResponse({ error: 'Internal server error' }, 500);
    }
  },
};

// ============================================================================
// AUTH HANDLERS
// ============================================================================

/**
 * POST /api/auth/login
 * Body: { username, password }
 * Returns: { token, user: { id, username, role, full_name } }
 */
async function loginHandler(request, env) {
  try {
    const body = await request.json();
    const { username, password } = body || {};

    if (!username || !password) {
      return jsonResponse({ error: 'Username and password are required' }, 400);
    }

    const { result: user } = await queryOne(
      env.DB,
      'SELECT id, username, password_hash, role, full_name, is_active FROM users WHERE username = ?',
      username
    );

    if (!user) {
      return jsonResponse({ error: 'Invalid username or password' }, 401);
    }

    if (!user.is_active) {
      return jsonResponse({ error: 'Account is disabled. Contact administrator.' }, 403);
    }

    const valid = await verifyPassword(password, user.password_hash);
    if (!valid) {
      return jsonResponse({ error: 'Invalid username or password' }, 401);
    }

    const token = await createToken(user, env.JWT_SECRET, env.JWT_EXPIRY || '8h');

    return jsonResponse({
      token,
      user: {
        id: user.id,
        username: user.username,
        role: user.role,
        full_name: user.full_name,
      },
    });
  } catch (err) {
    console.error('Login error:', err);
    return jsonResponse({ error: 'Invalid request' }, 400);
  }
}

/**
 * POST /api/auth/refresh — Issue a new token.
 * Header: Authorization: Bearer <current_token>
 * Returns: { token }
 */
async function refreshHandler(request, env) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return jsonResponse({ error: 'Missing authorization header' }, 401);
  }

  try {
    const { verifyToken } = await import('./auth.js');
    const { payload } = await verifyToken(authHeader.slice(7), env.JWT_SECRET);

    const { result: user } = await queryOne(
      env.DB,
      'SELECT id, username, role, full_name FROM users WHERE id = ? AND is_active = 1',
      parseInt(payload.sub, 10)
    );

    if (!user) {
      return jsonResponse({ error: 'User not found or inactive' }, 401);
    }

    const newToken = await createToken(user, env.JWT_SECRET, env.JWT_EXPIRY || '8h');
    return jsonResponse({ token: newToken });
  } catch {
    return jsonResponse({ error: 'Invalid or expired token' }, 401);
  }
}

// ============================================================================
// revenue.js — Revenue & Reporting Module Routes
// ============================================================================

import { jsonResponse } from '../middleware.js';
import { query } from '../db.js';

/**
 * GET /api/revenue/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
 * Total collections in a date range, grouped by payment method and course.
 */
export async function revenueSummary(request, env, ctx) {
  const params = new URL(request.url).searchParams;
  const from = params.get('from');
  const to = params.get('to');
  if (!from || !to) {
    return jsonResponse({ error: 'from and to query parameters required (YYYY-MM-DD)' }, 400);
  }

  // Total collections
  const { results: totalResult } = await query(
    env.DB,
    `SELECT COALESCE(SUM(amount), 0) AS total
     FROM payments
     WHERE date(paid_at) >= ? AND date(paid_at) <= ?`,
    from,
    to
  );
  const total = totalResult?.[0]?.total || 0;

  // By payment method
  const { results: byMethod } = await query(
    env.DB,
    `SELECT payment_method, COUNT(*) AS count, SUM(amount) AS total
     FROM payments
     WHERE date(paid_at) >= ? AND date(paid_at) <= ?
     GROUP BY payment_method
     ORDER BY total DESC`,
    from,
    to
  );

  // By course (join with students via tuition)
  const { results: byCourse } = await query(
    env.DB,
    `SELECT s.course, COUNT(*) AS count, SUM(p.amount) AS total
     FROM payments p
     JOIN tuition t ON t.id = p.tuition_id
     JOIN students s ON s.id = t.student_id
     WHERE date(p.paid_at) >= ? AND date(p.paid_at) <= ?
     GROUP BY s.course
     ORDER BY total DESC`,
    from,
    to
  );

  // Daily breakdown
  const { results: daily } = await query(
    env.DB,
    `SELECT date(paid_at) AS day, COUNT(*) AS count, SUM(amount) AS total
     FROM payments
     WHERE date(paid_at) >= ? AND date(paid_at) <= ?
     GROUP BY day
     ORDER BY day ASC`,
    from,
    to
  );

  return jsonResponse({
    from,
    to,
    total_collections: total,
    by_payment_method: byMethod || [],
    by_course: byCourse || [],
    daily_breakdown: daily || [],
  });
}

/**
 * GET /api/revenue/by-course — Revenue breakdown by course/year level.
 * Shows total collected per course, student count, and average payment.
 */
export async function revenueByCourse(request, env, ctx) {
  const { results: data } = await query(
    env.DB,
    `SELECT
       s.course,
       s.year_level,
       COUNT(DISTINCT s.id) AS student_count,
       COUNT(p.id) AS payment_count,
       COALESCE(SUM(p.amount), 0) AS total_collected,
       COALESCE(SUM(p.amount) / NULLIF(COUNT(DISTINCT s.id), 0), 0) AS avg_per_student
     FROM students s
     LEFT JOIN tuition t ON t.student_id = s.id
     LEFT JOIN payments p ON p.tuition_id = t.id
     GROUP BY s.course, s.year_level
     ORDER BY s.course, s.year_level`
  );

  return jsonResponse(data || []);
}

// ============================================================================
// tuition.js — Tuition & Cashier Module Routes
//
// MONEY HANDLING: All amounts are in centavos (integer).
//   total_amount, amount_paid, balance are INTEGER columns.
//   ₱1,500.00 = 150000 centavos.
//   This avoids ALL floating-point rounding errors in tuition math.
// ============================================================================

import { jsonResponse, parseBody } from '../middleware.js';
import { query, queryOne, execute, nextORNumber } from '../db.js';

/**
 * POST /api/tuition/payment — Record a payment against a student's tuition.
 * Auto-updates the tuition balance.
 * If no tuition record exists, creates one (initial setup).
 *
 * Body: {
 *   student_id,
 *   school_year?,
 *   semester?,
 *   total_amount?,    // centavos (for initial setup)
 *   amount,           // centavos — payment amount
 *   payment_method,
 *   reference_no?,
 *   notes?
 * }
 */
export async function recordPayment(request, env, ctx) {
  const body = await parseBody(request);
  if (!body) return jsonResponse({ error: 'Invalid JSON body' }, 400);

  const { student_id, amount, payment_method, reference_no, notes, total_amount, school_year, semester } = body;

  if (!student_id || amount == null) {
    return jsonResponse({ error: 'student_id and amount are required' }, 400);
  }

  const userId = request.user.id;
  const payAmount = parseInt(amount, 10);
  if (isNaN(payAmount) || payAmount <= 0) {
    return jsonResponse({ error: 'Amount must be a positive integer (centavos)' }, 400);
  }

  // Find or create tuition record
  let tuitionId;
  let { result: tuition } = await queryOne(
    env.DB,
    'SELECT id, total_amount, amount_paid, balance FROM tuition WHERE student_id = ? ORDER BY id DESC LIMIT 1',
    parseInt(student_id, 10)
  );

  if (!tuition) {
    // Initial setup: create tuition + enrollment if needed
    if (!total_amount || !school_year || !semester) {
      return jsonResponse({
        error: 'No existing tuition found. Provide total_amount, school_year, and semester for initial setup.',
      }, 400);
    }

    // Find or create enrollment
    const { result: enrollment } = await queryOne(
      env.DB,
      'SELECT id FROM enrollments WHERE student_id = ? AND school_year = ? AND semester = ?',
      parseInt(student_id, 10),
      school_year,
      semester
    );
    let enrollmentId;
    if (enrollment) {
      enrollmentId = enrollment.id;
    } else {
      const { meta: enrollResult } = await execute(
        env.DB,
        'INSERT INTO enrollments (student_id, school_year, semester) VALUES (?, ?, ?)',
        parseInt(student_id, 10),
        school_year,
        semester
      );
      enrollmentId = enrollResult?.meta?.last_row_id;
    }

    const totalCents = parseInt(total_amount, 10);
    const { meta: insertTuition } = await execute(
      env.DB,
      'INSERT INTO tuition (student_id, enrollment_id, total_amount, amount_paid, balance) VALUES (?, ?, ?, 0, ?)',
      parseInt(student_id, 10),
      enrollmentId,
      totalCents,
      totalCents
    );
    tuitionId = insertTuition?.meta?.last_row_id;
    tuition = { id: tuitionId, total_amount: totalCents, amount_paid: 0, balance: totalCents };
  } else {
    tuitionId = tuition.id;
  }

  // Validate payment does not exceed balance
  if (payAmount > tuition.balance) {
    return jsonResponse({
      error: `Payment amount (${payAmount}) exceeds remaining balance (${tuition.balance})`,
    }, 400);
  }

  // Generate OR number
  const orNumber = await nextORNumber(env.DB);

  // Record the payment
  const { meta: payResult } = await execute(
    env.DB,
    `INSERT INTO payments (tuition_id, amount, payment_method, or_number, reference_no, notes, received_by)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
    tuitionId,
    payAmount,
    payment_method || 'Cash',
    orNumber,
    reference_no || null,
    notes || null,
    userId
  );
  const paymentId = payResult?.meta?.last_row_id;

  // Update tuition balance
  const newAmountPaid = tuition.amount_paid + payAmount;
  const newBalance = tuition.total_amount - newAmountPaid;
  await execute(
    env.DB,
    'UPDATE tuition SET amount_paid = ?, balance = ? WHERE id = ?',
    newAmountPaid,
    newBalance,
    tuitionId
  );

  return jsonResponse({
    payment_id: paymentId,
    or_number: orNumber,
    tuition_id: tuitionId,
    amount: payAmount,
    amount_paid: newAmountPaid,
    balance: newBalance,
    message: 'Payment recorded successfully',
  }, 201);
}

/**
 * GET /api/tuition/:studentId — Get tuition breakdown and payment history.
 * Returns: student info, tuition summary, payment list with remaining balance.
 */
export async function getTuitionBreakdown(request, env, ctx) {
  const studentId = request.params?.studentId;
  if (!studentId) return jsonResponse({ error: 'Student ID required' }, 400);

  // Student info
  const { result: student } = await queryOne(
    env.DB,
    'SELECT id, student_number, full_name, course, year_level FROM students WHERE id = ?',
    parseInt(studentId, 10)
  );
  if (!student) return jsonResponse({ error: 'Student not found' }, 404);

  // Tuition records
  const { results: tuitionRecords } = await query(
    env.DB,
    `SELECT t.*, e.school_year, e.semester
     FROM tuition t
     JOIN enrollments e ON e.id = t.enrollment_id
     WHERE t.student_id = ?
     ORDER BY t.created_at DESC`,
    parseInt(studentId, 10)
  );

  // Payment history for each tuition record
  let allPayments = [];
  for (const t of tuitionRecords || []) {
    const { results: payments } = await query(
      env.DB,
      `SELECT p.*, u.full_name AS received_by_name
       FROM payments p
       LEFT JOIN users u ON u.id = p.received_by
       WHERE p.tuition_id = ?
       ORDER BY p.paid_at ASC`,
      t.id
    );
    // Calculate remaining balance
    let remainingBalance = t.total_amount;
    for (const pmt of payments || []) {
      remainingBalance -= pmt.amount;
      pmt.remaining_balance = remainingBalance;
    }
    allPayments = allPayments.concat(payments || []);
  }

  return jsonResponse({
    student,
    tuition: tuitionRecords || [],
    payments: allPayments,
  });
}

/**
 * GET /api/cashier/daily-report?date=YYYY-MM-DD — Daily collection summary.
 * Defaults to today if no date provided.
 */
export async function dailyReport(request, env, ctx) {
  const params = new URL(request.url).searchParams;
  const date = params.get('date') || new Date().toISOString().split('T')[0];

  const { results: payments } = await query(
    env.DB,
    `SELECT p.*, u.full_name AS received_by_name, t.student_id, s.full_name AS student_name
     FROM payments p
     JOIN tuition t ON t.id = p.tuition_id
     JOIN students s ON s.id = t.student_id
     JOIN users u ON u.id = p.received_by
     WHERE date(p.paid_at) = ?
     ORDER BY p.paid_at ASC`,
    date
  );

  // Summary stats
  const total = (payments || []).reduce((sum, p) => sum + p.amount, 0);
  const byMethod = {};
  const byCourse = {};
  for (const p of payments || []) {
    byMethod[p.payment_method] = (byMethod[p.payment_method] || 0) + p.amount;
    byCourse[p.student_course || 'Unknown'] = (byCourse[p.student_course || 'Unknown'] || 0) + p.amount;
  }

  // Get student course info
  const studentIds = [...new Set((payments || []).map(p => p.student_id))];
  const courseByStudent = {};
  if (studentIds.length > 0) {
    const placeholders = studentIds.map(() => '?').join(',');
    const { results: students } = await query(
      env.DB,
      `SELECT id, course FROM students WHERE id IN (${placeholders})`,
      ...studentIds
    );
    for (const s of students || []) {
      courseByStudent[s.id] = s.course;
    }
  }

  // Recalculate byCourse with actual course names
  const byCourseFinal = {};
  for (const p of payments || []) {
    const course = courseByStudent[p.student_id] || 'Unknown';
    byCourseFinal[course] = (byCourseFinal[course] || 0) + p.amount;
  }

  return jsonResponse({
    date,
    total_collections: total,
    transaction_count: (payments || []).length,
    by_payment_method: byMethod,
    by_course: byCourseFinal,
    payments: payments || [],
  });
}

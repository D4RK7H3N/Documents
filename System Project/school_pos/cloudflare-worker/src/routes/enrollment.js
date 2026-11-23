// ============================================================================
// enrollment.js — Enrollment Module Routes
// ============================================================================

import { jsonResponse, parseBody } from '../middleware.js';
import { query, queryOne, execute } from '../db.js';

/**
 * POST /api/enrollment/create — Enroll a student for a school year/semester.
 * If the student doesn't exist, creates them first.
 * Body: { student_number, full_name, course, year_level, school_year, semester }
 */
export async function createEnrollment(request, env, ctx) {
  const body = await parseBody(request);
  if (!body) return jsonResponse({ error: 'Invalid JSON body' }, 400);

  const { student_number, full_name, course, year_level, school_year, semester } = body;
  if (!student_number || !school_year || !semester) {
    return jsonResponse({ error: 'student_number, school_year, and semester are required' }, 400);
  }

  // Find or create student
  const { result: existingStudent } = await queryOne(
    env.DB,
    'SELECT id FROM students WHERE student_number = ?',
    student_number
  );
  let studentId;
  if (existingStudent) {
    studentId = existingStudent.id;
  } else {
    if (!full_name || !course || !year_level) {
      return jsonResponse({ error: 'full_name, course, and year_level required for new students' }, 400);
    }
    const { meta: insertResult } = await execute(
      env.DB,
      'INSERT INTO students (student_number, full_name, course, year_level, enrolled_at) VALUES (?, ?, ?, ?, date(\'now\'))',
      student_number,
      full_name,
      course,
      year_level
    );
    studentId = insertResult?.meta?.last_row_id;
    if (!studentId) return jsonResponse({ error: 'Failed to create student' }, 500);
  }

  // Check for duplicate enrollment
  const { result: duplicate } = await queryOne(
    env.DB,
    'SELECT id FROM enrollments WHERE student_id = ? AND school_year = ? AND semester = ?',
    studentId,
    school_year,
    semester
  );
  if (duplicate) {
    return jsonResponse({ error: 'Student already enrolled for this school year and semester' }, 409);
  }

  // Create enrollment
  const { meta: enrollResult } = await execute(
    env.DB,
    'INSERT INTO enrollments (student_id, school_year, semester) VALUES (?, ?, ?)',
    studentId,
    school_year,
    semester
  );
  const enrollmentId = enrollResult?.meta?.last_row_id;

  return jsonResponse({
    student_id: studentId,
    enrollment_id: enrollmentId,
    message: 'Enrolled successfully',
  }, 201);
}

/**
 * GET /api/enrollment/:studentId — Get enrollment history for a student.
 */
export async function getEnrollmentHistory(request, env, ctx) {
  const studentId = request.params?.studentId;
  if (!studentId) return jsonResponse({ error: 'Student ID required' }, 400);

  const { results: enrollments } = await query(
    env.DB,
    `SELECT e.*, s.student_number, s.full_name, s.course, s.year_level
     FROM enrollments e
     JOIN students s ON s.id = e.student_id
     WHERE e.student_id = ?
     ORDER BY e.school_year DESC, e.semester DESC`,
    parseInt(studentId, 10)
  );

  return jsonResponse(enrollments || []);
}

/**
 * PATCH /api/enrollment/:id/status — Update enrollment status.
 * Body: { status: 'Withdrawn' | 'Completed' }
 */
export async function updateEnrollmentStatus(request, env, ctx) {
  const enrollmentId = request.params?.id;
  if (!enrollmentId) return jsonResponse({ error: 'Enrollment ID required' }, 400);

  const body = await parseBody(request);
  if (!body || !body.status) return jsonResponse({ error: 'status field required' }, 400);

  const validStatuses = ['Enrolled', 'Withdrawn', 'Completed'];
  if (!validStatuses.includes(body.status)) {
    return jsonResponse({ error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` }, 400);
  }

  const { meta } = await execute(
    env.DB,
    'UPDATE enrollments SET status = ? WHERE id = ?',
    body.status,
    parseInt(enrollmentId, 10)
  );

  if (meta?.meta?.changes === 0) {
    return jsonResponse({ error: 'Enrollment not found' }, 404);
  }

  return jsonResponse({ message: `Enrollment status updated to ${body.status}` });
}

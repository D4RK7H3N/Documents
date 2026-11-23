// ============================================================================
// dorm.js — Dorm Management Module Routes
// ============================================================================

import { jsonResponse, parseBody } from '../middleware.js';
import { query, queryOne, execute } from '../db.js';

/**
 * POST /api/dorm/checkin — Assign a student to a room.
 * Body: { student_id, room_number, building? }
 * Prevents double-checkin (student must be checked out first).
 */
export async function checkin(request, env, ctx) {
  const body = await parseBody(request);
  if (!body) return jsonResponse({ error: 'Invalid JSON body' }, 400);

  const { student_id, room_number, building } = body;
  if (!student_id || !room_number) {
    return jsonResponse({ error: 'student_id and room_number are required' }, 400);
  }

  // Verify student exists
  const { result: student } = await queryOne(
    env.DB,
    'SELECT id, full_name FROM students WHERE id = ?',
    parseInt(student_id, 10)
  );
  if (!student) return jsonResponse({ error: 'Student not found' }, 404);

  // Check if student is already checked in
  const { result: activeResident } = await queryOne(
    env.DB,
    'SELECT id FROM dorm_residents WHERE student_id = ? AND status = \'Checked-in\'',
    parseInt(student_id, 10)
  );
  if (activeResident) {
    return jsonResponse({ error: 'Student is already checked in. Check them out first.' }, 409);
  }

  // Check room capacity (if needed — assumed max 2 per room)
  const { result: roomOccupancy } = await queryOne(
    env.DB,
    'SELECT COUNT(*) AS count FROM dorm_residents WHERE room_number = ? AND status = \'Checked-in\'',
    room_number
  );
  if (roomOccupancy && roomOccupancy.count >= 2) {
    return jsonResponse({ error: 'Room is full (max 2 residents)' }, 409);
  }

  const { meta } = await execute(
    env.DB,
    'INSERT INTO dorm_residents (student_id, room_number, building) VALUES (?, ?, ?)',
    parseInt(student_id, 10),
    room_number,
    building || 'Main'
  );

  return jsonResponse({
    id: meta?.meta?.last_row_id,
    student_id: parseInt(student_id, 10),
    student_name: student.full_name,
    room_number,
    status: 'Checked-in',
    message: 'Check-in successful',
  }, 201);
}

/**
 * POST /api/dorm/checkout — Release a student's room.
 * Body: { student_id }
 * Sets check_out_date and changes status to 'Checked-out'.
 */
export async function checkout(request, env, ctx) {
  const body = await parseBody(request);
  if (!body || !body.student_id) {
    return jsonResponse({ error: 'student_id is required' }, 400);
  }

  const { result: resident } = await queryOne(
    env.DB,
    'SELECT id FROM dorm_residents WHERE student_id = ? AND status = \'Checked-in\'',
    parseInt(body.student_id, 10)
  );
  if (!resident) {
    return jsonResponse({ error: 'Student is not currently checked in' }, 404);
  }

  await execute(
    env.DB,
    'UPDATE dorm_residents SET status = \'Checked-out\', check_out_date = date(\'now\') WHERE id = ?',
    resident.id
  );

  return jsonResponse({ message: 'Check-out successful', resident_id: resident.id });
}

/**
 * GET /api/dorm/occupancy — Current occupancy per room/building.
 * Shows checked-in residents grouped by room.
 */
export async function getOccupancy(request, env, ctx) {
  // Per-room breakdown
  const { results: byRoom } = await query(
    env.DB,
    `SELECT dr.room_number, dr.building, COUNT(*) AS residents, GROUP_CONCAT(s.full_name, ', ') AS resident_names
     FROM dorm_residents dr
     JOIN students s ON s.id = dr.student_id
     WHERE dr.status = 'Checked-in'
     GROUP BY dr.room_number, dr.building
     ORDER BY dr.building, dr.room_number`
  );

  // Summary stats
  const { results: summary } = await query(
    env.DB,
    `SELECT
       COUNT(*) AS total_residents,
       COUNT(DISTINCT room_number) AS occupied_rooms,
       COUNT(DISTINCT building) AS total_buildings
     FROM dorm_residents
     WHERE status = 'Checked-in'`
  );

  // Per-building breakdown
  const { results: byBuilding } = await query(
    env.DB,
    `SELECT building, COUNT(*) AS residents, COUNT(DISTINCT room_number) AS rooms_used
     FROM dorm_residents
     WHERE status = 'Checked-in'
     GROUP BY building
     ORDER BY building`
  );

  return jsonResponse({
    summary: summary?.[0] || { total_residents: 0, occupied_rooms: 0, total_buildings: 0 },
    by_room: byRoom || [],
    by_building: byBuilding || [],
  });
}

// ============================================================================
// db.js — D1 Database Helpers
// Cloudflare Workers runtime: uses env.DB binding (no Node.js modules)
// ============================================================================

/**
 * Execute a query with optional bindings.
 * Returns { results, success, error }
 */
export async function query(db, sql, ...bindings) {
  try {
    const stmt = db.prepare(sql);
    const result = await stmt.bind(...bindings).all();
    return { results: result.results, success: true, error: null };
  } catch (err) {
    return { results: null, success: false, error: err.message };
  }
}

/**
 * Execute a single-row query (returns first row or null).
 */
export async function queryOne(db, sql, ...bindings) {
  try {
    const stmt = db.prepare(sql);
    const result = await stmt.bind(...bindings).first();
    return { result, success: true, error: null };
  } catch (err) {
    return { result: null, success: false, error: err.message };
  }
}

/**
 * Execute a raw write (INSERT/UPDATE/DELETE). Returns meta info.
 */
export async function execute(db, sql, ...bindings) {
  try {
    const stmt = db.prepare(sql);
    const result = await stmt.bind(...bindings).run();
    return { meta: result, success: true, error: null };
  } catch (err) {
    return { meta: null, success: false, error: err.message };
  }
}

/**
 * Generate the next sequential OR (Official Receipt) number.
 * Format: OR-YYYY-NNNNN (padded to 5 digits)
 * Uses a sequences table with row-level locking via INSERT OR REPLACE.
 */
export async function nextORNumber(db) {
  const year = new Date().getFullYear().toString();
  const { result: seq } = await queryOne(
    db,
    'SELECT value FROM sequences WHERE name = ? AND year = ?',
    'or_number',
    year
  );
  const nextVal = (seq?.value ?? 0) + 1;
  await execute(
    db,
    'INSERT OR REPLACE INTO sequences (name, year, value) VALUES (?, ?, ?)',
    'or_number',
    year,
    nextVal
  );
  const padded = String(nextVal).padStart(5, '0');
  return `OR-${year}-${padded}`;
}

/**
 * Format centavos to PHP display string.
 * E.g. 150000 → "₱1,500.00"
 */
export function formatPHP(centavos) {
  const peso = (centavos / 100).toFixed(2);
  return `₱${Number(peso).toLocaleString('en-PH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Parse PHP string to centavos. Returns 0 on invalid input.
 * E.g. "1,500.50" → 150050
 */
export function parsePHP(value) {
  if (typeof value === 'number') return Math.round(value * 100);
  const cleaned = String(value).replace(/[₱, ]/g, '').trim();
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : Math.round(num * 100);
}

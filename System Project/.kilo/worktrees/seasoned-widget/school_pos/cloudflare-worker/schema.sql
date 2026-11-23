-- ============================================================================
-- SMS-2 Schema Migration (Cloudflare D1 / SQLite)
-- Sagay City College Inc. — School Management System
--
-- MONEY HANDLING STRATEGY (CRITICAL):
--   All monetary values are stored as INTEGER (centavos) to avoid
--   floating-point rounding errors. PHP amounts are multiplied by 100.
--   Examples:
--     ₱1,500.00 → stored as 150000
--     ₱250.50  → stored as 25050
--   Display logic: divide by 100, format to 2 decimal places.
--
-- SQLITE/D1 LIMITATIONS:
--   - No DECIMAL/NUMERIC types — use INTEGER for money (see above)
--   - No BOOLEAN type — use INTEGER (0/1)
--   - No DATETIME type — use TEXT (ISO 8601: '2026-07-07T14:30:00Z')
--   - No ENUM type — use TEXT with CHECK constraints
--   - Foreign keys must be enabled via PRAGMA foreign_keys = ON
--   - D1 max SQL statement size: ~1MB per statement
--   - D1 max bindings per query: ~100
-- ============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,              -- PBKDF2-SHA256 hex string
    role          TEXT    NOT NULL CHECK (role IN ('admin', 'cashier', 'registrar', 'dorm_manager')),
    full_name     TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,    -- 0 = disabled login
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- SUBJECTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS subjects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT    NOT NULL UNIQUE,           -- e.g. 'MATH101'
    name       TEXT    NOT NULL,                  -- e.g. 'College Algebra'
    units      INTEGER NOT NULL DEFAULT 3,
    course_id  TEXT,                              -- FK to course code (denormalized for simplicity)
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_subjects_code ON subjects(code);

-- ============================================================================
-- STUDENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_number  TEXT    NOT NULL UNIQUE,      -- e.g. 'SCC-2026-00001'
    full_name       TEXT    NOT NULL,
    course          TEXT    NOT NULL,              -- e.g. 'BSIT', 'BSCrim', 'Bundled - 1st Year Tesda Accredited'
    year_level      TEXT    NOT NULL,              -- e.g. '1st Year', '2nd Year', 'Grade 11', 'Grade 12'
    status          TEXT    NOT NULL DEFAULT 'Enrolled'
                          CHECK (status IN ('Enrolled','Drop-out','Withdrawn','Graduated','Graduating')),
    enrolled_at     TEXT,                          -- date of initial enrollment
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_students_number ON students(student_number);
CREATE INDEX idx_students_course ON students(course);
CREATE INDEX idx_students_status ON students(status);

-- ============================================================================
-- ENROLLMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS enrollments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    school_year   TEXT    NOT NULL,               -- e.g. '2025-2026'
    semester      TEXT    NOT NULL CHECK (semester IN ('1st', '2nd', 'Summer')),
    status        TEXT    NOT NULL DEFAULT 'Enrolled'
                          CHECK (status IN ('Enrolled','Withdrawn','Completed')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE UNIQUE INDEX idx_enrollments_unique ON enrollments(student_id, school_year, semester);
CREATE INDEX idx_enrollments_year_sem ON enrollments(school_year, semester);

-- ============================================================================
-- TUITION TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS tuition (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    enrollment_id   INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    total_amount    INTEGER NOT NULL,             -- in centavos (e.g. 150000 = ₱1,500.00)
    amount_paid     INTEGER NOT NULL DEFAULT 0,   -- in centavos
    balance         INTEGER NOT NULL,             -- computed: total_amount - amount_paid
    due_date        TEXT,                          -- ISO 8601 date
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_tuition_student ON tuition(student_id);
CREATE INDEX idx_tuition_enrollment ON tuition(enrollment_id);
CREATE INDEX idx_tuition_due ON tuition(due_date);

-- ============================================================================
-- PAYMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tuition_id      INTEGER NOT NULL REFERENCES tuition(id) ON DELETE CASCADE,
    amount          INTEGER NOT NULL,             -- in centavos
    payment_method  TEXT    NOT NULL CHECK (payment_method IN ('Cash', 'GCash', 'Bank Transfer', 'Check', 'Other')),
    or_number       TEXT    NOT NULL UNIQUE,       -- Official Receipt number: 'OR-YYYY-NNNNN'
    reference_no    TEXT,                          -- optional reference from GCash/bank
    notes           TEXT,
    received_by     INTEGER NOT NULL REFERENCES users(id),
    paid_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_payments_tuition ON payments(tuition_id);
CREATE INDEX idx_payments_or ON payments(or_number);
CREATE INDEX idx_payments_date ON payments(paid_at);
CREATE INDEX idx_payments_method ON payments(payment_method);

-- ============================================================================
-- ASSESSMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    enrollment_id   INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    subject_id      INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    tuition_fee     INTEGER NOT NULL DEFAULT 0,   -- in centavos
    misc_fee        INTEGER NOT NULL DEFAULT 0,   -- in centavos
    lab_fee         INTEGER NOT NULL DEFAULT 0,   -- in centavos
    total           INTEGER NOT NULL,             -- computed: tuition_fee + misc_fee + lab_fee
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_assessments_student ON assessments(student_id);
CREATE INDEX idx_assessments_enrollment ON assessments(enrollment_id);

-- ============================================================================
-- DORM RESIDENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS dorm_residents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    room_number     TEXT    NOT NULL,              -- e.g. 'Bldg-A-101'
    building        TEXT    NOT NULL DEFAULT 'Main',
    check_in_date   TEXT    NOT NULL DEFAULT (date('now')),
    check_out_date  TEXT,
    status          TEXT    NOT NULL DEFAULT 'Checked-in'
                          CHECK (status IN ('Checked-in', 'Checked-out')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_dorm_student ON dorm_residents(student_id);
CREATE INDEX idx_dorm_room ON dorm_residents(room_number);
CREATE INDEX idx_dorm_status ON dorm_residents(status);

-- ============================================================================
-- SEQUENCE TABLE (for OR number generation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sequences (
    name   TEXT PRIMARY KEY,                       -- e.g. 'or_number'
    year   TEXT NOT NULL,                          -- e.g. '2026'
    value  INTEGER NOT NULL DEFAULT 0
);

-- ============================================================================
-- SEED DATA: Default admin user
-- WARNING: Generate a real PBKDF2 hash BEFORE applying this schema.
--
-- The hash format is: salt_hex:hash_hex
--   algorithm: PBKDF2-SHA256
--   iterations: 100000
--   salt: 16 random bytes (hex)
--   dkLen: 32 bytes (64 hex chars)
--
-- To generate a real hash, run the Worker project's hashPassword() once:
--   node -e "const {hashPassword} = require('./src/auth.js'); hashPassword('admin123').then(console.log)"
-- Then replace the placeholder below with the output.
--
-- Example (replace with your real hash):
-- INSERT OR IGNORE INTO users (username, password_hash, role, full_name)
-- VALUES ('admin', 'REAL_HASH_HERE', 'admin', 'System Administrator');
-- ============================================================================

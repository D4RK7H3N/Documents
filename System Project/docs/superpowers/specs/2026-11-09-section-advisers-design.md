# Configurable Advisers for Sections — Design (option C)

Date: 2026-11-09
Status: Approved (user chose C in session)

## Goal

A dedicated **Advisers** manager inside School Config (Settings page) — separate
from the student-list-print signatory rows. Both the student list prints and
the cashier settlement panel resolve each section's adviser from this manager,
so advisers are entered once and reused everywhere. The existing free-typed
per-student adviser stays only as a fallback when the section has none.

## Backend

### Model (`tracks` app)

- **Adviser** — `full_name` CharField(120, unique), `is_active` Boolean
  (default True). Registered in Django admin.
- **Section** gains `adviser` FK → Adviser, `null=True, blank=True`,
  `on_delete=SET_NULL`.

### Migration & backfill

- Add Adviser table + nullable Section.adviser column.
- Data step: seed Adviser rows from the distinct non-empty names in existing
  `list_print_signatories` rows whose label is "Adviser" plus distinct
  `Student.adviser` values, and link sections where unambiguous — the current
  per-section adviser configuration is preserved, not discarded.

### API

- Advisers: `GET /api/advisers/` for all authenticated staff (dropdowns);
  create/update/deactivate restricted to **superuser** (the `IsSuperUser` gate
  added with the security hardening).
- Sections: serializer exposes `adviser` (id) + `adviser_name`; create/update
  accepts `adviser`.
- Adviser resolution (shared helper): for a student →
  1. their section's adviser, else
  2. the student's own typed `adviser` field.
- Consumers: cashier settlement context, tuition/SOA printables, and the
  student-list print's adviser signature line (Department Head / Principal
  signatory rows keep working unchanged from `list_print_signatories`).

## Frontend

- **Settings page (School Config)**: new "Advisers" card above the signatory
  editor — list, add, edit name, deactivate. Manage controls visible to
  superadmins; the list itself is readable by all staff for dropdowns.
- **Sections page**: adviser dropdown (sourced from `/api/advisers/`) in the
  section create/edit modal; adviser shown in the section table and print.
  The listing is also reorganized into **grade-level groups** — each section
  appears under a heading for its grade/year (Grade 11, Grade 12, 1st Year,
  2nd Year), and the add form slots the new section into its grade group.

### Section ↔ Strand/Course link (user-requested extension)

The Add Section modal's "Track" input is currently free text that is not
saved — the Section model has no track link. Sections gain real links:

- `Section.strand` FK → `tracks.Strand` (SHS sections: STEM, ABM, …),
  nullable, SET_NULL.
- `Section.course` FK → `tracks.Course` (Bundled/College sections),
  nullable, SET_NULL.
- In the Add/Edit modal, choosing the Grade Level drives the next dropdown:
  Grade 11/12 → **Strand** list (active SHS strands); 1st/2nd Year →
  **Course** list (active BUN courses). The chosen strand/course saves with
  the section and shows in the grade-grouped listing.
- **Cashier settlement panel** and all adviser-bearing printables: adviser
  comes from the resolution helper — no cashier action needed.

## Error handling

- Removing an adviser never deletes sections (SET_NULL); deactivation only
  hides it from dropdowns.
- Duplicate names blocked by the unique constraint with a friendly message.

## Testing

- Backend: adviser CRUD permissions (staff list OK, staff write 403); section
  save with adviser; resolution order (section adviser → student fallback);
  list-print signature block still renders Department Head / Principal rows.
- Manual: change a section's adviser → cashier panel and student list print
  reflect it on next load.

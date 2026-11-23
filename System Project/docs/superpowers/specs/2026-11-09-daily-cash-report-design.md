# Daily Collection & Disbursement Report — Design

Date: 2026-11-09
Status: Approved (user confirmed in session)

## Goal

A new **Daily Report** tab in the Cashier page that reproduces the school's
printed "DAILY COLLECTION & DISBURSEMENT REPORT" (Excel layout) from live
register data: collections grouped by fee type, disbursements deducted, a cash
denomination count, and a printable A4 sheet with signature lines.

## Core rule: the clock is the cutoff

- A report covers **from the close of the cashier's previous report up to the
  exact moment Generate is pressed** (`period_start` → `generated_at`).
  `period_start` is the previous report's `generated_at` for the same user,
  or midnight of the report date when there is none.
- No configured cutoff time. Money recorded after a report is printed lands in
  the next report automatically.
- Report date label = calendar date of generation. One saved report per user
  per date; regenerating overwrites it.

## Backend (Django, `cashier` app)

### Models

**Disbursement** — logged during the day as expenses happen:
- `date` DateField (default today)
- `description` CharField(200)
- `amount` Decimal(12,2)
- `created_by` FK User
- `created_at` auto

**DailyCashReport** — frozen snapshot, one per user per date:
- `date` DateField, `prepared_by` FK User, unique together `(prepared_by, date)`
- `period_start`, `generated_at` DateTimeField
- `collections` JSON — `[{description, amount, source}]`
- `disbursements` JSON — `[{description, amount}]`
- `denominations` JSON — `{1000, 500, 200, 100, 50, 20, coins}` quantities
  (coins stored as amount, others as bill counts)
- `total_collection`, `total_disbursement`, `net_amount`, `counted_total`,
  `difference` Decimal(12,2) — all computed server-side

### Collections auto-grouping

All money-in where `created_by = prepared_by` and
`period_start < created_at <= generated_at`:

| Source | Row label |
|---|---|
| TuitionPayment | "Tuition Fees" |
| TourPayment | "TOUR - <tour name>" |
| Charge payments | "<charge type>" (e.g. Type B - Bundled, Good Moral) |
| POS sale items | product name (e.g. ID Card - SHS) |
| Assessment / Dorm / Graduation payments | their type/event label |
| Walk-in / general payments | payment_type |

Plus **manual rows** typed by the cashier before generating (ephemeral — they
exist only inside the report snapshot).

### API (DRF, `IsAuthenticated`, scoped to `request.user`)

- `GET /api/cash-reports/preview/?date=YYYY-MM-DD` → period_start, auto
  collections, disbursements for the day, totals.
- `POST /api/cash-reports/` → body: `{date, manual_rows[], denominations}` →
  snapshots and saves (overwrites same user+date), returns the report.
- `GET /api/cash-reports/?date=YYYY-MM-DD` → saved report (for reprint).
- `GET|POST /api/disbursements/?date=`, `DELETE /api/disbursements/<id>/`
  (own records only).

### School Config

New field `report_checked_by` (CharField, blank) — the "Checked by" name on
the printed sheet. "Prepared by" is the logged-in user automatically;
"Received/Approved by" stays a blank line for wet signature.

## Frontend (Cashier page, new tab)

- Date picker (defaults today) → collections table: auto rows (read-only) +
  "Add row" for manual items → disbursements: quick add form (description +
  amount) and a delete action for today's own entries.
- **Generate Report** → denomination modal: qty inputs per bill
  (1000/500/200/100/50/20) + coins amount; counted total computes live and
  warns (yellow) when it differs from NET AMOUNT; saving is still allowed.
- Save & Print: A4 portrait via the Electron print pipeline (temp-file
  `print-html`), browser fallback. Layout mirrors the Excel original:
  school header (logo, name, address, contacts from School Config), title +
  report date, collections table with TOTAL COLLECTION, LESS: DISBURSEMENT
  block with subtotal, NET AMOUNT, highlighted **CASH ON HAND**, denominations
  box on the right with its own total, signature lines at the bottom.
- If a saved report already exists for the date: show it and offer Reprint
  (frozen numbers) or Regenerate (explicit overwrite warning).

## Error handling

- Backend recomputes all totals from raw data — client-supplied amounts for
  auto rows are never trusted; manual rows and denominations are the only
  client inputs.
- Regenerate conflict surfaced in UI, not silent.
- Print failures surface the existing toast pattern.

## Testing

- Backend: preview totals group correctly across sources; clock-window
  boundary (payment after generation goes to next report); overwrite on
  regenerate; disbursement ownership; staff (non-superuser) access scoped to
  self.
- Manual: print matches the photographed Excel layout on A4 and in Electron.

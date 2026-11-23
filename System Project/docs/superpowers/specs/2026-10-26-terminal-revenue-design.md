# Terminal-Attributed Revenue & POS Fixes — Design

Date: 2026-10-26
Status: Approved (pending final review)
Owner: D4RK7H3N

## Goal

Attribute every POS/tuition transaction to the physical terminal it was made on
(HWID via the Electron app), report revenue per terminal without changing any
grand totals, and fix cashier UX gaps: half-paid highlighting, Name/LRN student
search, printable A4 revenue reports (overall + per terminal), and Electron
receipt printing that currently comes out landscape and on the wrong paper.

## Non-Goals

- Changing how `total_revenue` is calculated (stays byte-identical).
- Per-terminal permissions or access control.
- Real HWID for plain browsers/phones (impossible in browser JS).
- Assessment/dorm/tour/graduation/general revenue breakdown by terminal
  (grand-total only; can extend later).

## 1. Device Identity (Electron)

- `frontend/electron/main.js`: new IPC `get-device-id`.
  - Primary: `machineIdSync()` from `node-machine-id` (new npm dependency).
  - Fallback: random UUID persisted at `<userData>/device-id.txt`.
- `frontend/electron/preload.js`: expose `getDeviceId()` on `window.electronAPI`.
- Renderer boot: when `window.electronAPI` exists, call it once and set axios
  default header `X-Device-Id: <id>` (`frontend/src/services/api.js`).
- Plain browser sessions send no header → transactions are recorded with
  terminal = NULL and surface as "Unassigned".

## 2. Backend (Django)

### Models

- New `sales.Terminal`:
  - `device_id` — CharField, unique.
  - `name` — CharField, default e.g. "Device xxxx1234"; admin renames to
    "Terminal 1..N".
  - `registered_at` — auto_now_add.
  - `last_seen_at` — DateTimeField.
  - `is_active` — BooleanField default True.
- `Sale.terminal` — FK `sales.Terminal`, null=True, SET_NULL.
- `Sale.created_by` — FK `auth.User`, null=True, SET_NULL (secondary info).
- `TuitionPayment.terminal` + `TuitionPayment.created_by` — same pattern.
- One migration for all of the above.

### Auto-registration

- Lightweight middleware: on any authenticated request carrying an
  `X-Device-Id` that matches no Terminal, `get_or_create` a Terminal named
  "Device <last6>" and refresh `last_seen_at` (throttled: only write when the
  stored value is older than 60 s, to avoid write amplification).
- Admin renames entries in Django admin (`sales.Terminal` registered with
  list_display: name, device_id, last_seen_at, is_active).

### Capture at creation

- `SaleViewSet.create` and `TuitionPaymentViewSet.create`: resolve
  `request.headers.get("X-Device-Id")` → Terminal (get_or_create, same
  middleware helper) and set `terminal=…`, `created_by=request.user`.
- Missing/invalid header → fields stay NULL; the sale is never blocked.

### Revenue API

- `RevenueViewSet.list` response gains `by_terminal` next to `totals`:
  - Rows: `{ terminal_id, terminal_name, staff_names, pos, tuition,
    total, transactions }`.
  - POS basis: existing `Sale.objects.filter(amount_paid__gt=0)` grouped by
    `terminal`; tuition basis: `TuitionPayment` grouped by `terminal`.
  - Honors the same date-range and search filters already applied to the
    report.
  - NULL-terminal rows grouped under `terminal_name: "Unassigned"`.
  - `total_revenue` and every existing totals field are unchanged.

## 3. Frontend

### RevenuePage (`frontend/src/pages/RevenuePage.jsx`)

- New "Revenue by Terminal" section fed by `by_terminal`:
  table `Terminal · Staff · POS · Tuition · Total · Transactions` plus a
  `Print` button per row.
- Respects the existing date-range filter.

### CashierPage (`frontend/src/pages/CashierPage.jsx`)

- Transaction history rows with `payment_status === 'partial'` render with a
  yellow row highlight (paid stays green, unpaid stays red).
- Student search: backend already matches
  `first_name | last_name | lrn` (`api/views.py` StudentViewSet). Verify
  end-to-end in the cashier search; display the LRN in the results dropdown
  so cashiers can confirm identity.

## 4. Printables (A4 portrait)

- **Overall revenue report** — school header, date range, totals table,
  Revenue by Terminal table, prepared-by footer.
- **Per-terminal report** — one sheet per terminal: terminal + staff names,
  date range, that terminal's totals, and its full transaction line-items for
  the range.
- Both print A4 portrait via the Electron pipeline when inside Electron;
  browsers keep the `@media print` CSS path.

## 5. Electron Print Pipeline Fix

- Problem: in Electron, printing goes through the native dialog with the
  printer driver's defaults (landscape + A4/Letter); `@media print` CSS does
  not override the dialog.
- Fix: main-process IPC `print-html { html, options }`:
  - Opens a hidden `BrowserWindow`, loads the HTML, then
    `webContents.print({ landscape: false, printBackground: true,
    pageSize: … , margins … })` with explicit options.
  - `pageSize` 80 mm roll for receipts, `A4` for reports.
- Renderer: when Electron is detected, receipt (Cashier + Tuition) and report
  printing route through `print-html`; otherwise existing react-to-print /
  `@media print` behavior is kept.

## Error Handling

- Unknown/absent device header → NULL terminal, sale proceeds ("Unassigned").
- `machine-id` failure in Electron → persisted UUID fallback.
- Printer errors inside `print-html` → surface a renderer toast; never block
  the sale flow.

## Testing

1. Backend: migrate locally, restart `DarkZSMS-Backend`; `curl` a sale with a
   fake `X-Device-Id` → Terminal auto-registered; rename it in Django admin;
   `GET /api/revenue/` shows the new terminal in `by_terminal`; totals equal
   pre-change values.
2. Electron: rebuilt installer sends `X-Device-Id`; its terminal appears and
   revenue rolls up under it.
3. Print: receipt prints 80 mm portrait from Electron; A4 reports print
   portrait with correct pagination.
4. Cashier: `partial` rows highlight yellow; Name/LRN search returns
   matches; LRN visible in results.

## Rollout

1. Backend migration + service restart.
2. Frontend build + deploy.
3. Rebuild Electron installer (new `node-machine-id` dependency).
4. Admin renames auto-registered devices to Terminal 1..N in Django admin.

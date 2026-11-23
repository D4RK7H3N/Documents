"""Re-run the 5x4x3 sweep through the refactored API and diff the gen50 grid."""
import json
import time
import urllib.request

BASE = "http://localhost:8003/api/sweeps/"
baseline = json.load(open("baseline-5x4x3.json"))

payload = baseline["payload"]
t0 = time.perf_counter()
req = urllib.request.Request(
    BASE,
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=600) as resp:
    created = json.loads(resp.read())
elapsed = time.perf_counter() - t0

print(f"POST /api/sweeps/ -> id={created['id']} status={created['status']} in {elapsed:.2f}s")
print(f"progress: {created['progress']}")

cells = created["cells"]
kill = payload["sweep"]["pesticide_kill"]
cost = payload["sweep"]["resistance_cost"]
grid = [[None] * len(cost) for _ in kill]
for c in cells:
    grid[c["a_index"]][c["b_index"]] = c["gen50_mean"]

print("new grid (kill \\ cost):")
for k, row_vals in zip(kill, grid):
    print(f"  {k:>4}", row_vals)

if grid == baseline["grid"]:
    print("MATCH: gen50 grid IDENTICAL to the pre-refactor baseline (5x4x3, 60 runs)")
else:
    for i, (old_row, new_row) in enumerate(zip(baseline["grid"], grid)):
        if old_row != new_row:
            print(f"MISMATCH row kill={kill[i]}: old={old_row} new={new_row}")
    raise SystemExit("GRID MISMATCH")

# Extra integrity checks on the new row shape (SQLite stores UUIDs without dashes)
import sqlite3
con = sqlite3.connect("backend/db.sqlite3")
cur = con.cursor()
sid = created["id"].replace("-", "")
n_runs, n_done = cur.execute(
    "SELECT COUNT(*), SUM(status='done') FROM experiments_sweeprun WHERE sweep_id = ?",
    (sid,),
).fetchone()
print(f"SweepRun rows: {n_runs} (done={n_done}); expected 60/60")
results = cur.execute(
    "SELECT results FROM experiments_sweepexperiment WHERE id = ?", (sid,)
).fetchone()[0]
keys = sorted(json.loads(results).keys())
print("results keys:", keys, "(no 'runs' list)")
assert keys == ["aggregate"], "results must hold only the aggregate"
assert n_runs == 60 and n_done == 60
print("OK")

import type { ReportStatus } from "../api/types";

const styles: Record<ReportStatus, string> = {
  queued: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40",
  running: "bg-purple-500/15 text-purple-300 border-purple-500/40",
  fix_ready: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  failed: "bg-red-500/15 text-red-300 border-red-500/40",
  rejected: "bg-amber-500/15 text-amber-300 border-amber-500/40",
};

export function StatusBadge({ status }: { status: ReportStatus }) {
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${styles[status] ?? styles.queued}`}>
      {status.replace("_", " ")}
    </span>
  );
}

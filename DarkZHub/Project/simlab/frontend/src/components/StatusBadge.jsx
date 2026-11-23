/**
 * Shared status badge (pending / running / done / partial / failed).
 */
const STATUS_STYLES = {
  pending: "border-edge text-ash",
  running: "border-lilac text-lilac animate-pulse",
  done: "border-emerald-500/60 text-emerald-400",
  partial: "border-amber-500/60 text-amber-400",
  failed: "border-red-500/60 text-red-400",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`border rounded px-3 py-1 text-xs uppercase tracking-wider whitespace-nowrap ${
        STATUS_STYLES[status] ?? STATUS_STYLES.pending
      }`}
    >
      {status}
    </span>
  );
}

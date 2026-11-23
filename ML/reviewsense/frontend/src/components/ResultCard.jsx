const LABEL_STYLES = {
  positive: {
    chip: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
    bar: "bg-emerald-500",
  },
  neutral: {
    chip: "border-slate-500/30 bg-slate-500/15 text-slate-300",
    bar: "bg-slate-400",
  },
  negative: {
    chip: "border-rose-500/30 bg-rose-500/15 text-rose-400",
    bar: "bg-rose-500",
  },
};

export default function ResultCard({ result, loading }) {
  if (loading) {
    return (
      <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
        Analyzing your review…
      </div>
    );
  }

  if (!result) return null;

  const style = LABEL_STYLES[result.prediction] || LABEL_STYLES.neutral;
  const pct = Math.round(result.confidence * 100);

  return (
    <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span
          className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold capitalize ${style.chip}`}
        >
          {result.prediction}
        </span>
        <span className="text-sm text-slate-400">
          Confidence:{" "}
          <span className="font-semibold text-slate-100">{pct}%</span>
        </span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${style.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>Model: {result.model_version}</span>
        {result.inference_ms != null && <span>Inference: {result.inference_ms} ms</span>}
        {result.created_at && (
          <span>At: {new Date(result.created_at).toLocaleString()}</span>
        )}
      </div>
    </div>
  );
}

const MAX_LENGTH = 5000;

export default function PredictForm({ text, onChange, onSubmit, loading }) {
  const canSubmit = text.trim().length >= 3 && !loading;

  return (
    <form onSubmit={onSubmit}>
      <label
        htmlFor="review"
        className="mb-2 block text-sm font-medium text-slate-300"
      >
        Customer review
      </label>
      <textarea
        id="review"
        value={text}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        maxLength={MAX_LENGTH}
        disabled={loading}
        placeholder="e.g. The headphones arrived quickly and the sound quality is amazing!"
        className="w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none transition focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 disabled:opacity-60"
      />
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          {text.length}/{MAX_LENGTH}
        </span>
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950/40 border-t-slate-950" />
          )}
          {loading ? "Analyzing…" : "Predict"}
        </button>
      </div>
    </form>
  );
}

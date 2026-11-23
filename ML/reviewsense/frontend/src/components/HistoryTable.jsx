const LABEL_COLORS = {
  positive: "text-emerald-400",
  neutral: "text-slate-300",
  negative: "text-rose-400",
};

export default function HistoryTable({ items }) {
  if (!items.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-sm text-slate-500">
        No predictions yet. Submit a review above.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-slate-900 text-xs uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Review</th>
            <th className="px-4 py-3 font-medium">Prediction</th>
            <th className="px-4 py-3 font-medium">Confidence</th>
            <th className="px-4 py-3 font-medium">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/70">
          {items.map((item) => (
            <tr
              key={item.id}
              className="odd:bg-slate-900/40 hover:bg-slate-900/70"
            >
              <td
                className="max-w-[320px] truncate px-4 py-3 text-slate-300"
                title={item.input_text}
              >
                {item.input_text}
              </td>
              <td
                className={`px-4 py-3 font-medium capitalize ${
                  LABEL_COLORS[item.prediction] || ""
                }`}
              >
                {item.prediction}
              </td>
              <td className="px-4 py-3 text-slate-300">
                {(item.confidence * 100).toFixed(1)}%
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                {new Date(item.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

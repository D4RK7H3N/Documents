import { useCallback, useEffect, useState } from "react";
import PredictForm from "./components/PredictForm.jsx";
import ResultCard from "./components/ResultCard.jsx";
import HistoryTable from "./components/HistoryTable.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export default function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState("");

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/history/`);
      if (!res.ok) throw new Error(`History request failed (HTTP ${res.status})`);
      setHistory(await res.json());
      setHistoryError("");
    } catch (err) {
      setHistoryError(err.message || "Could not load history.");
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (trimmed.length < 3) {
      setError("Please enter at least 3 characters.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/predict/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const message = Array.isArray(data.text)
          ? data.text.join(" ")
          : data.error || `Request failed (HTTP ${res.status})`;
        throw new Error(message);
      }
      setResult(data);
      setText("");
      fetchHistory();
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Cannot reach the API. Is the Django server running?"
          : err.message || "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:py-14">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Review<span className="text-emerald-400">Sense</span>
          </h1>
          <p className="mt-2 text-sm text-slate-400 sm:text-base">
            Classify a customer review as positive, neutral, or negative — with a
            confidence score.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg shadow-black/20 sm:p-6">
          <PredictForm
            text={text}
            onChange={setText}
            onSubmit={handleSubmit}
            loading={loading}
          />
          {error && (
            <p className="mt-3 rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-300">
              {error}
            </p>
          )}
          <ResultCard result={result} loading={loading} />
        </section>

        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent predictions</h2>
            <button
              type="button"
              onClick={fetchHistory}
              className="text-xs text-slate-400 transition hover:text-slate-200"
            >
              Refresh
            </button>
          </div>
          {historyError && (
            <p className="mb-2 text-xs text-amber-400">
              Could not load history: {historyError}
            </p>
          )}
          <HistoryTable items={history} />
        </section>

        <footer className="mt-10 text-center text-xs text-slate-600">
          Django + DRF · scikit-learn · React + Vite + Tailwind
        </footer>
      </div>
    </div>
  );
}

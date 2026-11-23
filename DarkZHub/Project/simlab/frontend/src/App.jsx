import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import NewExperiment from "./pages/NewExperiment.jsx";
import ExperimentResult from "./pages/ExperimentResult.jsx";
import SweepPage from "./pages/SweepPage.jsx";
import SweepResult from "./pages/SweepResult.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

const NAV_LINKS = [
  { to: "/", label: "New experiment" },
  { to: "/sweeps/new", label: "New sweep" },
  { to: "/history", label: "History" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-edge bg-panel/60">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-baseline justify-between">
            <Link to="/" className="flex items-baseline gap-3 group">
              <span className="font-display text-2xl tracking-wide group-hover:text-lilac transition-colors">
                Sim<span className="text-lilac">Lab</span>
              </span>
              <span className="text-[11px] uppercase tracking-[0.3em] text-ash">
                simulation platform
              </span>
            </Link>
            <nav className="flex gap-5 text-sm">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="text-ash hover:text-lilac transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main className="flex-1 w-full max-w-5xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<NewExperiment />} />
            <Route path="/experiments/:id" element={<ExperimentResult />} />
            <Route path="/sweeps/new" element={<SweepPage />} />
            <Route path="/sweeps/:id" element={<SweepResult />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>

        <footer className="border-t border-edge py-3">
          <p className="text-center text-xs text-ash">
            Simulation result, not experimental evidence.
          </p>
        </footer>
      </div>
    </BrowserRouter>
  );
}

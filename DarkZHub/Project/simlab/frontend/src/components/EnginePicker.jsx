/**
 * Engine picker card grid, shared by NewExperiment and SweepPage.
 */
export default function EnginePicker({ engines, selected, onSelect }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
      {engines.map((e) => (
        <button
          key={e.name}
          onClick={() => onSelect(e.name)}
          className={`text-left border rounded px-4 py-3 transition-colors ${
            e.name === selected
              ? "border-lilac bg-lilac/10"
              : "border-edge bg-panel hover:border-lilac/50"
          }`}
        >
          <div className="text-ink">{e.name}</div>
          <div className="text-xs text-ash">v{e.version}</div>
        </button>
      ))}
    </div>
  );
}

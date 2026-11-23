import { useSettings } from "../api/hooks";

const labels: Record<string, string> = {
  llm_key_set: "LLM key configured",
  github_token_set: "GitHub token configured",
  smtp_set: "SMTP configured",
  turnstile_set: "Turnstile secret configured",
  cf_access_enabled: "Cloudflare Access enabled",
  use_r2: "R2 screenshot storage",
  r2_bucket_set: "R2 bucket configured",
  dashboard_origin_set: "Dashboard origin configured",
  widget_url_set: "Widget URL configured",
  debug: "Debug mode",
};

export function SettingsPage() {
  const settings = useSettings();

  if (settings.isLoading) return <p className="text-sm text-zinc-500">Loading settings…</p>;
  if (settings.isError) return <p role="alert" className="text-sm text-red-400">{settings.error.message}</p>;
  if (!settings.data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">Configuration status only — values are never shown.</p>
      </div>
      <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
        {Object.entries(settings.data).map(([key, value]) => (
          <li key={key} className="flex items-center justify-between gap-4 p-4 text-sm">
            <span>{labels[key] ?? key}</span>
            <span className={`rounded-full border px-2 py-0.5 text-xs ${value ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300" : "border-zinc-300 text-zinc-500 dark:border-zinc-700"}`}>
              {value ? "On" : "Off"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

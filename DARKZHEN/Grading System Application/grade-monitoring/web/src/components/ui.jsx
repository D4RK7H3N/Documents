import { createContext, useContext, useEffect, useState } from "react";

const ToastContext = createContext(null);

function ToastCard({ toast, onClose }) {
  const styles = {
    success: { icon: "check_circle", iconCls: "text-tertiary-container", title: "text-on-surface" },
    error: { icon: "error", iconCls: "text-error", title: "text-on-surface" },
    info: { icon: "info", iconCls: "text-primary", title: "text-on-surface" },
  };
  const s = styles[toast.type] || styles.info;
  return (
    <div className="flex items-start gap-space-sm bg-surface-container-lowest border border-outline-variant/25 rounded-xl shadow-[0_4px_16px_rgba(11,28,48,0.12)] px-space-md py-space-sm">
      <span className={`material-symbols-outlined text-lg shrink-0 mt-0.5 ${s.iconCls}`}>{s.icon}</span>
      <p className="flex-1 font-body-sm text-body-sm text-on-surface leading-snug">{toast.message}</p>
      <button
        onClick={onClose}
        aria-label="Dismiss notification"
        className="flex h-11 w-11 -mr-2 -mt-2 items-center justify-center rounded-lg text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface shrink-0"
      >
        <span className="material-symbols-outlined text-sm">close</span>
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = (id) => setToasts((list) => list.filter((t) => t.id !== id));

  const push = (type, message) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((list) => [...list.slice(-4), { id, type, message }]);
    setTimeout(() => dismiss(id), 4500);
  };

  const value = {
    success: (message) => push("success", message),
    error: (message) => push("error", message),
    info: (message) => push("info", message),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed top-space-md right-space-md z-[120] flex flex-col gap-space-sm w-[24rem] max-w-[92vw]">
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}

export function Spinner() {
  return (
    <div className="flex justify-center items-center py-16">
      <div className="h-10 w-10 rounded-full border-[3px] border-surface-container-high border-t-primary animate-spin" />
    </div>
  );
}

export function ErrorBanner({ error }) {
  if (!error) return null;
  return (
    <div className="rounded-xl bg-error-container text-on-error-container px-space-md py-space-sm text-body-sm">
      <div className="flex items-center gap-space-xs font-label-md">
        <span className="material-symbols-outlined text-lg">error</span>
        {error.message || String(error)}
      </div>
      {error.details && typeof error.details === "object" && (
        <ul className="mt-space-2xs list-disc pl-space-lg opacity-90">
          {Object.values(error.details)
            .flat()
            .map((d, i) => (
              <li key={i}>{typeof d === "string" ? d : JSON.stringify(d)}</li>
            ))}
        </ul>
      )}
    </div>
  );
}

export function NoticeBanner({ children, tone = "good" }) {
  const tones = {
    good: "bg-tertiary-fixed/30 text-[#005336] border-tertiary-container/40",
    info: "bg-secondary-container/40 text-[#1f2937] border-secondary-container",
  };
  return (
    <div className={`rounded-xl border px-space-md py-space-sm text-body-sm ${tones[tone]}`}>{children}</div>
  );
}

export function PageHeader({ eyebrow, title, sub, actions }) {
  return (
    <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest border border-outline-variant/70 p-space-lg sm:p-space-xl rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)]">
      <div className="flex flex-col gap-space-2xs">
        {eyebrow && (
          <div className="flex items-center gap-space-xs text-on-surface-variant font-label-sm text-label-sm uppercase tracking-wider">
            <span className="inline-block w-2 h-2 rounded-full bg-primary" />
            {eyebrow}
          </div>
        )}
        <h1 className="font-headline-xl text-headline-lg-mobile sm:text-headline-xl text-on-surface tracking-tight">{title}</h1>
        {sub && <p className="font-body-md text-body-md text-on-surface-variant">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-space-sm flex-wrap">{actions}</div>}
    </section>
  );
}

export function Card({ children, className = "" }) {
  return <div className={`bg-surface-container-lowest border border-outline-variant/70 rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)] ${className}`}>{children}</div>;
}

export function SectionCard({ title, sub, icon, actions, children, className = "" }) {
  return (
    <Card className={className}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm px-space-lg sm:px-space-xl pt-space-lg pb-space-sm">
        <div className="flex items-center gap-space-md min-w-0">
          {icon && (
            <div className="w-9 h-9 rounded-lg bg-secondary-container/70 text-primary flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-xl">{icon}</span>
            </div>
          )}
          <div className="min-w-0">
            <h2 className="font-headline-md text-headline-md text-on-surface">{title}</h2>
            {sub && <p className="font-body-sm text-body-sm text-on-surface-variant">{sub}</p>}
          </div>
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </div>
      <div className="px-space-lg sm:px-space-xl pb-space-lg sm:pb-space-xl">{children}</div>
    </Card>
  );
}

export function KpiCard({
  label,
  icon,
  value,
  trend,
  trendTone = "info",
  progress,
  progressTone = "bg-primary",
  progressTrack = "bg-secondary-fixed",
  scaleLabel,
  actionStrip,
  footnote,
}) {
  const tones = {
    good: "bg-tertiary-fixed text-on-tertiary-fixed",
    bad: "bg-error-container text-on-error-container",
    info: "bg-secondary-container text-on-secondary-container",
    warn: "bg-error-container/40 text-on-error-container",
  };
  return (
    <div className="flex flex-col justify-between bg-surface-container-lowest border border-outline-variant/70 p-space-lg rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)] hover:border-secondary-fixed-dim transition-colors duration-200">
      <div className="flex items-center justify-between text-on-surface-variant">
        <span className="font-label-sm text-label-sm uppercase tracking-wider">{label}</span>
        {icon && <span className="material-symbols-outlined text-primary text-lg">{icon}</span>}
      </div>
      <div className="my-space-md flex items-baseline justify-between">
        <span className="font-headline-xl text-headline-xl text-on-surface tracking-tight font-bold">{value}</span>
        {trend && (
          <div className={`flex items-center gap-space-2xs px-space-xs py-space-2xs rounded-full font-label-sm text-label-sm ${tones[trendTone]}`}>
            {trend}
          </div>
        )}
      </div>
      {actionStrip && (
        <div className="flex items-center justify-between bg-error-container/30 px-space-sm py-space-2xs rounded-lg">
          <span className="font-label-sm text-label-sm text-on-error-container font-semibold uppercase">
            {actionStrip.label}
          </span>
          <span className="font-data-tabular-sm text-data-tabular-sm text-on-error-container">{actionStrip.value}</span>
        </div>
      )}
      {progress !== undefined && (
        <div className="flex items-end justify-between gap-space-2xs h-7 pt-space-xs">
          <div className={`w-full ${progressTrack} h-2 rounded-full overflow-hidden flex`}>
            <div className={`${progressTone} h-full`} style={{ width: `${progress}%` }} />
          </div>
          {scaleLabel && (
            <span className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant shrink-0">{scaleLabel}</span>
          )}
        </div>
      )}
      {footnote && <div className="pt-space-xs font-label-sm text-label-sm text-on-surface-variant">{footnote}</div>}
    </div>
  );
}

export function TrendPill({ children, tone = "info", icon }) {
  const tones = {
    good: "bg-tertiary-fixed text-[#005236]",
    bad: "bg-error-container text-on-error-container",
    warn: "bg-error-container/40 text-on-error-container",
    info: "bg-secondary-container text-on-secondary-container",
    neutral: "bg-surface-container-high text-on-surface-variant",
  };
  return (
    <span className={`inline-flex items-center gap-space-2xs px-space-sm py-space-2xs rounded-full font-label-sm text-label-sm whitespace-nowrap ${tones[tone]}`}>
      {icon && <span className="material-symbols-outlined text-xs">{icon}</span>}
      {children}
    </span>
  );
}

export function Btn({ variant = "primary", icon, className = "", children, ...props }) {
  const styles = {
    primary: "bg-primary-container hover:bg-primary-hover text-on-primary shadow-sm",
    secondary: "bg-secondary-container/70 hover:bg-secondary-container text-on-surface border border-outline-variant/70",
    ghost: "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface",
    danger: "bg-error-container hover:bg-error text-on-error-container hover:text-on-error border border-error/15",
  };
  return (
    <button
      className={`flex min-h-11 items-center justify-center gap-space-xs px-space-md py-space-sm font-label-md text-label-md rounded-lg transition-colors duration-150 active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none ${styles[variant]} ${className}`}
      {...props}
    >
      {icon && <span className="material-symbols-outlined text-base">{icon}</span>}
      {children}
    </button>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-space-2xs block font-label-md text-label-md text-on-surface-variant">{label}</span>
      {children}
      {hint && <span className="mt-space-2xs block font-body-sm text-body-sm text-on-surface-variant/70">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full min-h-11 bg-surface-container-low border border-outline-variant rounded-lg px-space-md py-space-sm font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/70 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-colors";

export function EmptyState({ icon = "inbox", title, sub }) {
  return (
    <div className="flex flex-col items-center justify-center py-space-2xl text-center">
      <div className="w-14 h-14 rounded-full bg-surface-container-high flex items-center justify-center">
        <span className="material-symbols-outlined text-2xl text-outline-variant">{icon}</span>
      </div>
      <p className="mt-space-md font-body-md text-body-md text-on-surface">{title}</p>
      {sub && <p className="font-body-sm text-body-sm text-on-surface-variant">{sub}</p>}
    </div>
  );
}

export function TempPasswordModal({ open, title = "Account created", username, role, password, onClose }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setCopied(false);
  }, [open, password]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-space-lg">
      <div className="absolute inset-0 bg-[#0b1c30]/60 backdrop-blur-sm" />
      <Card className="relative w-full max-w-md p-space-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-full bg-primary-container/10 text-primary flex items-center justify-center">
            <span className="material-symbols-outlined text-3xl">key</span>
          </div>
          <h2 className="mt-space-md font-headline-md text-headline-md text-on-surface">{title}</h2>
          <p className="mt-space-2xs font-body-md text-body-md text-on-surface-variant">
            {username} <span className="capitalize">({role})</span> — temporary password
          </p>
          <div className="mt-space-lg w-full flex items-center gap-space-sm bg-surface-container-low border border-outline-variant/40 rounded-xl px-space-md py-space-md">
            <code className="flex-1 font-data-tabular-lg text-data-tabular-lg text-on-surface font-bold tracking-wide select-all text-center">
              {password}
            </code>
            <Btn
              variant="secondary"
              icon={copied ? "check" : "content_copy"}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(password);
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? "Copied" : "Copy"}
            </Btn>
          </div>
          <div className="mt-space-md w-full rounded-xl bg-error-container/30 text-on-error-container px-space-md py-space-sm font-body-sm text-body-sm flex items-start gap-space-xs text-left">
            <span className="material-symbols-outlined text-base">warning</span>
            Shown only once. Copy it now — the account must change this password at first login.
          </div>
          <Btn className="mt-space-lg justify-center w-full" icon="done" onClick={onClose}>
            Done, I saved it
          </Btn>
        </div>
      </Card>
    </div>
  );
}

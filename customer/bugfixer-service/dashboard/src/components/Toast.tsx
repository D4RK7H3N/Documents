import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  message: string;
  kind: ToastKind;
}

type Push = (message: string, kind?: ToastKind) => void;

const ToastContext = createContext<Push | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback<Push>((message, kind = "info") => {
    const id = Date.now() + Math.random();
    setItems((current) => [...current, { id, message, kind }]);
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), 4500);
  }, []);

  const colors: Record<ToastKind, string> = {
    success: "border-emerald-500 bg-emerald-950/80 text-emerald-100",
    error: "border-red-500 bg-red-950/80 text-red-100",
    info: "border-zinc-500 bg-zinc-900/90 text-zinc-100",
  };

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" role="status" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`rounded-lg border px-4 py-3 text-sm shadow-lg ${colors[item.kind]}`}>
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Push {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used inside ToastProvider");
  return value;
}

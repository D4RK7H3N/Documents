"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface NotificationItem {
  id: string;
  type: string;
  message: string;
  link: string | null;
  readAt: string | null;
  createdAt: string;
}

export default function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch("/api/notifications");
    if (!res.ok) return;
    const data = await res.json();
    setItems(data.notifications ?? []);
    setUnread(data.unread ?? 0);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function handleOpen() {
    setOpen((o) => !o);
    if (!open) load();
  }

  async function markAllRead() {
    setBusy(true);
    await fetch("/api/notifications/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    setBusy(false);
    await load();
  }

  async function handleClick(n: NotificationItem) {
    if (!n.readAt) {
      await fetch("/api/notifications/read", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: n.id }),
      });
      await load();
    }
    setOpen(false);
    if (n.link) {
      router.push(n.link);
      router.refresh();
    }
  }

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="relative p-1.5 text-text-muted hover:text-text transition-colors press-down"
        aria-label="Notifications"
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-accent-pink text-white text-[10px] font-semibold flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 z-50 w-80 glass-panel rounded-xl overflow-hidden flex flex-col anim-slide-down">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="font-display font-semibold tracking-widest text-sm text-text-muted">
                NOTIFICATIONS
              </span>
              {unread > 0 && (
                <button
                  onClick={markAllRead}
                  disabled={busy}
                  className="text-xs text-accent-cyan hover:underline disabled:opacity-50"
                >
                  Mark all read
                </button>
              )}
            </div>

            {items.length === 0 ? (
              <p className="text-sm text-text-muted px-4 py-6 text-center">
                No notifications yet.
              </p>
            ) : (
              <ul className="max-h-80 overflow-y-auto flex flex-col">
                {items.map((n) => (
                  <li key={n.id} className="border-b border-border/50 last:border-b-0">
                    <button
                      onClick={() => handleClick(n)}
                      className={`w-full text-left px-4 py-3 flex flex-col gap-0.5 transition-colors ${
                        n.readAt ? "opacity-70 hover:opacity-100" : "bg-white/[0.03] hover:bg-white/[0.06]"
                      }`}
                    >
                      <span className="text-sm">{n.message}</span>
                      <span className="font-mono-tabular text-[10px] text-text-muted">
                        {new Date(n.createdAt).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                        {!n.readAt && (
                          <span className="text-accent-cyan ml-2">● new</span>
                        )}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}

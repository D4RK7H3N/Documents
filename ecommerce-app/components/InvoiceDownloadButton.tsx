"use client";

import { useState } from "react";
import Link from "next/link";

export default function InvoiceDownloadButton({ orderId }: { orderId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setError(null);
    setBusy(true);

    const res = await fetch(`/api/orders/${orderId}/invoice`);
    setBusy(false);

    if (!res.ok) {
      setError("Couldn't generate invoice");
      return;
    }

    const data = await res.json();
    const blob = new Blob([JSON.stringify(data.invoice, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${data.invoice.invoiceNumber}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex items-center gap-2">
      <Link
        href={`/admin/orders/${orderId}/invoice`}
        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors"
      >
        View invoice
      </Link>
      <button
        onClick={handleDownload}
        disabled={busy}
        className="btn-ghost rounded-lg px-3 py-1.5 text-sm hover:bg-surface-hover transition-colors disabled:opacity-50"
      >
        {busy ? "Generating..." : "Download JSON"}
      </button>
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}

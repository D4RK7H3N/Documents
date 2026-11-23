"use client";

export default function InvoicePrintButton() {
  return (
    <button onClick={() => window.print()} className="btn-primary rounded-lg px-4 py-2 text-sm">
      Print
    </button>
  );
}

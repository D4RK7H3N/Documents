import { useState } from "react";

export function CodeBlock({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center justify-between border-b border-zinc-200 px-3 py-2 text-xs text-zinc-500 dark:border-zinc-800">
        <span>{label ?? "Output"}</span>
        <button type="button" onClick={copy} className="rounded px-2 py-1 hover:bg-zinc-100 dark:hover:bg-zinc-800">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-relaxed">
        {text || "(empty)"}
      </pre>
    </div>
  );
}

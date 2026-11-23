import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useReport, useReportAction } from "../api/hooks";
import { CodeBlock } from "../components/CodeBlock";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";
import type { ReportStatus } from "../api/types";

const steps = ["queued", "running", "fix_ready / failed"] as const;

function stepIndex(status: ReportStatus): number {
  if (status === "queued") return 0;
  if (status === "running") return 1;
  return 2;
}

export function ReportDetailPage() {
  const { id } = useParams();
  const reportId = Number(id);
  const report = useReport(reportId);
  const toast = useToast();
  const [confirm, setConfirm] = useState<null | "requeue" | "reject" | "approve">(null);
  const [zoom, setZoom] = useState(false);

  const requeue = useReportAction("requeue");
  const reject = useReportAction("reject");
  const approve = useReportAction("approvePr");

  const runAction = () => {
    if (!confirm) return;
    const mutation = confirm === "requeue" ? requeue : confirm === "reject" ? reject : approve;
    mutation.mutate(reportId, {
      onSuccess: () => { toast("Action completed", "success"); setConfirm(null); },
      onError: (error) => { toast(error.message, "error"); setConfirm(null); },
    });
  };

  if (report.isLoading) return <p className="text-sm text-zinc-500">Loading report…</p>;
  if (report.isError) return <p role="alert" className="text-sm text-red-400">{report.error.message}</p>;
  if (!report.data) return null;

  const data = report.data;
  const current = stepIndex(data.status);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/reports" className="text-sm text-purple-400 hover:underline">← Reports</Link>
          <h1 className="mt-1 text-2xl font-semibold">Report #{data.id}</h1>
        </div>
        <StatusBadge status={data.status} />
      </div>

      <section className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="text-sm font-semibold">Status timeline</h2>
        <ol className="mt-4 flex flex-wrap gap-2" aria-label="Status timeline">
          {steps.map((step, index) => (
            <li
              key={step}
              className={`rounded-full border px-3 py-1 text-xs ${
                index <= current ? "border-purple-500/60 bg-purple-500/10 text-purple-300" : "border-zinc-300 text-zinc-500 dark:border-zinc-700"
              }`}
              aria-current={index === current ? "step" : undefined}
            >
              {index < current ? "✓ " : ""}{step}
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="space-y-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
          <h2 className="text-sm font-semibold">Report</h2>
          <p className="whitespace-pre-wrap break-words text-sm">{data.message}</p>
          <dl className="space-y-2 text-sm">
            <div><dt className="inline text-zinc-500">Project: </dt><dd className="inline">{data.project_name}</dd></div>
            <div><dt className="inline text-zinc-500">Reporter: </dt><dd className="inline">{data.reporter_email || data.reporter_id || "—"}</dd></div>
            <div><dt className="inline text-zinc-500">Classification: </dt><dd className="inline">{data.classification || "—"}</dd></div>
            <div><dt className="inline text-zinc-500">Page URL: </dt><dd className="inline break-all">{data.page_url || "—"}</dd></div>
            <div><dt className="inline text-zinc-500">User agent: </dt><dd className="inline break-all">{data.user_agent || "—"}</dd></div>
            <div><dt className="inline text-zinc-500">Created: </dt><dd className="inline">{new Date(data.created_at).toLocaleString()}</dd></div>
          </dl>
          <details className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <summary className="cursor-pointer text-sm">Console log</summary>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-zinc-400">
              {data.console_log || "(none)"}
            </pre>
          </details>
        </div>

        <div className="space-y-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
          <h2 className="text-sm font-semibold">Fix details</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="inline text-zinc-500">Screenshot description: </dt><dd className="inline">{data.screenshot_description || "—"}</dd></div>
            <div><dt className="inline text-zinc-500">Branch: </dt><dd className="inline font-mono">{data.branch || "—"}</dd></div>
            <div>
              <dt className="inline text-zinc-500">PR: </dt>
              <dd className="inline">
                {data.pr_url ? <a className="text-purple-400 hover:underline" href={data.pr_url} target="_blank" rel="noreferrer">{data.pr_url}</a> : "—"}
              </dd>
            </div>
          </dl>
          {data.screenshot_url && (
            <div>
              <button type="button" onClick={() => setZoom(true)} className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700">
                View screenshot
              </button>
            </div>
          )}
          <CodeBlock text={data.result_log} label="Result log" />
        </div>
      </section>

      <section className="flex flex-wrap gap-2">
        <button type="button" onClick={() => setConfirm("requeue")} className="rounded-lg border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">Re-queue</button>
        <button type="button" onClick={() => setConfirm("reject")} className="rounded-lg border border-red-500/60 px-4 py-2 text-sm text-red-300">Reject</button>
        <button
          type="button"
          onClick={() => setConfirm("approve")}
          disabled={data.status !== "fix_ready" || !data.branch || Boolean(data.pr_url)}
          className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500 disabled:opacity-40"
        >
          Approve and open PR
        </button>
      </section>

      <ConfirmDialog
        open={confirm !== null}
        title={`${confirm === "approve" ? "Approve PR" : confirm === "reject" ? "Reject report" : "Re-queue report"}`}
        message={
          confirm === "approve"
            ? "This creates a pull request for the already-pushed branch. Continue?"
            : confirm === "reject"
              ? "The report will be marked rejected and will not be processed."
              : "The worker will try this report again from scratch."
        }
        confirmLabel="Continue"
        onConfirm={runAction}
        onCancel={() => setConfirm(null)}
      />

      {zoom && data.screenshot_url && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={() => setZoom(false)}>
          <img src={data.screenshot_url} alt="Report screenshot" className="max-h-full max-w-full rounded-lg" onClick={(event) => event.stopPropagation()} />
        </div>
      )}
    </div>
  );
}

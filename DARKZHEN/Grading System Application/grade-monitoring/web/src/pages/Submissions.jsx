import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, EmptyState, ErrorBanner, PageHeader, SectionCard, Spinner, TrendPill } from "../components/ui";

const STATUS_TONES = {
  pending: "warn",
  approved: "good",
  returned: "bad",
};

function SnapshotTable({ snapshot }) {
  if (!snapshot?.length) return null;
  return (
    <div className="overflow-x-auto mt-space-sm">
      <table className="w-full">
        <thead>
          <tr>
            <th className="min-w-[200px]">Learner</th>
            <th className="text-right">Initial Grade</th>
            <th className="text-right">Quarterly Grade</th>
            <th>Blanks</th>
          </tr>
        </thead>
        <tbody>
          {snapshot.map((row) => (
            <tr key={row.lrn}>
              <td>
                <p className="font-label-md text-label-md text-on-surface">{row.full_name}</p>
                <p className="font-data-tabular-sm text-data-tabular-sm text-on-surface-variant">{row.lrn}</p>
              </td>
              <td className="text-right font-data-tabular-md text-data-tabular-md text-on-surface-variant">
                {row.initial_grade ?? "—"}
              </td>
              <td className="text-right">
                {row.grade !== null ? (
                  <span className="inline-flex items-center font-bold text-tertiary-container bg-surface-container-high px-2 py-0.5 rounded-full text-data-tabular-sm">
                    {row.grade}
                  </span>
                ) : (
                  <span className="text-on-surface-variant/50">—</span>
                )}
              </td>
              <td>
                {row.blanks > 0 ? <TrendPill tone="warn">{row.blanks} blank</TrendPill> : <TrendPill tone="neutral">complete</TrendPill>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Submissions() {
  const { user } = useAuth();
  const [box, setBox] = useState("received");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [returnNote, setReturnNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api(`/submissions/?box=${box}`));
    } catch (err) {
      setError(err);
    }
  }, [box]);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(submission, decision, note = "") {
    setBusy(true);
    setError(null);
    try {
      await api(`/submissions/${submission.id}/${decision}/`, {
        method: "POST",
        body: { decision_note: note },
      });
      setOpenId(null);
      setReturnNote("");
      load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Grade Submissions"
        sub="Encoded quarterly grades sent between teachers for review — approve them or return them with a note."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <div className="flex items-center gap-space-2xs bg-surface-container-low p-space-2xs rounded-xl w-fit">
        {[
          ["received", `Received${user?.role === "teacher" ? "" : ""}`],
          ["sent", "Sent"],
        ].map(([value, label]) => (
          <button
            key={value}
            onClick={() => setBox(value)}
            className={`px-space-lg py-space-xs rounded-lg font-label-md text-label-md transition-colors ${
              box === value
                ? "bg-surface-container-lowest text-on-surface shadow-sm font-semibold"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {!data ? (
        <Spinner />
      ) : data.length === 0 ? (
        <Card className="p-space-xl">
          <EmptyState
            icon={box === "received" ? "inbox" : "outgoing_mail"}
            title={box === "received" ? "Nothing to review" : "Nothing sent yet"}
            sub={
              box === "received"
                ? "Submissions other teachers send you appear here."
                : "Use “Submit for review” in the Gradebook to send quarterly grades to another teacher."
            }
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-space-md">
          {data.map((s) => (
            <SectionCard
              key={s.id}
              icon={box === "received" ? "inbox" : "outgoing_mail"}
              title={`${s.class.subject} · ${s.class.section}`}
              sub={`Quarter ${s.quarter} · from ${s.submitted_by} to ${s.submitted_to}`}
              actions={
                <div className="flex items-center gap-space-sm">
                  <TrendPill tone={STATUS_TONES[s.status]} icon={s.status === "approved" ? "verified" : s.status === "returned" ? "undo" : "hourglass_top"}>
                    {s.status}
                  </TrendPill>
                  <Btn variant="ghost" icon={openId === s.id ? "expand_less" : "visibility"} onClick={() => setOpenId(openId === s.id ? null : s.id)}>
                    {openId === s.id ? "Hide" : "Review"}
                  </Btn>
                </div>
              }
            >
              {s.note && (
                <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-sm">
                  <b className="text-on-surface">Note:</b> {s.note}
                </p>
              )}
              {s.status === "returned" && s.decision_note && (
                <p className="font-body-sm text-body-sm text-on-error-container mb-space-sm">
                  <b>Returned:</b> {s.decision_note}
                </p>
              )}
              {s.status === "approved" && s.decided_at && (
                <p className="font-body-sm text-body-sm text-[#005336] mb-space-sm">
                  Approved {new Date(s.decided_at).toLocaleString()}
                </p>
              )}

              {openId === s.id && (
                <>
                  <SnapshotTable snapshot={s.snapshot} />
                  {s.status === "pending" && s.submitted_to === user?.username && (
                    <div className="mt-space-md pt-space-md border-t border-surface-container-high">
                      <div className="flex flex-wrap items-end gap-space-md">
                        <div className="flex-1 min-w-[220px]">
                          <input
                            className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-space-md py-space-sm font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:border-primary"
                            placeholder="Note when returning (optional)"
                            value={returnNote}
                            onChange={(e) => setReturnNote(e.target.value)}
                          />
                        </div>
                        <Btn icon="undo" variant="secondary" disabled={busy} onClick={() => decide(s, "return", returnNote)}>
                          Return for changes
                        </Btn>
                        <Btn icon="verified" disabled={busy} onClick={() => decide(s, "approve")}>
                          {busy ? "Working…" : "Approve"}
                        </Btn>
                      </div>
                    </div>
                  )}
                </>
              )}
            </SectionCard>
          ))}
        </div>
      )}
    </>
  );
}

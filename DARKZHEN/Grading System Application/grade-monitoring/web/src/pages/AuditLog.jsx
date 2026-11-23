import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { Btn, Card, ErrorBanner, PageHeader, SectionCard, Spinner, TrendPill, inputClass } from "../components/ui";

export default function AuditLog() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ entity: "", action: "", actor: "" });
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page });
      for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
      setData(await api(`/admin/audit-log/?${params}`));
    } catch (err) {
      setError(err);
    }
  }, [filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  if (!data) return error ? <ErrorBanner error={error} /> : <Spinner />;
  const results = data.results || [];

  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Audit Log"
        sub="Every grade-related change, with the old and new values side by side."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <SectionCard title="Entries" sub={`${data.count} total`}>
        <div className="flex flex-wrap gap-space-md mb-space-md">
          <input
            className={`${inputClass} w-44`}
            placeholder="Entity (assessment…)"
            value={filters.entity}
            onChange={(e) => {
              setFilters({ ...filters, entity: e.target.value });
              setPage(1);
            }}
          />
          <input
            className={`${inputClass} w-44`}
            placeholder="Action (score.save…)"
            value={filters.action}
            onChange={(e) => {
              setFilters({ ...filters, action: e.target.value });
              setPage(1);
            }}
          />
          <input
            className={`${inputClass} w-44`}
            placeholder="Actor username"
            value={filters.actor}
            onChange={(e) => {
              setFilters({ ...filters, actor: e.target.value });
              setPage(1);
            }}
          />
        </div>

        {results.length === 0 ? (
          <p className="font-body-md text-body-md text-on-surface-variant py-space-lg text-center">No entries match these filters.</p>
        ) : (
          <div className="flex flex-col gap-space-sm">
            {results.map((e) => (
              <Card key={e.id} className="!bg-surface-container-low px-space-md py-space-sm">
                <div className="flex flex-wrap items-center gap-space-sm">
                  <span className="font-label-sm text-label-sm text-on-surface-variant whitespace-nowrap">
                    {new Date(e.timestamp).toLocaleString()}
                  </span>
                  <TrendPill tone="info">{e.action}</TrendPill>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    {e.entity}{e.entity_id ? ` #${e.entity_id}` : ""} · by <b className="text-on-surface">{e.actor}</b>
                  </span>
                </div>
                <div className="mt-space-2xs flex flex-col gap-space-2xs font-data-tabular-sm text-data-tabular-sm">
                  {e.old_values !== null && e.old_values !== undefined && (
                    <span className="text-on-error-container break-all">− {JSON.stringify(e.old_values)}</span>
                  )}
                  {e.new_values !== null && e.new_values !== undefined && (
                    <span className="text-[#005336] break-all">+ {JSON.stringify(e.new_values)}</span>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        <div className="mt-space-md flex items-center justify-end gap-space-sm">
          <span className="font-label-sm text-label-sm text-on-surface-variant mr-auto">
            Page {page} of {Math.max(1, Math.ceil(data.count / 50))}
          </span>
          <Btn variant="secondary" icon="chevron_left" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Btn>
          <Btn variant="secondary" icon="chevron_right" disabled={!data.next} onClick={() => setPage(page + 1)}>
            Next
          </Btn>
        </div>
      </SectionCard>
    </>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card, EmptyState, ErrorBanner, PageHeader, Spinner, TrendPill } from "../components/ui";

export default function MyClasses() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api("/teacher/classes/")
      .then((d) => setData(d.results || d))
      .catch(setError);
  }, []);

  if (error) return <ErrorBanner error={error} />;
  if (!data) return <Spinner />;

  return (
    <>
      <PageHeader
        eyebrow="Teaching"
        title="My Classes"
        sub="Subject and section combinations assigned to you for this school year."
      />
      {data.length === 0 ? (
        <Card className="p-space-xl">
          <EmptyState icon="class" title="No classes assigned yet" sub="Contact the administrator." />
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-lg">
          {data.map((c) => {
            const locked = c.locked_quarters || [];
            return (
              <Card key={c.id} className="p-space-lg h-full flex flex-col">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">
                      {c.section_name}
                    </p>
                    <h2 className="font-headline-sm text-headline-sm text-on-surface mt-space-2xs">
                      {c.subject_name}
                    </h2>
                  </div>
                  <span className="material-symbols-outlined text-primary text-xl">table_chart</span>
                </div>
                <div className="mt-space-md flex items-center gap-space-xs flex-wrap">
                  <TrendPill tone="info">S.Y. {c.school_year}</TrendPill>
                  {locked.length > 0 && (
                    <TrendPill tone="bad" icon="lock">
                      {locked.map((q) => `Q${q}`).join(", ")} locked
                    </TrendPill>
                  )}
                </div>
                <div className="mt-space-lg pt-space-md border-t border-surface-container-high flex gap-space-sm mt-auto">
                  <Link
                    to={`/gradebook/${c.id}`}
                    className="flex-1 flex items-center justify-center gap-space-xs px-space-md py-space-xs rounded-xl bg-primary-container text-on-primary font-label-md text-label-md shadow-sm hover:bg-primary transition-colors"
                  >
                    <span className="material-symbols-outlined text-base">table_chart</span>
                    Gradebook
                  </Link>
                  <Link
                    to={`/classes/${c.id}/report`}
                    className="flex-1 flex items-center justify-center gap-space-xs px-space-md py-space-xs rounded-xl bg-surface-container text-on-surface font-label-md text-label-md shadow-sm hover:bg-surface-container-high transition-colors"
                  >
                    <span className="material-symbols-outlined text-base text-primary">summarize</span>
                    Class Report
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

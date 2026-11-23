import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Btn, ErrorBanner, PageHeader, Card, Spinner, TrendPill, inputClass, useToast } from "../components/ui";

const TYPES = ["core", "applied", "specialized"];
const COMPONENTS = ["WW", "PT", "QA"];

export default function GradingConfig() {
  const toast = useToast();
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [tableText, setTableText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/admin/grading-config/")
      .then((data) => {
        setConfig(data);
        setTableText(JSON.stringify(data.transmutation_table, null, 1));
      })
      .catch(setError);
  }, []);

  function setWeight(type, component, value) {
    setConfig({ ...config, weights: { ...config.weights, [type]: { ...config.weights[type], [component]: value } } });
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let table;
      try {
        table = JSON.parse(tableText);
      } catch {
        throw { message: "Transmutation table is not valid JSON." };
      }
      if (!Array.isArray(table) || table.length === 0) {
        throw { message: "Transmutation table must be a non-empty array of [min, max, grade] rows." };
      }
      const payload = { name: config.name, weights: config.weights, transmutation_table: table, is_active: true };
      const saved = await api("/admin/grading-config/", { method: "PUT", body: payload });
      setConfig(saved);
      setTableText(JSON.stringify(saved.transmutation_table, null, 1));
      toast.success("Grading configuration saved — every grade was recomputed and the change was written to the audit log.");
    } catch (err) {
      setError(err.message ? err : { message: String(err) });
    } finally {
      setBusy(false);
    }
  }

  if (!config) return error ? <ErrorBanner error={error} /> : <Spinner />;

  return (
    <>
      <PageHeader
        eyebrow="Manage"
        title="Grading Config"
        sub="Component weights per subject type and the transmutation table, per DepEd Order No. 8, s. 2015."
        actions={
          <Btn icon="save" onClick={save} disabled={busy}>
            {busy ? "Saving & recomputing…" : "Save configuration"}
          </Btn>
        }
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <form onSubmit={save} className="grid grid-cols-1 xl:grid-cols-2 gap-space-lg items-start">
        <Card className="p-space-lg">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-space-xs">Component weights (%)</h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-md">
            DepEd Order No. 8, s. 2015 presets for SHS — Core 25/50/25 · Academic (Applied) 25/45/30 ·
            TVL, Sports & Arts 20/60/20. Verify with the school; individual subjects can override
            these in <b>Academics â†’ Subjects â†’ Configure</b>.
          </p>
          <div className="flex flex-col gap-space-lg">
            {TYPES.map((type) => {
              const total = COMPONENTS.reduce((sum, c) => sum + (Number(config.weights?.[type]?.[c]) || 0), 0);
              return (
                <div key={type}>
                  <div className="flex items-center justify-between mb-space-2xs">
                    <p className="font-label-md text-label-md text-on-surface capitalize">{type}</p>
                    <TrendPill tone={total === 100 ? "good" : "bad"}>{total}%</TrendPill>
                  </div>
                  <div className="flex gap-space-md">
                    {COMPONENTS.map((comp) => (
                      <div key={comp} className="flex-1">
                        <input
                          className={inputClass}
                          value={config.weights?.[type]?.[comp] ?? ""}
                          onChange={(e) => setWeight(type, comp, e.target.value)}
                        />
                        <p className="mt-space-2xs font-label-sm text-label-sm text-on-surface-variant text-center">{comp}</p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="p-space-lg">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-space-xs">Transmutation table</h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-sm">
            JSON rows of [initial grade min, max, transmuted grade]. Changing this recomputes every grade.
          </p>
          <textarea
            value={tableText}
            onChange={(e) => setTableText(e.target.value)}
            spellCheck={false}
            className="w-full h-[28rem] bg-surface-container-low border border-outline-variant/40 rounded-xl p-space-md font-data-tabular-sm text-data-tabular-sm leading-relaxed focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/40"
          />
        </Card>
      </form>
    </>
  );
}

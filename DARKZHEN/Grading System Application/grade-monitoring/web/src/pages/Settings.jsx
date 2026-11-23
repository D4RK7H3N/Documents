import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, ErrorBanner, Field, PageHeader, Spinner, inputClass, useToast } from "../components/ui";

export default function Settings() {
  const toast = useToast();
  const { refreshConfig } = useAuth();
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState({ school_name: "", short_name: "", default_school_year: "" });
  const [logoFile, setLogoFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/admin/school-config/")
      .then((data) => {
        setConfig(data);
        setForm({
          school_name: data.school_name || "",
          short_name: data.short_name || "",
          default_school_year: data.default_school_year || "",
        });
      })
      .catch(setError);
  }, []);

  useEffect(() => {
    if (!logoFile) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(logoFile);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [logoFile]);

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("school_name", form.school_name);
      body.append("short_name", form.short_name);
      body.append("default_school_year", form.default_school_year);
      if (logoFile) body.append("logo", logoFile, logoFile.name);
      const access = localStorage.getItem("access");
      const res = await fetch("/api/v1/admin/school-config/", {
        method: "PUT",
        headers: { Authorization: `Bearer ${access}` },
        body,
      });
      const payload = await res.json().catch(() => null);
      if (!res.ok) {
        setError({ message: payload?.error?.message || "Save failed." });
        return;
      }
      setConfig(payload);
      setLogoFile(null);
      toast.success("School settings saved — branding updates everywhere immediately.");
      refreshConfig();
    } finally {
      setBusy(false);
    }
  }

  if (!config) return error ? <ErrorBanner error={error} /> : <Spinner />;
  const currentLogo = preview || config.logo_url || "/logo.svg";

  return (
    <>
      <PageHeader
        eyebrow="Manage"
        title="School Settings"
        sub="How the Grade Monitoring System presents itself — name, logo and the active school year."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <form onSubmit={save} className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-start">
        <Card className="lg:col-span-2 p-space-lg">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-space-md">Identity</h2>
          <div className="flex flex-col gap-space-md">
            <Field label="School name" hint="Shown on the login page and reports.">
              <input
                className={inputClass}
                value={form.school_name}
                onChange={(e) => setForm({ ...form, school_name: e.target.value })}
                required
              />
            </Field>
            <Field label="Short name" hint="Initials shown in the sidebar (e.g. SNHS).">
              <input
                className={inputClass}
                value={form.short_name}
                onChange={(e) => setForm({ ...form, short_name: e.target.value })}
                maxLength={20}
                required
              />
            </Field>
            <Field label="Default school year" hint="Used when syncing learners without a section year.">
              <input
                className={inputClass}
                value={form.default_school_year}
                onChange={(e) => setForm({ ...form, default_school_year: e.target.value })}
                pattern="\d{4}-\d{4}"
                required
              />
            </Field>
            <div>
              <Btn type="submit" icon="save" disabled={busy}>
                {busy ? "Saving…" : "Save settings"}
              </Btn>
            </div>
          </div>
        </Card>

        <Card className="p-space-lg">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-space-md">School logo</h2>
          <div className="flex flex-col items-center gap-space-md">
            <img src={currentLogo} alt="School logo preview" className="w-24 h-24 object-contain rounded-xl border border-outline-variant/30 bg-surface-container-low p-space-sm" />
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.svg,.webp"
              className="text-body-sm text-body-sm"
              onChange={(e) => setLogoFile(e.target.files[0] || null)}
            />
            <p className="font-label-sm text-label-sm text-on-surface-variant text-center">
              PNG, JPG, SVG or WEBP · up to 2 MB.
              {config.logo_url && !logoFile && " A new upload replaces the current logo."}
            </p>
            {logoFile && (
              <Btn
                type="button"
                variant="ghost"
                icon="undo"
                onClick={() => setLogoFile(null)}
              >
                Keep current logo
              </Btn>
            )}
          </div>
        </Card>
      </form>
    </>
  );
}

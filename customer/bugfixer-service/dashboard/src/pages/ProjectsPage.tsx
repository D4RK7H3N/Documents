import { useState } from "react";

import type { Project, ProjectInput } from "../api/types";
import { useProjectMutations, useProjects } from "../api/hooks";
import { CodeBlock } from "../components/CodeBlock";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { DataTable, type Column } from "../components/DataTable";
import { useToast } from "../components/Toast";

const blank: ProjectInput = {
  name: "",
  repo_url: "",
  base_branch: "main",
  test_command: "",
  allowed_origins: [],
  forbidden_paths: [],
  extra_instructions: "",
  triage_enabled: true,
  vision_enabled: false,
  auto_pr: true,
  is_active: true,
};

export function ProjectsPage() {
  const projects = useProjects();
  const mutations = useProjectMutations();
  const toast = useToast();
  const [form, setForm] = useState<ProjectInput>(blank);
  const [editing, setEditing] = useState<number | null>(null);
  const [origins, setOrigins] = useState("[]");
  const [forbidden, setForbidden] = useState("[]");
  const [confirm, setConfirm] = useState<null | { kind: "rotate" | "delete"; project: Project }>(null);

  const set = <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  const startEdit = (project: Project) => {
    setEditing(project.id);
    setForm({
      name: project.name,
      repo_url: project.repo_url,
      base_branch: project.base_branch,
      test_command: project.test_command,
      allowed_origins: project.allowed_origins,
      forbidden_paths: project.forbidden_paths,
      extra_instructions: project.extra_instructions,
      triage_enabled: project.triage_enabled,
      vision_enabled: project.vision_enabled,
      auto_pr: project.auto_pr,
      is_active: project.is_active,
    });
    setOrigins(JSON.stringify(project.allowed_origins));
    setForbidden(JSON.stringify(project.forbidden_paths));
  };

  const save = () => {
    let allowed: string[];
    let paths: string[];
    try {
      allowed = JSON.parse(origins) as string[];
      paths = JSON.parse(forbidden) as string[];
    } catch {
      toast("Allowed origins and forbidden paths must be JSON arrays.", "error");
      return;
    }
    const payload: ProjectInput = { ...form, allowed_origins: allowed, forbidden_paths: paths };
    const onSuccess = () => { toast("Project saved", "success"); setEditing(null); setForm(blank); setOrigins("[]"); setForbidden("[]"); };
    const onError = (error: Error) => toast(error.message, "error");
    if (editing) mutations.update.mutate({ id: editing, data: payload }, { onSuccess, onError });
    else mutations.create.mutate(payload, { onSuccess, onError });
  };

  const runConfirm = () => {
    if (!confirm) return;
    const onSuccess = () => { toast(confirm.kind === "rotate" ? "Key rotated" : "Project deleted", "success"); setConfirm(null); };
    const onError = (error: Error) => { toast(error.message, "error"); setConfirm(null); };
    if (confirm.kind === "rotate") mutations.rotate.mutate(confirm.project.id, { onSuccess, onError });
    else mutations.remove.mutate(confirm.project.id, { onSuccess, onError });
  };

  const columns: Column<Project>[] = [
    { key: "name", label: "Name", render: (row) => <span className="font-medium">{row.name}</span> },
    { key: "repo", label: "Repository", render: (row) => <span className="block max-w-xs truncate font-mono text-xs">{row.repo_url}</span> },
    { key: "branch", label: "Base", render: (row) => row.base_branch },
    { key: "flags", label: "Flags", render: (row) => (
      <span className="text-xs text-zinc-500">
        {[row.triage_enabled && "triage", row.vision_enabled && "vision", row.auto_pr && "auto-pr", !row.is_active && "inactive"].filter(Boolean).join(" · ") || "—"}
      </span>
    ) },
    { key: "actions", label: "Actions", render: (row) => (
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={(event) => { event.stopPropagation(); startEdit(row); }} className="text-sm text-purple-400 hover:underline">Edit</button>
        <button type="button" onClick={(event) => { event.stopPropagation(); setConfirm({ kind: "rotate", project: row }); }} className="text-sm text-purple-400 hover:underline">Rotate key</button>
        <button type="button" onClick={(event) => { event.stopPropagation(); setConfirm({ kind: "delete", project: row }); }} className="text-sm text-red-400 hover:underline">Delete</button>
      </div>
    ) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="mt-1 text-sm text-zinc-500">Register target apps and manage their public keys.</p>
      </div>

      <section className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="mb-4 text-sm font-semibold">{editing ? `Edit project #${editing}` : "New project"}</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {([
            ["name", "Name"], ["repo_url", "Repository URL"], ["base_branch", "Base branch"], ["test_command", "Test command"],
          ] as const).map(([key, label]) => (
            <div key={key}>
              <label htmlFor={key} className="block text-xs font-medium text-zinc-500">{label}</label>
              <input id={key} value={String(form[key] ?? "")} onChange={(event) => set(key, event.target.value)} className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700" />
            </div>
          ))}
          <div className="md:col-span-2">
            <label htmlFor="origins" className="block text-xs font-medium text-zinc-500">Allowed origins (JSON array)</label>
            <input id="origins" value={origins} onChange={(event) => setOrigins(event.target.value)} className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 font-mono text-sm dark:border-zinc-700" />
          </div>
          <div className="md:col-span-2">
            <label htmlFor="forbidden" className="block text-xs font-medium text-zinc-500">Forbidden paths (JSON array)</label>
            <input id="forbidden" value={forbidden} onChange={(event) => setForbidden(event.target.value)} className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 font-mono text-sm dark:border-zinc-700" />
          </div>
          <div className="md:col-span-2">
            <label htmlFor="instructions" className="block text-xs font-medium text-zinc-500">Extra instructions</label>
            <textarea id="instructions" rows={3} value={form.extra_instructions ?? ""} onChange={(event) => set("extra_instructions", event.target.value)} className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 text-sm dark:border-zinc-700" />
          </div>
          {([
            ["triage_enabled", "Triage"], ["vision_enabled", "Vision"], ["auto_pr", "Auto PR"], ["is_active", "Active"],
          ] as const).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={Boolean(form[key])} onChange={(event) => set(key, event.target.checked)} className="h-4 w-4 accent-purple-600" />
              {label}
            </label>
          ))}
        </div>
        <div className="mt-5 flex gap-2">
          <button type="button" onClick={save} className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500">Save</button>
          {editing && (
            <button type="button" onClick={() => { setEditing(null); setForm(blank); setOrigins("[]"); setForbidden("[]"); }} className="rounded-lg border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">Cancel</button>
          )}
        </div>
      </section>

      {projects.isLoading && <p className="text-sm text-zinc-500">Loading projects…</p>}
      {projects.isError && <p role="alert" className="text-sm text-red-400">{projects.error.message}</p>}
      {projects.data && <DataTable columns={columns} rows={projects.data} rowKey={(row) => row.id} empty="No projects registered." />}

      {projects.data?.map((project) => (
        <details key={project.id} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <summary className="cursor-pointer text-sm font-medium">{project.name} — embed snippet</summary>
          <div className="mt-3">
            <CodeBlock text={project.embed_snippet} label="Embed" />
          </div>
        </details>
      ))}

      <ConfirmDialog
        open={confirm !== null}
        title={confirm?.kind === "rotate" ? "Rotate public key" : "Delete project"}
        message={confirm?.kind === "rotate" ? "Existing widget embeds will stop working until updated." : "This deletes the project and all its reports."}
        confirmLabel={confirm?.kind === "rotate" ? "Rotate" : "Delete"}
        onConfirm={runConfirm}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}

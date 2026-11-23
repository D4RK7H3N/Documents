export type ReportStatus = "queued" | "running" | "fix_ready" | "failed" | "rejected";

export interface Me {
  id: number;
  username: string;
  is_staff: boolean;
}

export interface Project {
  id: number;
  name: string;
  public_key: string;
  embed_snippet: string;
  allowed_origins: string[];
  repo_url: string;
  base_branch: string;
  test_command: string;
  forbidden_paths: string[];
  extra_instructions: string;
  triage_enabled: boolean;
  vision_enabled: boolean;
  auto_pr: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ProjectInput = Partial<Omit<Project, "id" | "public_key" | "embed_snippet" | "created_at" | "updated_at">>;

export interface ReportSummary {
  id: number;
  project: number;
  project_name: string;
  status: ReportStatus;
  classification: string;
  message: string;
  reporter_email: string;
  created_at: string;
  updated_at: string;
  pr_url: string;
}

export interface ReportDetail extends ReportSummary {
  reporter_id: string;
  page_url: string;
  user_agent: string;
  console_log: string;
  screenshot_url: string | null;
  screenshot_description: string;
  branch: string;
  result_log: string;
  status_token: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Stats {
  status_counts: Record<ReportStatus, number>;
  reports_per_day: { date: string; count: number }[];
  avg_time_to_fix_seconds: number;
  per_project: { project_id: number; name: string; total: number; fixed: number; success_rate: number }[];
}

export interface SettingsFlags {
  llm_key_set: boolean;
  github_token_set: boolean;
  smtp_set: boolean;
  turnstile_set: boolean;
  cf_access_enabled: boolean;
  use_r2: boolean;
  r2_bucket_set: boolean;
  dashboard_origin_set: boolean;
  widget_url_set: boolean;
  debug: boolean;
}

import styles from "./styles.css?inline";
import { redact } from "./redact";

type Identify = { id?: string; email?: string };
type CreateResponse = { id?: number; status_token?: string; detail?: string };
type StatusResponse = { status?: string; message?: string };

declare global {
  interface Window {
    BugFixer?: { identify: (info: Identify) => void };
  }
}

const script = document.querySelector<HTMLScriptElement>("script[data-key]");
const projectKey = script?.dataset.key ?? "";
const theme = script?.dataset.theme ?? "dark";
const apiBase = (script?.dataset.api ?? new URL(script?.src ?? location.href).origin).replace(/\/+$/, "");

let reporter: Identify = {};
window.BugFixer = {
  identify(info: Identify): void {
    reporter = { ...reporter, ...info };
  },
};

const consoleErrors: string[] = [];
const nativeConsoleError = console.error.bind(console);
console.error = (...args: unknown[]): void => {
  try {
    consoleErrors.push(redact(args.map((arg) => String(arg)).join(" ")));
    if (consoleErrors.length > 10) consoleErrors.shift();
  } catch {}
  nativeConsoleError(...args);
};

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

const host = el("div", "bf-host");
host.setAttribute("data-theme", theme);
document.body.appendChild(host);
const shadow = host.attachShadow({ mode: "open" });
const style = el("style");
style.textContent = styles;
shadow.appendChild(style);

const button = el("button", "bf-fab", "Report a bug");
button.type = "button";
shadow.appendChild(button);

const panel = el("div", "bf-panel");
panel.hidden = true;
const header = el("div", "bf-header");
const close = el("button", "bf-close", "\u00d7");
close.type = "button";
header.append(el("strong", "bf-title", "Report a bug"), close);

const form = el("div", "bf-form");
const textarea = el("textarea", "bf-textarea");
textarea.placeholder = "What went wrong?";
textarea.rows = 4;
const preview = el("img", "bf-preview");
preview.alt = "Screenshot preview";
preview.hidden = true;
const actions = el("div", "bf-actions");
const attach = el("button", "bf-secondary", "Attach screenshot");
attach.type = "button";
const remove = el("button", "bf-secondary", "Remove");
remove.type = "button";
remove.hidden = true;
const fileInput = el("input");
fileInput.type = "file";
fileInput.accept = "image/*";
fileInput.hidden = true;
actions.append(attach, remove, fileInput);
const hint = el("div", "bf-hint", "You can also drop or paste a screenshot here.");
const errorBox = el("div", "bf-error");
errorBox.hidden = true;
const submit = el("button", "bf-primary", "Send report");
submit.type = "button";
form.append(textarea, preview, actions, hint, errorBox, submit);

const success = el("div", "bf-success");
success.hidden = true;
const successText = el("p", "", "Thanks! Your report has been submitted.");
const statusText = el("p", "bf-status", "");
const check = el("button", "bf-secondary", "Check status");
check.type = "button";
success.append(successText, statusText, check);

panel.append(header, form, success);
shadow.appendChild(panel);

let screenshot: File | null = null;
let previewUrl = "";
let lastReport: { id: number; token: string } | null = null;

function showError(message: string): void {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function setScreenshot(file: File): void {
  if (!file.type.startsWith("image/")) {
    showError("Please choose an image file.");
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    showError("Screenshot must be 5 MB or smaller.");
    return;
  }
  screenshot = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  preview.hidden = false;
  remove.hidden = false;
  errorBox.hidden = true;
}

function clearScreenshot(): void {
  screenshot = null;
  preview.hidden = true;
  remove.hidden = true;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = "";
}

async function submitReport(): Promise<void> {
  const message = textarea.value.trim();
  if (!message) {
    showError("Please describe the problem.");
    return;
  }
  errorBox.hidden = true;
  submit.disabled = true;
  submit.textContent = "Sending\u2026";
  try {
    const data = new FormData();
    data.append("message", message);
    data.append("page_url", location.href);
    data.append("user_agent", navigator.userAgent);
    data.append("console_log", consoleErrors.join("\n"));
    if (screenshot) data.append("screenshot", screenshot, screenshot.name || "screenshot.png");
    if (reporter.id) data.append("reporter_id", reporter.id);
    if (reporter.email) data.append("reporter_email", reporter.email);

    const response = await fetch(`${apiBase}/api/v1/reports/`, {
      method: "POST",
      headers: { "X-Project-Key": projectKey },
      body: data,
    });
    let result: CreateResponse = {};
    try {
      result = (await response.json()) as CreateResponse;
    } catch {}
    if (!response.ok || !result.id || !result.status_token) {
      showError(result.detail ?? "Could not submit the report. Please try again.");
      return;
    }
    lastReport = { id: result.id, token: result.status_token };
    form.hidden = true;
    success.hidden = false;
    statusText.textContent = "Submitted. We will take a look shortly.";
  } catch {
    showError("Network error. Please try again.");
  } finally {
    submit.disabled = false;
    submit.textContent = "Send report";
  }
}

async function checkStatus(): Promise<void> {
  if (!lastReport) return;
  check.disabled = true;
  try {
    const query = `token=${encodeURIComponent(lastReport.token)}`;
    const response = await fetch(`${apiBase}/api/v1/reports/${lastReport.id}/?${query}`);
    if (!response.ok) {
      statusText.textContent = "Status is temporarily unavailable.";
      return;
    }
    const result = (await response.json()) as StatusResponse;
    statusText.textContent = result.message ?? result.status ?? "Unknown status";
  } catch {
    statusText.textContent = "Status is temporarily unavailable.";
  } finally {
    check.disabled = false;
  }
}

button.addEventListener("click", () => {
  panel.hidden = !panel.hidden;
  if (!panel.hidden) textarea.focus();
});
close.addEventListener("click", () => {
  panel.hidden = true;
});
attach.addEventListener("click", () => fileInput.click());
remove.addEventListener("click", clearScreenshot);
fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) setScreenshot(file);
  fileInput.value = "";
});
submit.addEventListener("click", submitReport);
check.addEventListener("click", checkStatus);

panel.addEventListener("dragover", (event) => {
  event.preventDefault();
  panel.classList.add("bf-dragging");
});
panel.addEventListener("dragleave", () => panel.classList.remove("bf-dragging"));
panel.addEventListener("drop", (event) => {
  event.preventDefault();
  panel.classList.remove("bf-dragging");
  const file = event.dataTransfer?.files?.[0];
  if (file) setScreenshot(file);
});
panel.addEventListener("paste", (event) => {
  const items = event.clipboardData?.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        event.preventDefault();
        setScreenshot(file);
        return;
      }
    }
  }
});

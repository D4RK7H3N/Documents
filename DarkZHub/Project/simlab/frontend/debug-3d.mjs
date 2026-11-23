/** Debug: capture console + errors while switching to 3D. */
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9341;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), "simlab-3ddbg-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--window-size=1400,1100", "--no-first-run", "--use-gl=angle", "--use-angle=swiftshader",
  "--enable-unsafe-swiftshader", "about:blank",
], { stdio: "ignore" });

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl, { maxPayload: 64 * 1024 * 1024 });
  let id = 0; const pending = new Map(); const events = [];
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method) events.push(msg);
  });
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      id += 1; pending.set(id, { resolve, reject });
      const m = { id, method, params };
      if (sessionId) m.sessionId = sessionId;
      ws.send(JSON.stringify(m));
    });
  return { ready: new Promise((res, rej) => { ws.once("open", res); ws.once("error", rej); }), send, events };
}

let cdp;
try {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) break; } catch {}
    await sleep(500);
  }
  const browser = await fetch(`http://127.0.0.1:${PORT}/json/version`).then((r) => r.json());
  cdp = connect(browser.webSocketDebuggerUrl);
  await cdp.ready;
  const { targetId } = await cdp.send("Target.createTarget", { url: "http://localhost:5173/experiments/f2fadebd-264f-4084-afed-03d5aadb6b50" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Log.enable", {}, sessionId);

  for (let i = 0; i < 40; i++) {
    const r = await cdp.send("Runtime.evaluate", { expression: `!!document.querySelector('[data-testid="readout"]')`, returnByValue: true }, sessionId);
    if (r.result.value) break;
    await sleep(400);
  }
  console.log("page loaded, clicking 3D...");
  await cdp.send("Runtime.evaluate", { expression: `document.querySelector('[data-testid="view-3d"]')?.click()` }, sessionId);
  await sleep(15000);
  const state = await cdp.send("Runtime.evaluate", {
    expression: `JSON.stringify({
      skeleton: !!document.querySelector('[data-testid="arena3d-skeleton"]'),
      canvas: !!document.querySelector('[data-testid="arena3d-canvas"]'),
      webglNote: document.querySelector(".text-amber-400")?.innerText ?? null,
    })`,
    returnByValue: true,
  }, sessionId);
  console.log("state:", state.result.value);
  const logs = cdp.events
    .filter((m) => ["Runtime.consoleAPICalled", "Runtime.exceptionThrown", "Log.entryAdded", "Network.loadingFailed"].includes(m.method))
    .map((m) => {
      if (m.method === "Runtime.exceptionThrown") return "EXC " + JSON.stringify(m.params.exceptionDetails).slice(0, 1600);
      if (m.method === "Log.entryAdded") return "LOG[" + m.params.entry.level + "] " + m.params.entry.text.slice(0, 300) + " " + (m.params.entry.url ?? "");
      if (m.method === "Network.loadingFailed") return "NETFAIL " + m.params.errorText + " " + m.params.type;
      return "CONSOLE[" + m.params.type + "] " + (m.params.args ?? []).map((a) => (a.description ?? a.value ?? "")).join(" ").slice(0, 300);
    });
  console.log(logs.slice(0, 30).join("\n---\n") || "(no console output)");
} catch (e) {
  console.error("FAIL:", e.message);
} finally {
  try { cdp?.close?.(); } catch {}
  chrome.kill();
  process.exit(0);
}

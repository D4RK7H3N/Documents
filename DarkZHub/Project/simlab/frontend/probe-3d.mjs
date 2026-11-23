/** Probe: how many instances are actually drawn, and where are they? */
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9342;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "simlab-probe-"));
const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--window-size=1400,1100", "--no-first-run", "--use-gl=angle", "--use-angle=swiftshader",
  "--enable-unsafe-swiftshader", "about:blank",
], { stdio: "ignore" });

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl, { maxPayload: 64 * 1024 * 1024 });
  let id = 0; const pending = new Map();
  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    }
  });
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      id += 1; pending.set(id, { resolve, reject });
      const m = { id, method, params };
      if (sessionId) m.sessionId = sessionId;
      ws.send(JSON.stringify(m));
    });
  return { ready: new Promise((res, rej) => { ws.once("open", res); ws.once("error", rej); }), send };
}

async function evalJson(cdp, s, expr) {
  const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }, s);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
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
  for (let i = 0; i < 40; i++) {
    const r = await evalJson(cdp, sessionId, `!!document.querySelector('[data-testid="readout"]')`).catch(() => false);
    if (r) break;
    await sleep(400);
  }
  await evalJson(cdp, sessionId, `document.querySelector('[data-testid="view-3d"]').click()`);
  for (let i = 0; i < 60; i++) {
    const ok = await evalJson(cdp, sessionId, `!!document.querySelector('[data-testid="arena3d-canvas"]')`).catch(() => false);
    if (ok) break;
    await sleep(400);
  }
  await sleep(4000);
  await evalJson(cdp, sessionId, `document.querySelector('[data-testid="species-beetle"]').click()`);
  await evalJson(cdp, sessionId, `document.querySelector('[data-testid="quality-high"]').click()`);
  await sleep(2500);

  const stats = await evalJson(cdp, sessionId, `(() => {
    const scene = window.__r3fScene;
    if (!scene) return { error: "no scene hook" };
    const instanced = [];
    scene.traverse((o) => {
      if (o.isInstancedMesh) {
        const m = o.instanceMatrix.array;
        instanced.push({
          count: o.count,
          capacity: o.instanceMatrix.count,
          firstPositions: [0, 1, 2].slice(0, Math.min(3, o.count)).map((i) => [
            +m[i * 16 + 12].toFixed(2), +m[i * 16 + 13].toFixed(2), +m[i * 16 + 14].toFixed(2),
          ]),
        });
      }
    });
    return { instanced };
  })()`);
  console.log("stats:", JSON.stringify(stats));
} catch (e) {
  console.error("FAIL:", e.message);
} finally {
  try { cdp?.close?.(); } catch {}
  chrome.kill();
  process.exit(0);
}

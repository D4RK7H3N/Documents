/**
 * Headless verification of the 3D Evolution View.
 * Chrome runs with SwiftShader (GPU-less software WebGL) -- frame rates
 * reported here are SOFTWARE rendering numbers, not GPU numbers.
 *
 * Captures: gen 1 / mid / last screenshots for each species, the extinction
 * run, an fps reading at quality high (400 instances), and a 20x
 * mount/unmount cycle leak check via renderer.info.memory.
 */
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9340;
const FRONT = "http://localhost:5173";
const DEF_ID = "f2fadebd-264f-4084-afed-03d5aadb6b50";
const EXT_ID = "0fb2691f-173a-45a7-bcd6-ea37dd86f02e";
const OUT = process.argv[2] || ".";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), "simlab-3d-"));
const chrome = spawn(CHROME, [
  "--headless=new",
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  "--window-size=1400,1100",
  "--hide-scrollbars",
  "--no-first-run",
  "--use-gl=angle",
  "--use-angle=swiftshader",
  "--enable-unsafe-swiftshader",
  "about:blank",
], { stdio: "ignore" });

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl, { maxPayload: 64 * 1024 * 1024 });
  let id = 0;
  const pending = new Map();
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
      id += 1;
      pending.set(id, { resolve, reject });
      const m = { id, method, params };
      if (sessionId) m.sessionId = sessionId;
      ws.send(JSON.stringify(m));
    });
  return { ready: new Promise((res, rej) => { ws.once("open", res); ws.once("error", rej); }), send };
}

async function evalJson(cdp, sessionId, expr) {
  const r = await cdp.send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }, sessionId);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
}

async function waitSelector(s, selector, timeoutMs = 20000) {
  return evalJson(cdp, s, `
    new Promise((resolve) => {
      const t0 = Date.now();
      const tick = () => {
        if (document.querySelector(${JSON.stringify(selector)})) resolve(true);
        else if (Date.now() - t0 > ${timeoutMs}) resolve(false);
        else setTimeout(tick, 150);
      };
      tick();
    })`);
}

const click = (s, sel) => evalJson(cdp, s, `(() => { document.querySelector(${JSON.stringify(sel)})?.click(); return true; })()`);
const wait = (ms) => sleep(ms);

async function scrub(s, gen) {
  await evalJson(cdp, s, `(() => {
    const el = document.querySelector('[data-testid="scrubber"]');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(el, String(${gen}));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await wait(600);
}

async function screenshot(s, name) {
  const r = await cdp.send("Page.captureScreenshot", { format: "png" }, s);
  writeFileSync(join(OUT, name), Buffer.from(r.data, "base64"));
}

let cdp;
const results = {};
try {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) break; } catch {}
    await sleep(500);
  }
  const browser = await fetch(`http://127.0.0.1:${PORT}/json/version`).then((r) => r.json());
  cdp = connect(browser.webSocketDebuggerUrl);
  await cdp.ready;

  // Identify the GL renderer honestly.
  const { targetId: probeT } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId: probeS } = await cdp.send("Target.attachToTarget", { targetId: probeT, flatten: true });
  results.renderer = await evalJson(cdp, probeS, `(() => {
    const c = document.createElement("canvas");
    const gl = c.getContext("webgl2") || c.getContext("webgl");
    if (!gl) return "NO WEBGL";
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  })()`);
  await cdp.send("Target.closeTarget", { targetId: probeT });

  async function open3d(expId, sessionId) {
    await evalJson(cdp, sessionId, `location.href = ${JSON.stringify(`${FRONT}/experiments/${expId}`)}`);
    await waitSelector(sessionId, '[data-testid="readout"]');
    await click(sessionId, '[data-testid="view-3d"]');
    const ok = await waitSelector(sessionId, '[data-testid="arena3d-canvas"]', 30000);
    if (!ok) throw new Error("3D canvas never appeared");
    await wait(2500); // lazy chunk + first frames
    return true;
  }

  for (const species of ["mosquito", "beetle", "fruit_fly"]) {
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await open3d(DEF_ID, sessionId);

    await click(sessionId, `[data-testid="species-${species}"]`);
    await click(sessionId, '[data-testid="quality-high"]');
    await wait(800);

    // Deterministic paused states at gen 1 / mid / last.
    await click(sessionId, '[data-testid="play-pause"]'); // pause
    await click(sessionId, '[data-testid="restart"]');
    await wait(700);
    await screenshot(sessionId, `3d-${species}-gen1.png`);
    results[`${species}_gen1`] = await evalJson(cdp, sessionId,
      `document.querySelector('[data-testid="readout"]')?.innerText`);

    await scrub(sessionId, 100);
    await screenshot(sessionId, `3d-${species}-gen100.png`);
    results[`${species}_gen100`] = await evalJson(cdp, sessionId,
      `document.querySelector('[data-testid="readout"]')?.innerText`);

    await scrub(sessionId, 200);
    await screenshot(sessionId, `3d-${species}-gen200.png`);
    results[`${species}_gen200`] = await evalJson(cdp, sessionId,
      `document.querySelector('[data-testid="readout"]')?.innerText`);

    // fps at 1x, quality high (400 instances), playing.
    await scrub(sessionId, 1);
    await click(sessionId, '[data-testid="play-pause"]'); // play
    await wait(5000);
    results[`${species}_fps_high`] = await evalJson(cdp, sessionId,
      `document.querySelector('[data-testid="fps"]')?.innerText`);
    await click(sessionId, '[data-testid="play-pause"]'); // pause
    results[`${species}_info`] = await evalJson(cdp, sessionId,
      `window.__r3fInfo ? window.__r3fInfo() : null`);

    await cdp.send("Target.closeTarget", { targetId });
    await wait(400);
  }

  // Extinction run (population 15, seed 11) in 3D at its final generation.
  {
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await open3d(EXT_ID, sessionId);
    await click(sessionId, '[data-testid="play-pause"]');
    await scrub(sessionId, 14);
    await screenshot(sessionId, "3d-extinct-gen14.png");
    results.extinct = {
      readout: await evalJson(cdp, sessionId, `document.querySelector('[data-testid="readout"]')?.innerText`),
      overlay: await evalJson(cdp, sessionId, `document.querySelector('[data-testid="extinct-overlay"]')?.innerText ?? null`),
    };
    await cdp.send("Target.closeTarget", { targetId });
  }

  // Leak check: 20 mount/unmount cycles, renderer.info.memory must not grow.
  {
    const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await open3d(DEF_ID, sessionId);
    await click(sessionId, '[data-testid="play-pause"]');
    const samples = [];
    for (let i = 0; i < 20; i++) {
      await click(sessionId, '[data-testid="view-2d"]');
      await wait(350);
      await click(sessionId, '[data-testid="view-3d"]');
      await waitSelector(sessionId, '[data-testid="arena3d-canvas"]', 20000);
      await wait(700);
      const info = await evalJson(cdp, sessionId, `window.__r3fInfo ? window.__r3fInfo() : null`);
      samples.push(info);
    }
    results.leakCheck = {
      first: samples[0],
      last: samples[samples.length - 1],
      geometries: samples.map((s) => s?.geometries ?? null),
      textures: samples.map((s) => s?.textures ?? null),
    };
    await cdp.send("Target.closeTarget", { targetId });
  }

  console.log(JSON.stringify(results, null, 2));
} catch (e) {
  console.error("FAIL:", e.message);
  process.exitCode = 1;
} finally {
  try { cdp?.close?.(); } catch {}
  chrome.kill();
  process.exit(process.exitCode ?? 0);
}

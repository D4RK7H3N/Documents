"use client";

import { useEffect, useState } from "react";
import { useToasts } from "@/lib/toast-context";
import CodeInput from "@/components/CodeInput";

const OTP_COOLDOWN_S = 60;

function DevCodeHint({ item }: { item: { channel: string; target: string; code: string } | null }) {
  if (process.env.NODE_ENV === "production" || !item) return null;
  return (
    <p className="mt-2 rounded-lg border border-dashed border-white/15 bg-black/20 p-2 font-mono-tabular text-[11px] text-text-muted">
      dev code: {item.channel} → {item.target}: <span className="text-accent-cyan">{item.code}</span>
    </p>
  );
}

export default function AccountSecurity({
  email,
  phone,
  emailVerified,
  phoneVerified,
  totpEnabled,
}: {
  email: string;
  phone: string | null;
  emailVerified: boolean;
  phoneVerified: boolean;
  totpEnabled: boolean;
}) {
  const { success } = useToasts();
  const [verified, setVerified] = useState({ email: emailVerified, phone: phoneVerified });
  const [phoneInput, setPhoneInput] = useState(phone ?? "");
  const [active, setActive] = useState<"email" | "phone" | null>(null);
  const [step, setStep] = useState<"idle" | "input">("idle");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [cooldownLeft, setCooldownLeft] = useState(0);
  const [devCode, setDevCode] = useState<{ channel: string; target: string; code: string } | null>(null);

  const [totpOn, setTotpOn] = useState(totpEnabled);
  const [totpPhase, setTotpPhase] = useState<"idle" | "setup" | "codes" | "disable">("idle");
  const [totpSetup, setTotpSetup] = useState<{ secret: string; qr: string } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  useEffect(() => {
    if (cooldownLeft <= 0) return;
    const t = setTimeout(() => setCooldownLeft((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldownLeft]);

  const send = async (target: string, waitFor: "email" | "phone") => {
    setBusy(true);
    setErr(null);
    setDevCode(null);
    try {
      const res = await fetch("/api/otp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: waitFor === "email" ? "EMAIL" : "PHONE", target }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error ?? "Could not send the code");
        return false;
      }
      if (data.debugCode) {
        setDevCode({ channel: waitFor === "email" ? "EMAIL" : "PHONE", target, code: data.debugCode });
      }
      setCooldownLeft(OTP_COOLDOWN_S);
      setStep("input");
      setCode("");
      return true;
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    if (!active || code.length !== 6) {
      setErr("Enter the 6-digit code");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const channel = active === "email" ? "EMAIL" : "PHONE";
      const phone = active === "phone" ? (phoneInput.trim() || null) : undefined;
      const res = await fetch("/api/otp/verify-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel, code, ...(phone ? { phone } : {}) }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error ?? "Verification failed");
        return;
      }
      setVerified((v) => ({ ...v, [active]: true }));
      if (active === "phone") setPhoneInput((p) => (phoneInput.trim() ? phoneInput.trim() : p));
      setActive(null);
      setStep("idle");
      setCode("");
      setDevCode(null);
      success(active === "email" ? "Email verified" : "Phone verified");
    } finally {
      setBusy(false);
    }
  };

  const badge = (ok: boolean) =>
    ok ? (
      <span className="rounded-full border border-lime-400/40 bg-lime-400/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-lime-300">
        Verified
      </span>
    ) : (
      <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-text-muted">
        Not verified
      </span>
    );

  const startTotpSetup = async () => {
    setBusy(true);
    setErr(null);
    setTotpPhase("idle");
    try {
      const res = await fetch("/api/account/totp/setup");
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error ?? "Could not start the setup");
        return;
      }
      setTotpSetup({ secret: data.secret, qr: data.qr });
      setTotpPhase("setup");
      setTotpCode("");
    } finally {
      setBusy(false);
    }
  };

  const confirmTotp = async () => {
    if (totpCode.length !== 6) {
      setErr("Enter the 6-digit code");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/account/totp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error ?? "Verification failed");
        return;
      }
      setRecoveryCodes(data.codes ?? []);
      setTotpOn(true);
      setTotpPhase("codes");
      setTotpCode("");
    } finally {
      setBusy(false);
    }
  };

  const disableTotp = async () => {
    if (totpCode.length !== 6) {
      setErr("Enter the 6-digit code");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/api/account/totp/disable", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setErr(data.error ?? "Could not disable the authenticator");
        return;
      }
      setTotpOn(false);
      setTotpPhase("idle");
      setTotpCode("");
      success("Authenticator disabled");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="glass-panel rounded-xl p-6 flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-lg font-bold">SECURITY</h2>
        <p className="text-sm text-text-muted">
          Verified channels are used for your 2-step login check at sign-in.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="text-xs uppercase tracking-[0.14em] text-text-muted">Email</span>
            <span className="text-sm truncate">{email}</span>
          </div>
          <div className="flex items-center gap-2">
            {badge(verified.email)}
            {!verified.email && active !== "email" && (
              <button
                type="button"
                onClick={() => {
                  setActive("email");
                  setStep("idle");
                  setErr(null);
                  setCode("");
                }}
                className="btn-ghost rounded-lg px-3 py-1 text-xs hover:bg-surface-hover transition-colors"
              >
                Verify
              </button>
            )}
          </div>
        </div>

        {active === "email" && (
          <div className="flex flex-col gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
            {step === "idle" ? (
              <button
                type="button"
                onClick={() => send(email, "email")}
                disabled={busy}
                className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
              >
                {busy ? "Sending..." : "Send code to this email"}
              </button>
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-text-muted">We sent a code to {email}.</p>
                <CodeInput value={code} onChange={setCode} disabled={busy} invalid={!!err} />
                {err && <p className="text-[11px] text-rose-400">{err}</p>}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => verify()}
                    disabled={busy || code.length !== 6}
                    className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
                  >
                    {busy ? "Checking..." : "Verify"}
                  </button>
                  <button
                    type="button"
                    onClick={() => send(email, "email")}
                    disabled={busy || cooldownLeft > 0}
                    className="text-xs text-accent-cyan underline underline-offset-2 hover:text-text disabled:opacity-40"
                  >
                    {cooldownLeft > 0 ? `Resend in ${cooldownLeft}s` : "Resend code"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setActive(null);
                      setErr(null);
                      setStep("idle");
                    }}
                    className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
                  >
                    Cancel
                  </button>
                </div>
                <DevCodeHint item={devCode} />
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <div className="flex flex-col gap-0.5 min-w-0">
            <span className="text-xs uppercase tracking-[0.14em] text-text-muted">Phone</span>
            <span className="text-sm truncate">{phoneInput || "No phone on file"}</span>
          </div>
          <div className="flex items-center gap-2">
            {badge(verified.phone)}
            {active !== "phone" && (
              <button
                type="button"
                onClick={() => {
                  setActive("phone");
                  setStep("idle");
                  setErr(null);
                }}
                className="btn-ghost rounded-lg px-3 py-1 text-sm hover:bg-surface-hover transition-colors"
              >
                {verified.phone ? "Change" : "Verify"}
              </button>
            )}
          </div>
        </div>

        {active === "phone" && (
          <div className="flex flex-col gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
            {step === "idle" ? (
              <div className="flex flex-col gap-2">
                <input
                  type="tel"
                  placeholder="+1 555 000 0000"
                  value={phoneInput}
                  onChange={(e) => setPhoneInput(e.target.value)}
                  className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                />
                {err && <p className="text-[11px] text-rose-400">{err}</p>}
                <button
                  type="button"
                  onClick={() => phoneInput.trim() && send(phoneInput.trim(), "phone")}
                  disabled={busy || !phoneInput.trim()}
                  className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
                >
                  {busy ? "Sending..." : "Send code to this number"}
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-text-muted">We sent a code to {phoneInput}.</p>
                <CodeInput value={code} onChange={setCode} disabled={busy} invalid={!!err} />
                {err && <p className="text-[11px] text-rose-400">{err}</p>}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => verify()}
                    disabled={busy || code.length !== 6}
                    className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
                  >
                    {busy ? "Checking..." : "Verify"}
                  </button>
                  <button
                    type="button"
                    onClick={() => phoneInput.trim() && send(phoneInput.trim(), "phone")}
                    disabled={busy || cooldownLeft > 0}
                    className="text-xs text-accent-cyan underline underline-offset-2 hover:text-text disabled:opacity-40"
                  >
                    {cooldownLeft > 0 ? `Resend in ${cooldownLeft}s` : "Resend code"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setActive(null);
                      setErr(null);
                      setStep("idle");
                    }}
                    className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <DevCodeHint item={devCode} />

      <div className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-xs uppercase tracking-[0.14em] text-text-muted">Authenticator app</span>
          <span className="text-sm truncate">
            {totpOn ? "2-step codes from your app at login" : "Not enabled — you log in via email/phone codes"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => (totpOn ? setTotpPhase("disable") : startTotpSetup())}
          disabled={busy}
          className="btn-ghost rounded-lg px-3 py-1 text-sm hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          {totpOn ? "Disable" : "Enable"}
        </button>
      </div>

      {totpPhase === "setup" && totpSetup && (
        <div className="flex flex-col gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <p className="text-sm text-text-muted">
            Scan this QR in your authenticator app, then enter the 6-digit code it shows.
          </p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={totpSetup.qr} alt="TOTP QR code" className="h-40 w-40 self-center rounded-lg bg-white p-2" />
          <p className="self-center font-mono-tabular text-xs text-text-muted break-all">
            {totpSetup.secret}
          </p>
          <CodeInput value={totpCode} onChange={setTotpCode} disabled={busy} invalid={!!err} />
          {err && <p className="text-[11px] text-rose-400">{err}</p>}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={confirmTotp}
              disabled={busy || totpCode.length !== 6}
              className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
            >
              {busy ? "Checking..." : "Verify & enable"}
            </button>
            <button
              type="button"
              onClick={() => setTotpPhase("idle")}
              className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {totpPhase === "codes" && (
        <div className="flex flex-col gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <p className="text-sm text-text-muted">
            Save these one-time recovery codes somewhere safe — they are shown only once and unlock
            your account if you lose the authenticator app.
          </p>
          <div className="grid grid-cols-1 gap-1 font-mono-tabular text-xs sm:grid-cols-2">
            {recoveryCodes.map((c) => (
              <span key={c} className="rounded bg-black/30 px-2 py-1 text-center">
                {c}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setTotpPhase("idle")}
            className="btn-primary rounded-lg px-3 py-2 text-sm"
          >
            I saved them
          </button>
        </div>
      )}

      {totpPhase === "disable" && (
        <div className="flex flex-col gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <p className="text-sm text-text-muted">
            Enter a current code from your authenticator app to disable it.
          </p>
          <CodeInput value={totpCode} onChange={setTotpCode} disabled={busy} invalid={!!err} />
          {err && <p className="text-[11px] text-rose-400">{err}</p>}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={disableTotp}
              disabled={busy || totpCode.length !== 6}
              className="btn-primary rounded-lg px-3 py-2 text-sm disabled:opacity-50"
            >
              {busy ? "Checking..." : "Disable"}
            </button>
            <button
              type="button"
              onClick={() => setTotpPhase("idle")}
              className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
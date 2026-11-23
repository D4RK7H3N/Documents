"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Reveal from "@/components/Reveal";
import CodeInput from "@/components/CodeInput";

type Step = "email" | "code" | "newpass" | "done";

function scorePassword(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

const STRENGTH_LABELS = ["Too short", "Weak", "Okay", "Good", "Strong"];
const STRENGTH_COLORS = ["", "bg-rose-500", "bg-amber-400", "bg-lime-400", "bg-accent-cyan"];

export default function ForgotPasswordForm() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldownLeft, setCooldownLeft] = useState(0);
  const [devCode, setDevCode] = useState<string | null>(null);

  useEffect(() => {
    if (cooldownLeft <= 0) return;
    const t = setTimeout(() => setCooldownLeft((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldownLeft]);

  const requestCode = async () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Enter a valid email address");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/forgot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error ?? "Something went wrong");
        return;
      }
      setDevCode(data.debugCode ?? null);
      setCooldownLeft(60);
      setCode("");
      setStep("code");
    } finally {
      setBusy(false);
    }
  };

  const verifyCode = async () => {
    if (code.length !== 6) {
      setError("Enter the 6-digit code");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/forgot/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), code }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.attemptsLeft ? `${data.error} ${data.attemptsLeft} attempt${data.attemptsLeft === 1 ? "" : "s"} left.` : (data.error ?? "Verification failed"));
        return;
      }
      setStep("newpass");
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async () => {
    if (code.length !== 6) {
      setError("Enter the 6-digit code");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/forgot/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), code, newPassword: password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.attemptsLeft ? `${data.error} ${data.attemptsLeft} attempt${data.attemptsLeft === 1 ? "" : "s"} left.` : (data.error ?? "Reset failed"));
        return;
      }
      setStep("done");
    } finally {
      setBusy(false);
    }
  };

  const score = scorePassword(password);

  return (
    <Reveal className="w-full max-w-md">
      <div className="glow-card glow-card--active rounded-2xl flex flex-col gap-5 p-6 sm:p-8">
        {step === "done" ? (
          <div className="flex flex-col gap-5">
            <h1 className="font-display text-2xl font-bold">Password updated</h1>
            <p className="text-sm text-text-muted">
              All your sessions were signed out. Log in again with your new password.
            </p>
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="btn-primary press-down rounded-lg px-3 py-2.5"
            >
              Go to log in
            </button>
          </div>
        ) : step === "email" ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-cyan">
                Account recovery
              </span>
              <h1 className="font-display text-2xl font-bold">Forgot your password?</h1>
              <p className="text-sm text-text-muted">
                Enter your email and we&apos;ll send a code to reset it.
              </p>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Email
              </span>
              <input
                type="email"
                placeholder="you@grid.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                  error ? "border-rose-500/60 focus:ring-rose-500/40" : "focus:ring-accent-cyan/60"
                }`}
              />
            </label>
            {error && <p className="text-[11px] text-rose-400">{error}</p>}
            <button
              type="button"
              onClick={requestCode}
              disabled={busy}
              className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
            >
              {busy ? "Sending..." : "Send code"}
            </button>
            <Link href="/login" className="text-xs text-text-muted underline underline-offset-2 hover:text-text">
              Back to log in
            </Link>
          </div>
        ) : step === "code" ? (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-cyan">
                Step 1 of 2
              </span>
              <h1 className="font-display text-xl font-bold">Enter the code</h1>
              <p className="text-sm text-text-muted">
                We sent a 6-digit code to <span className="text-text">{email}</span>.
              </p>
            </div>
            <CodeInput value={code} onChange={setCode} disabled={busy} invalid={!!error} />
            {error && <p className="text-[11px] text-rose-400">{error}</p>}
            <button
              type="button"
              onClick={verifyCode}
              disabled={busy || code.length !== 6}
              className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
            >
              {busy ? "Verifying..." : "Continue"}
            </button>
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => {
                  setStep("email");
                  setError(null);
                }}
                className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
              >
                Edit email
              </button>
              <button
                type="button"
                onClick={requestCode}
                disabled={cooldownLeft > 0 || busy}
                className="text-xs text-accent-cyan underline underline-offset-2 hover:text-text disabled:opacity-40"
              >
                {cooldownLeft > 0 ? `Resend in ${cooldownLeft}s` : "Resend code"}
              </button>
            </div>
            {devCode && process.env.NODE_ENV !== "production" && (
              <div className="flex flex-col gap-1 rounded-lg border border-dashed border-white/15 bg-black/20 p-3 font-mono-tabular text-[11px] text-text-muted">
                <span className="uppercase tracking-[0.2em] text-[9px]">Dev codes</span>
                <span>
                  EMAIL → {email}: <span className="text-accent-cyan">{devCode}</span>
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-cyan">
                Step 2 of 2
              </span>
              <h1 className="font-display text-xl font-bold">Choose a new password</h1>
              <p className="text-sm text-text-muted">
                At least 8 characters. All your other sessions will be signed out.
              </p>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                New password
              </span>
              <input
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              />
              {password.length > 0 && (
                <div className="flex flex-col gap-1">
                  <div className="flex gap-1" aria-hidden>
                    {[0, 1, 2, 3].map((i) => (
                      <span
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i < score ? STRENGTH_COLORS[score] : "bg-white/10"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-text-muted">
                    {STRENGTH_LABELS[score]}
                  </span>
                </div>
              )}
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                Confirm password
              </span>
              <input
                type="password"
                placeholder="Repeat your password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              />
            </label>
            {error && <p className="text-[11px] text-rose-400">{error}</p>}
            <button
              type="button"
              onClick={resetPassword}
              disabled={busy}
              className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
            >
              {busy ? "Resetting..." : "Reset password"}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("code");
                setError(null);
              }}
              className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
            >
              Back
            </button>
          </div>
        )}
      </div>
    </Reveal>
  );
}

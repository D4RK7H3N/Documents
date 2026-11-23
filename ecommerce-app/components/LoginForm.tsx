"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToasts } from "@/lib/toast-context";
import Reveal from "@/components/Reveal";
import CodeInput from "@/components/CodeInput";

type Mode = "login" | "register";
type Field = "name" | "email" | "phone" | "password" | "confirm" | "terms";
type Errors = Partial<Record<Field | "server", string>>;
type Channel = "EMAIL" | "PHONE";

interface FormState {
  name: string;
  email: string;
  phone: string;
  password: string;
  confirm: string;
  terms: boolean;
}

interface DevCode {
  id: number;
  channel: Channel;
  target: string;
  code: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^[0-9+\-\s()]{8,20}$/;
const OTP_COOLDOWN_S = 60;

const EMPTY_FORM: FormState = { name: "", email: "", phone: "", password: "", confirm: "", terms: false };

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

function validateField(field: Field, mode: Mode, f: FormState): string {
  switch (field) {
    case "name":
      return mode === "register" && f.name.trim().length < 2
        ? "Name must be at least 2 characters"
        : "";
    case "email":
      return !EMAIL_RE.test(f.email.trim()) ? "Enter a valid email address" : "";
    case "phone":
      if (mode !== "register") return "";
      if (f.phone.trim() === "") return "Phone number is required";
      return !PHONE_RE.test(f.phone.trim()) ? "Enter a valid phone number" : "";
    case "password":
      return mode === "register"
        ? f.password.length < 8
          ? "Password must be at least 8 characters"
          : ""
        : f.password.length < 1
          ? "Enter your password"
          : "";
    case "confirm":
      return mode === "register" && f.confirm !== f.password ? "Passwords don't match" : "";
    case "terms":
      return mode === "register" && !f.terms ? "Please accept the terms to continue" : "";
  }
}

function validateAll(mode: Mode, f: FormState): Errors {
  const errs: Errors = {};
  for (const field of ["name", "email", "phone", "password", "confirm", "terms"] as const) {
    const msg = validateField(field, mode, f);
    if (msg) errs[field] = msg;
  }
  return errs;
}

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {open ? (
        <>
          <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7" />
          <circle cx="12" cy="12" r="3" />
        </>
      ) : (
        <>
          <path d="M17.9 17.9A10.4 10.4 0 0 1 12 19c-7 0-11-7-11-7a18.6 18.6 0 0 1 4.7-5.4M9.9 4.2A10.2 10.2 0 0 1 12 4c7 0 11 7 11 7a18.7 18.7 0 0 1-2.9 3.7M3 3l18 18" />
        </>
      )}
    </svg>
  );
}

export default function LoginForm({
  categories,
  productCount,
}: {
  categories: string[];
  productCount: number;
}) {
  const router = useRouter();
  const { success } = useToasts();
  const [mode, setMode] = useState<Mode>("login");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<Errors>({});
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);

  const [otpStage, setOtpStage] = useState<"none" | "email" | "phone">("none");
  const [otpTarget, setOtpTarget] = useState<{ channel: Channel; target: string } | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpVerifying, setOtpVerifying] = useState(false);
  const [emailProof, setEmailProof] = useState<string | null>(null);
  const [cooldownLeft, setCooldownLeft] = useState(0);

  const [challenge, setChallenge] = useState<{
    token: string;
    channel: Channel | "TOTP";
    targetMasked: string;
    remember: boolean;
  } | null>(null);
  const [usedEmailInstead, setUsedEmailInstead] = useState(false);
  const [usingRecovery, setUsingRecovery] = useState(false);

  const [devCodes, setDevCodes] = useState<DevCode[]>([]);
  const devCodeId = useRef(0);

  useEffect(() => {
    if (cooldownLeft <= 0) return;
    const t = setTimeout(() => setCooldownLeft((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldownLeft]);

  const recordDevCode = (channel: Channel, target: string, code: string | undefined) => {
    if (!code) return;
    setDevCodes((prev) => {
      const next = [...prev, { id: (devCodeId.current += 1), channel, target, code }];
      return next.slice(-3);
    });
  };

  const setField = (field: Field, value: string | boolean) => {
    const next = { ...form, [field]: value };
    setForm(next);
    const msg = validateField(field, mode, next);
    setErrors((prev) => ({ ...prev, [field]: msg || undefined, server: undefined }));
  };

  const onBlur = (field: Field) => {
    setTouched((t) => ({ ...t, [field]: true }));
    const msg = validateField(field, mode, form);
    setErrors((prev) => ({ ...prev, [field]: msg || undefined }));
  };

  const switchMode = (m: Mode) => {
    if (m === mode) return;
    setMode(m);
    setErrors({});
    setTouched({});
    setShowPass(false);
    setOtpStage("none");
    setOtpCode("");
    setOtpError(null);
    setEmailProof(null);
    setChallenge(null);
    setUsedEmailInstead(false);
    setCooldownLeft(0);
    setForm((prev) => ({ ...EMPTY_FORM, email: prev.email }));
  };

  const backToForm = () => {
    setOtpStage("none");
    setOtpCode("");
    setOtpError(null);
    setEmailProof(null);
    setChallenge(null);
    setUsedEmailInstead(false);
    setUsingRecovery(false);
    setCooldownLeft(0);
  };

  const sendOtp = async (channel: Channel, target: string, forSignup = false) => {
    setOtpVerifying(true);
    setOtpError(null);
    try {
      const res = await fetch("/api/otp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel, target, forSignup }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setOtpError(data.error ?? "Could not send the code");
        return false;
      }
      recordDevCode(channel, target, data.debugCode);
      setCooldownLeft(OTP_COOLDOWN_S);
      return true;
    } finally {
      setOtpVerifying(false);
    }
  };

  const submitOtpCode = async (channel: Channel, target: string) => {
    if (otpCode.length !== 6) {
      setOtpError("Enter the 6-digit code");
      return;
    }
    setOtpVerifying(true);
    setOtpError(null);
    try {
      const res = await fetch("/api/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel, target, code: otpCode }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setOtpError(
          data.attemptsLeft
            ? `${data.error} ${data.attemptsLeft} attempt${data.attemptsLeft === 1 ? "" : "s"} left.`
            : (data.error ?? "Incorrect code"),
        );
        return false;
      }
      return data.proof as string;
    } finally {
      setOtpVerifying(false);
    }
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validateAll(mode, form);
    setErrors(errs);
    setTouched({ name: true, email: true, phone: true, password: true, confirm: true, terms: true });
    if (Object.values(errs).some(Boolean)) return;

    setLoading(true);
    try {
      if (mode === "login") {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: form.email.trim(), password: form.password }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setErrors({ server: data.error ?? "Invalid email or password" });
          return;
        }
        if (data.requireOtp) {
          recordDevCode(data.channel, data.targetMasked, data.debugCode);
          setChallenge({
            token: data.challenge,
            channel: data.channel,
            targetMasked: data.targetMasked,
            remember: true,
          });
          setCooldownLeft(OTP_COOLDOWN_S);
          setOtpCode("");
          setOtpError(null);
          return;
        }
        if (data.requireTotp) {
          setChallenge({ token: data.challenge, channel: "TOTP", targetMasked: "", remember: true });
          setOtpCode("");
          setOtpError(null);
          setUsingRecovery(false);
          return;
        }
        success("Welcome back");
        router.push("/");
        router.refresh();
        return;
      }

      const sent = await sendOtp("EMAIL", form.email.trim(), true);
      if (!sent) return;
      const sentPhone = await sendOtp("PHONE", form.phone.trim(), true);
      if (!sentPhone) return;
      setOtpTarget({ channel: "EMAIL", target: form.email.trim() });
      setOtpStage("email");
      setOtpCode("");
      setOtpError(null);
    } finally {
      setLoading(false);
    }
  }

  const verifyCurrentStep = async () => {
    if (!otpTarget) return;
    const proof = await submitOtpCode(otpTarget.channel, otpTarget.target);
    if (!proof) return;
    if (otpTarget.channel === "EMAIL") {
      setEmailProof(proof);
      const phoneSent = await sendOtp("PHONE", form.phone.trim(), true);
      if (!phoneSent) return;
      setOtpTarget({ channel: "PHONE", target: form.phone.trim() });
      setOtpCode("");
      setOtpError(null);
      return;
    }
    registerWithProofs(proof);
  };

  const registerWithProofs = async (phoneProof: string) => {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
          phone: form.phone.trim(),
          emailProof: emailProof ?? "",
          phoneProof,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (data.error === "Email address not verified" || data.error === "Phone number not verified") {
          setOtpError(data.error);
          return;
        }
        setOtpError(data.error?.formErrors?.[0] ?? data.error ?? "Registration failed");
        return;
      }
      success("Account created");
      router.push("/");
      router.refresh();
    } finally {
      setLoading(false);
    }
  };

  const resendCurrent = async () => {
    if (!otpTarget) return;
    await sendOtp(otpTarget.channel, otpTarget.target, mode === "register");
  };

  const loginWithCode = async () => {
    if (!challenge) return;
    const isRecovery = challenge.channel === "TOTP" && usingRecovery;
    if (isRecovery ? !/^[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(otpCode.trim().toUpperCase()) : otpCode.length !== 6) {
      setOtpError(isRecovery ? "Enter a recovery code like XXXX-XXXX" : "Enter the 6-digit code");
      return;
    }
    setOtpVerifying(true);
    setOtpError(null);
    try {
      const res = await fetch("/api/auth/otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          challenge: challenge.token,
          code: isRecovery ? otpCode.trim().toUpperCase() : otpCode,
          remember: challenge.remember,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setOtpError(
          data.attemptsLeft
            ? `${data.error} ${data.attemptsLeft} attempt${data.attemptsLeft === 1 ? "" : "s"} left.`
            : (data.error ?? "Incorrect code"),
        );
        if (!data.attemptsLeft) {
          setChallenge(null);
          setOtpCode("");
          setErrors({ server: data.error ?? "Login session expired. Log in again." });
          setOtpStage("none");
        }
        return;
      }
      success("Welcome back");
      router.push("/");
      router.refresh();
    } finally {
      setOtpVerifying(false);
    }
  };

  const resendLogin = async (emailInstead: boolean) => {
    if (!challenge) return;
    setOtpVerifying(true);
    setOtpError(null);
    try {
      const res = await fetch("/api/auth/otp/resend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge: challenge.token, emailInstead }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setOtpError(data.error ?? "Could not resend the code");
        return;
      }
      recordDevCode(data.channel, data.targetMasked, data.debugCode);
      setChallenge({
        token: data.challenge,
        channel: data.channel,
        targetMasked: data.targetMasked,
        remember: challenge.remember,
      });
      setUsedEmailInstead(emailInstead || usedEmailInstead);
      setUsingRecovery(false);
      setOtpCode("");
      setOtpError(null);
      setCooldownLeft(OTP_COOLDOWN_S);
    } finally {
      setOtpVerifying(false);
    }
  };

  const score = scorePassword(form.password);
  const strengthColor = STRENGTH_COLORS[score];
  const strengthLabel = STRENGTH_LABELS[score];
  const showStrength = mode === "register" && otpStage === "none" && form.password.length > 0;
  const isDev = process.env.NODE_ENV !== "production";
  const inOtp = otpStage !== "none" || challenge !== null;

  return (
    <main className="flex min-h-[calc(100vh-104px)] overflow-hidden">
      <aside className="relative hidden lg:flex w-[46%] flex-col justify-between gap-10 overflow-hidden border-r border-white/10 p-10 xl:p-14">
        <div aria-hidden className="absolute inset-0 -z-10 overflow-hidden">
          <div className="ambience-blob blob-cyan" />
          <div className="ambience-blob blob-pink" />
          <div className="ambience-blob blob-purple" />
          <div className="grid-overlay" />
        </div>

        <div className="flex flex-col gap-2">
          <span className="font-display text-2xl font-bold tracking-wide">
            CLICK
            <span className="bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
              BOUND
            </span>
          </span>
          <span className="font-mono-tabular text-[10px] uppercase tracking-[0.35em] text-text-muted">
            Neon-grade gear · synthwave standard
          </span>
        </div>

        <div className="flex flex-col gap-6">
          <h1 className="font-display text-4xl xl:text-5xl font-bold leading-tight">
            Access to
            <br />
            the{" "}
            <span className="bg-gradient-to-r from-accent-cyan to-accent-pink bg-clip-text text-transparent">
              grid.
            </span>
          </h1>
          <p className="max-w-md text-sm text-text-muted">
            Track your cart, save picks to your wishlist, follow orders and never miss a flash
            deal.
          </p>
          {!inOtp && categories.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {categories.map((c) => (
                <span
                  key={c}
                  className="rounded-full border border-white/10 px-3 py-1 font-mono-tabular text-xs text-text-muted"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-6 font-mono-tabular text-[10px] uppercase tracking-[0.25em] text-text-muted">
          <span>
            <span className="text-accent-cyan">{productCount}</span> products
          </span>
          <span className="h-1 w-1 rounded-full bg-white/20" />
          <span>
            <span className="text-accent-pink">{categories.length}</span> categories
          </span>
        </div>
      </aside>

      <section className="flex flex-1 items-center justify-center p-6">
        <Reveal className="w-full max-w-md">
          <div className="glow-card glow-card--active rounded-2xl flex flex-col gap-5 p-6 sm:p-8">
            {inOtp ? (
              otpStage !== "none" ? (
                <div className="flex flex-col gap-5">
                  <div className="flex flex-col gap-1.5">
                    <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-cyan">
                      Step {otpStage === "email" ? "1 of 2" : "2 of 2"}
                    </span>
                    <h1 className="font-display text-xl font-bold">
                      {otpStage === "email" ? "Verify your email" : "Verify your phone"}
                    </h1>
                    <p className="text-sm text-text-muted">
                      We sent a 6-digit code to{" "}
                      <span className="text-text">{otpTarget?.target}</span>.
                    </p>
                  </div>

                  <CodeInput
                    value={otpCode}
                    onChange={setOtpCode}
                    onComplete={() => verifyCurrentStep()}
                    disabled={otpVerifying}
                    invalid={!!otpError}
                  />
                  {otpError && <p className="text-[11px] text-rose-400">{otpError}</p>}

                  <button
                    type="button"
                    onClick={() => verifyCurrentStep()}
                    disabled={otpVerifying || otpCode.length !== 6}
                    className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
                  >
                    {otpVerifying ? "Checking..." : "Verify code"}
                  </button>

                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={backToForm}
                      className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
                    >
                      Edit details
                    </button>
                    <button
                      type="button"
                      onClick={resendCurrent}
                      disabled={cooldownLeft > 0 || otpVerifying}
                      className="text-xs text-accent-cyan underline underline-offset-2 hover:text-text disabled:opacity-40"
                    >
                      {cooldownLeft > 0 ? `Resend in ${cooldownLeft}s` : "Resend code"}
                    </button>
                  </div>

                  {devCodes.length > 0 ? (
                    isDev && (
                      <div className="flex flex-col gap-1 rounded-lg border border-dashed border-white/15 bg-black/20 p-3 font-mono-tabular text-[11px] text-text-muted">
                        <span className="uppercase tracking-[0.2em] text-[9px]">Dev codes</span>
                        {devCodes.map((c) => (
                          <span key={c.id}>
                            {c.channel} → {c.target}:{" "}
                            <span className="text-accent-cyan">{c.code}</span>
                          </span>
                        ))}
                      </div>
                    )
                  ) : (
                    <p className="text-xs text-text-muted">
                      Check your inbox — the code arrives within a few minutes. Don&apos;t forget
                      the spam folder.
                    </p>
                  )}
                </div>
              ) : challenge?.channel === "TOTP" ? (
                <div className="flex flex-col gap-5">
                  <div className="flex flex-col gap-1.5">
                    <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-pink">
                      2-step check
                    </span>
                    <h1 className="font-display text-xl font-bold">Authenticator code</h1>
                    <p className="text-sm text-text-muted">
                      Open your authenticator app and enter the 6-digit code it shows for
                      Clickbound.
                    </p>
                  </div>

                  {usingRecovery ? (
                    <input
                      type="text"
                      inputMode="text"
                      placeholder="XXXX-XXXX"
                      maxLength={9}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.toUpperCase())}
                      className={`input-field rounded-lg px-3 py-2.5 text-center font-mono-tabular tracking-[0.2em] focus:outline-none focus:ring-2 ${
                        otpError ? "border-rose-500/60 focus:ring-rose-500/40" : "focus:ring-accent-cyan/60"
                      }`}
                    />
                  ) : (
                    <CodeInput
                      value={otpCode}
                      onChange={setOtpCode}
                      onComplete={() => loginWithCode()}
                      disabled={otpVerifying}
                      invalid={!!otpError}
                    />
                  )}
                  {otpError && <p className="text-[11px] text-rose-400">{otpError}</p>}

                  <button
                    type="button"
                    onClick={() => {
                      setUsingRecovery((u) => !u);
                      setOtpCode("");
                      setOtpError(null);
                    }}
                    className="self-start text-xs text-text-muted underline underline-offset-2 hover:text-text"
                  >
                    {usingRecovery ? "Use the authenticator app instead" : "Use a recovery code instead"}
                  </button>

                  <button
                    type="button"
                    onClick={() => loginWithCode()}
                    disabled={
                      otpVerifying || (usingRecovery ? otpCode.trim().length !== 9 : otpCode.length !== 6)
                    }
                    className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
                  >
                    {otpVerifying ? "Checking..." : "Verify & log in"}
                  </button>

                  <button
                    type="button"
                    onClick={backToForm}
                    className="self-start text-xs text-text-muted underline underline-offset-2 hover:text-text"
                  >
                    Back to log in
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-5">
                  <div className="flex flex-col gap-1.5">
                    <span className="font-mono-tabular text-[10px] uppercase tracking-[0.3em] text-accent-pink">
                      2-step check
                    </span>
                    <h1 className="font-display text-xl font-bold">Enter the code</h1>
                    <p className="text-sm text-text-muted">
                      We sent a 6-digit code to{" "}
                      <span className="text-text">{challenge?.targetMasked}</span>.
                      {challenge?.channel === "PHONE" && !usedEmailInstead && (
                        <button
                          type="button"
                          onClick={() => resendLogin(true)}
                          className="ml-1.5 text-accent-cyan underline underline-offset-2 hover:text-text"
                        >
                          Use email instead
                        </button>
                      )}
                    </p>
                  </div>

                  <CodeInput
                    value={otpCode}
                    onChange={setOtpCode}
                    onComplete={() => loginWithCode()}
                    disabled={otpVerifying}
                    invalid={!!otpError}
                  />
                  {otpError && <p className="text-[11px] text-rose-400">{otpError}</p>}

                  <label className="flex items-center gap-2 text-xs text-text-muted">
                    <input
                      type="checkbox"
                      checked={challenge?.remember ?? false}
                      onChange={(e) =>
                        setChallenge((c) => (c ? { ...c, remember: e.target.checked } : c))
                      }
                      className="h-3.5 w-3.5 accent-[var(--accent-cyan)]"
                    />
                    Remember this device for 30 days
                  </label>

                  <button
                    type="button"
                    onClick={() => loginWithCode()}
                    disabled={otpVerifying || otpCode.length !== 6}
                    className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
                  >
                    {otpVerifying ? "Checking..." : "Verify & log in"}
                  </button>

                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={backToForm}
                      className="text-xs text-text-muted underline underline-offset-2 hover:text-text"
                    >
                      Back to log in
                    </button>
                    <button
                      type="button"
                      onClick={() => resendLogin(false)}
                      disabled={cooldownLeft > 0 || otpVerifying}
                      className="text-xs text-accent-cyan underline underline-offset-2 hover:text-text disabled:opacity-40"
                    >
                      {cooldownLeft > 0 ? `Resend in ${cooldownLeft}s` : "Resend code"}
                    </button>
                  </div>

                  {devCodes.length > 0 ? (
                    isDev && (
                      <div className="flex flex-col gap-1 rounded-lg border border-dashed border-white/15 bg-black/20 p-3 font-mono-tabular text-[11px] text-text-muted">
                        <span className="text-[9px] uppercase tracking-[0.2em]">Dev codes</span>
                        {devCodes.map((c) => (
                          <span key={c.id}>
                            {c.channel} → {c.target}:{" "}
                            <span className="text-accent-cyan">{c.code}</span>
                          </span>
                        ))}
                      </div>
                    )
                  ) : (
                    <p className="text-xs text-text-muted">
                      Check your inbox — the code arrives within a few minutes. Don&apos;t forget
                      the spam folder.
                    </p>
                  )}
                </div>
              )
            ) : (
              <>
                <div className="grid grid-cols-2 gap-1 rounded-lg bg-white/5 p-1">
                  {(["login", "register"] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => switchMode(m)}
                      aria-pressed={mode === m}
                      className={`rounded-md px-2 py-1.5 font-mono-tabular text-xs font-medium uppercase tracking-widest transition-colors ${
                        mode === m
                          ? "bg-gradient-to-r from-accent-purple to-accent-pink text-white"
                          : "text-text-muted hover:text-text"
                      }`}
                    >
                      {m === "login" ? "Log in" : "Sign up"}
                    </button>
                  ))}
                </div>

                <div className="flex flex-col gap-1.5">
                  <h1 className="font-display text-2xl font-bold">
                    {mode === "login" ? "Welcome back." : "Create your account."}
                  </h1>
                  <p className="text-sm text-text-muted">
                    {mode === "login"
                      ? "Log in to reach your grid session."
                      : "Join the grid — it only takes a minute."}
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
                  {mode === "register" && (
                    <label className="flex flex-col gap-1.5">
                      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                        Name
                      </span>
                      <input
                        type="text"
                        placeholder="Your name"
                        className={`input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                          errors.name
                            ? "border-rose-500/60 focus:ring-rose-500/40"
                            : "focus:ring-accent-cyan/60"
                        }`}
                        value={form.name}
                        onChange={(e) => setField("name", e.target.value)}
                        onBlur={() => onBlur("name")}
                      />
                      {touched.name && errors.name && (
                        <span className="text-[11px] text-rose-400">{errors.name}</span>
                      )}
                    </label>
                  )}

                  <label className="flex flex-col gap-1.5">
                    <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                      Email
                    </span>
                    <input
                      type="email"
                      placeholder="you@grid.com"
                      className={`input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                        errors.email
                          ? "border-rose-500/60 focus:ring-rose-500/40"
                          : "focus:ring-accent-cyan/60"
                      }`}
                      value={form.email}
                      onChange={(e) => setField("email", e.target.value)}
                      onBlur={() => onBlur("email")}
                    />
                    {touched.email && errors.email && (
                      <span className="text-[11px] text-rose-400">{errors.email}</span>
                    )}
                  </label>

                  {mode === "register" && (
                    <label className="flex flex-col gap-1.5">
                      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                        Phone
                      </span>
                      <input
                        type="tel"
                        placeholder="+1 555 000 0000"
                        className={`input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 ${
                          errors.phone
                            ? "border-rose-500/60 focus:ring-rose-500/40"
                            : "focus:ring-accent-cyan/60"
                        }`}
                        value={form.phone}
                        onChange={(e) => setField("phone", e.target.value)}
                        onBlur={() => onBlur("phone")}
                      />
                      {touched.phone && errors.phone && (
                        <span className="text-[11px] text-rose-400">{errors.phone}</span>
                      )}
                    </label>
                  )}

                  <label className="flex flex-col gap-1.5">
                    <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                      Password
                    </span>
                    <div className="relative">
                      <input
                        type={showPass ? "text" : "password"}
                        placeholder={mode === "login" ? "Your password" : "At least 8 characters"}
                        className={`input-field w-full rounded-lg px-3 py-2 pr-10 focus:outline-none focus:ring-2 ${
                          errors.password
                            ? "border-rose-500/60 focus:ring-rose-500/40"
                            : "focus:ring-accent-cyan/60"
                        }`}
                        value={form.password}
                        onChange={(e) => setField("password", e.target.value)}
                        onBlur={() => onBlur("password")}
                      />
                      <button
                        type="button"
                        aria-label={showPass ? "Hide password" : "Show password"}
                        onClick={() => setShowPass((v) => !v)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-text-muted transition-colors hover:text-text"
                      >
                        <EyeIcon open={showPass} />
                      </button>
                    </div>
                    {touched.password && errors.password && (
                      <span className="text-[11px] text-rose-400">{errors.password}</span>
                    )}

                    {mode === "login" && (
                      <Link
                        href="/forgot-password"
                        className="self-start text-xs text-accent-cyan underline underline-offset-2 hover:text-text"
                      >
                        Forgot your password?
                      </Link>
                    )}

                    {showStrength && (
                      <div className="flex flex-col gap-1">
                        <div className="flex gap-1" aria-hidden>
                          {[0, 1, 2, 3].map((i) => (
                            <span
                              key={i}
                              className={`h-1 flex-1 rounded-full transition-colors ${
                                i < score ? strengthColor : "bg-white/10"
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-[10px] uppercase tracking-[0.18em] text-text-muted">
                          {strengthLabel}
                        </span>
                      </div>
                    )}
                  </label>

                  {mode === "register" && (
                    <label className="flex flex-col gap-1.5">
                      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-text-muted">
                        Confirm password
                      </span>
                      <div className="relative">
                        <input
                          type={showPass ? "text" : "password"}
                          placeholder="Repeat your password"
                          className={`input-field w-full rounded-lg px-3 py-2 pr-10 focus:outline-none focus:ring-2 ${
                            errors.confirm
                              ? "border-rose-500/60 focus:ring-rose-500/40"
                              : "focus:ring-accent-cyan/60"
                          }`}
                          value={form.confirm}
                          onChange={(e) => setField("confirm", e.target.value)}
                          onBlur={() => onBlur("confirm")}
                        />
                        <button
                          type="button"
                          aria-label={showPass ? "Hide password" : "Show password"}
                          onClick={() => setShowPass((v) => !v)}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-text-muted transition-colors hover:text-text"
                        >
                          <EyeIcon open={showPass} />
                        </button>
                      </div>
                      {touched.confirm && errors.confirm && (
                        <span className="text-[11px] text-rose-400">{errors.confirm}</span>
                      )}
                    </label>
                  )}

                  {mode === "register" && (
                    <div className="flex flex-col gap-1.5">
                      <label
                        className={`flex items-start gap-2 text-xs cursor-pointer ${
                          errors.terms ? "text-rose-400" : "text-text-muted"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={form.terms}
                          onChange={(e) => setField("terms", e.target.checked)}
                          className="mt-0.5 h-3.5 w-3.5 accent-[var(--accent-cyan)]"
                        />
                        <span>
                          I agree to the{" "}
                          <Link href="/faq" className="underline underline-offset-2 hover:text-text">
                            Terms of Service
                          </Link>{" "}
                          and{" "}
                          <Link href="/faq" className="underline underline-offset-2 hover:text-text">
                            Privacy Policy
                          </Link>
                          .
                        </span>
                      </label>
                      {touched.terms && errors.terms && (
                        <span className="text-[11px] text-rose-400">{errors.terms}</span>
                      )}
                    </div>
                  )}

                  {errors.server && (
                    <div className="rounded-lg border border-rose-500/40 bg-rose-500/15 px-3 py-2 text-sm text-rose-200">
                      {errors.server}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary press-down rounded-lg px-3 py-2.5 disabled:opacity-50"
                  >
                    {loading
                      ? "Please wait..."
                      : mode === "login"
                        ? "Log in"
                        : "Create account"}
                  </button>
                </form>

                {mode === "register" && (
                  <p className="text-xs text-text-muted">
                    Already have an account?{" "}
                    <button
                      type="button"
                      onClick={() => switchMode("login")}
                      className="font-medium text-accent-cyan underline underline-offset-2 hover:text-text"
                    >
                      Log in
                    </button>
                  </p>
                )}
              </>
            )}
          </div>
        </Reveal>
      </section>
    </main>
  );
}
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToasts } from "@/lib/toast-context";

type FormErrors = Record<string, string>;

function extractErrors(error: unknown): FormErrors {
  if (typeof error === "string") return { form: error };
  if (error && typeof error === "object" && "fieldErrors" in error) {
    const e = error as { fieldErrors?: Record<string, string[]>; formErrors?: string[] };
    const out: FormErrors = {};
    for (const [key, messages] of Object.entries(e.fieldErrors ?? {})) {
      if (messages.length > 0) out[key] = messages[0];
    }
    if (e.formErrors?.length) out.form = e.formErrors[0];
    return out;
  }
  return { form: "Something went wrong" };
}

export default function AccountForm({
  user,
}: {
  user: {
    name: string;
    email: string;
    addressLine: string | null;
    city: string | null;
    zipCode: string | null;
    phone: string | null;
  };
}) {
  const router = useRouter();
  const { success } = useToasts();
  const [profile, setProfile] = useState({
    name: user.name,
    email: user.email,
    addressLine: user.addressLine ?? "",
    city: user.city ?? "",
    zipCode: user.zipCode ?? "",
    phone: user.phone ?? "",
  });
  const [profileErrors, setProfileErrors] = useState<FormErrors>({});
  const [profileSaving, setProfileSaving] = useState(false);

  const [emailProof, setEmailProof] = useState<{ email: string; proof: string } | null>(null);
  const [emailVerifyStage, setEmailVerifyStage] = useState<
    "idle" | "sending" | "input" | "verifying"
  >("idle");
  const [emailCode, setEmailCode] = useState("");
  const [emailVerifyError, setEmailVerifyError] = useState<string | null>(null);
  const [devCode, setDevCode] = useState<string | null>(null);

  const [passwords, setPasswords] = useState({ currentPassword: "", newPassword: "" });
  const [passwordErrors, setPasswordErrors] = useState<FormErrors>({});
  const [passwordSaving, setPasswordSaving] = useState(false);

  async function handleProfileSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    setProfileErrors({});

    const newEmail = profile.email.trim().toLowerCase();
    const emailChanged = newEmail !== user.email.toLowerCase();

    if (emailChanged && (!emailProof || emailProof.email !== newEmail)) {
      setEmailVerifyError(null);
      setEmailVerifyStage("sending");
      const res = await fetch("/api/otp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "EMAIL", target: profile.email.trim(), forSignup: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setEmailVerifyStage("idle");
        setProfileErrors({ form: data.error ?? "Could not send the code" });
        return;
      }
      setDevCode(data.debugCode ?? null);
      setEmailCode("");
      setEmailVerifyStage("input");
      return;
    }

    setProfileSaving(true);

    const body: Record<string, unknown> = {
      name: profile.name.trim(),
      addressLine: profile.addressLine.trim() || null,
      city: profile.city.trim() || null,
      zipCode: profile.zipCode.trim() || null,
      phone: profile.phone.trim() || null,
    };
    if (emailChanged && emailProof && emailProof.email === newEmail) {
      body.email = newEmail;
      body.emailProof = emailProof.proof;
    }

    const res = await fetch("/api/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    setProfileSaving(false);

    if (!res.ok) {
      const data = await res.json();
      setProfileErrors(extractErrors(data.error));
      return;
    }

    if (body.email) setEmailProof(null);
    success("Profile saved");
    router.refresh();
  }

  async function confirmEmailCode() {
    if (emailCode.trim().length !== 6) {
      setEmailVerifyError("Enter the 6-digit code");
      return;
    }
    setEmailVerifyStage("verifying");
    setEmailVerifyError(null);
    try {
      const res = await fetch("/api/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "EMAIL", target: profile.email.trim(), code: emailCode.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setEmailVerifyStage("input");
        setEmailVerifyError(
          data.attemptsLeft
            ? `${data.error} ${data.attemptsLeft} attempt${data.attemptsLeft === 1 ? "" : "s"} left.`
            : (data.error ?? "Incorrect code"),
        );
        return;
      }
      setEmailProof({ email: profile.email.trim().toLowerCase(), proof: data.proof });
      setEmailVerifyStage("idle");
      setEmailCode("");
      setEmailVerifyError(null);
      await handleProfileSubmit();
    } finally {
      setEmailVerifyStage((s) => (s === "verifying" ? "idle" : s));
    }
  }

  function cancelEmailVerify() {
    setEmailVerifyStage("idle");
    setEmailCode("");
    setEmailVerifyError(null);
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPasswordErrors({});
    setPasswordSaving(true);

    const res = await fetch("/api/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPassword: passwords.currentPassword,
        newPassword: passwords.newPassword,
      }),
    });

    setPasswordSaving(false);

    if (!res.ok) {
      const data = await res.json();
      setPasswordErrors(extractErrors(data.error));
      return;
    }

    setPasswords({ currentPassword: "", newPassword: "" });
    success("Password updated");
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        onSubmit={handleProfileSubmit}
        className="glass-panel rounded-xl p-6 flex flex-col gap-4"
      >
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          PROFILE
        </h2>

        <div className="flex flex-col gap-2">
          <label htmlFor="name" className="text-sm font-medium text-text-muted">
            Name
          </label>
          <input
            id="name"
            type="text"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={profile.name}
            onChange={(e) => setProfile({ ...profile, name: e.target.value })}
            required
          />
          {profileErrors.name && <p className="text-xs text-danger">{profileErrors.name}</p>}
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="email" className="text-sm font-medium text-text-muted">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })}
            required
          />
          {profileErrors.email && <p className="text-xs text-danger">{profileErrors.email}</p>}
          {emailVerifyStage !== "idle" && (
            <div className="flex flex-col gap-2 rounded-lg border border-accent-cyan/30 bg-accent-cyan/5 p-3">
              <p className="text-xs text-text-muted">
                We sent a 6-digit code to{" "}
                <span className="font-medium text-text">{profile.email.trim()}</span>. Enter it
                here to verify the new email before saving.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  className="input-field w-32 rounded-lg px-3 py-2 text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
                  value={emailCode}
                  onChange={(e) => setEmailCode(e.target.value.replace(/\D/g, ""))}
                />
                <button
                  type="button"
                  disabled={emailVerifyStage === "sending" || emailVerifyStage === "verifying"}
                  onClick={confirmEmailCode}
                  className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50"
                >
                  {emailVerifyStage === "verifying" ? "Verifying..." : "Verify"}
                </button>
                <button
                  type="button"
                  disabled={emailVerifyStage === "sending" || emailVerifyStage === "verifying"}
                  onClick={cancelEmailVerify}
                  className="btn-ghost rounded-lg px-3 py-2 text-sm disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
              {emailVerifyStage === "sending" && (
                <p className="text-xs text-text-muted">Sending code...</p>
              )}
              {process.env.NODE_ENV !== "production" && devCode && (
                <p className="rounded-lg border border-dashed border-white/15 bg-black/20 p-2 font-mono-tabular text-[11px] text-text-muted">
                  dev code: EMAIL → {profile.email.trim()}:{" "}
                  <span className="text-accent-cyan">{devCode}</span>
                </p>
              )}
              {emailVerifyError && <p className="text-xs text-danger">{emailVerifyError}</p>}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="phone" className="text-sm font-medium text-text-muted">
            Phone
          </label>
          <input
            id="phone"
            type="tel"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={profile.phone}
            onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
          />
          {profileErrors.phone && <p className="text-xs text-danger">{profileErrors.phone}</p>}
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="addressLine" className="text-sm font-medium text-text-muted">
            Address line
          </label>
          <input
            id="addressLine"
            type="text"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={profile.addressLine}
            onChange={(e) => setProfile({ ...profile, addressLine: e.target.value })}
          />
          {profileErrors.addressLine && (
            <p className="text-xs text-danger">{profileErrors.addressLine}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="city" className="text-sm font-medium text-text-muted">
              City
            </label>
            <input
              id="city"
              type="text"
              className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={profile.city}
              onChange={(e) => setProfile({ ...profile, city: e.target.value })}
            />
            {profileErrors.city && <p className="text-xs text-danger">{profileErrors.city}</p>}
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="zipCode" className="text-sm font-medium text-text-muted">
              ZIP
            </label>
            <input
              id="zipCode"
              type="text"
              className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={profile.zipCode}
              onChange={(e) => setProfile({ ...profile, zipCode: e.target.value })}
            />
            {profileErrors.zipCode && <p className="text-xs text-danger">{profileErrors.zipCode}</p>}
          </div>
        </div>

        {profileErrors.form && <p className="text-sm text-danger">{profileErrors.form}</p>}

        <button
          type="submit"
          disabled={profileSaving}
          className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50"
        >
          {profileSaving ? "Saving..." : "Save profile"}
        </button>
      </form>

      <form
        onSubmit={handlePasswordSubmit}
        className="glass-panel rounded-xl p-6 flex flex-col gap-4"
      >
        <h2 className="font-display font-semibold tracking-widest text-sm text-text-muted">
          CHANGE PASSWORD
        </h2>

        <div className="flex flex-col gap-2">
          <label htmlFor="currentPassword" className="text-sm font-medium text-text-muted">
            Current password
          </label>
          <input
            id="currentPassword"
            type="password"
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={passwords.currentPassword}
            onChange={(e) => setPasswords({ ...passwords, currentPassword: e.target.value })}
            required
          />
          {passwordErrors.currentPassword && (
            <p className="text-xs text-danger">{passwordErrors.currentPassword}</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label htmlFor="newPassword" className="text-sm font-medium text-text-muted">
            New password
          </label>
          <input
            id="newPassword"
            type="password"
            minLength={8}
            className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
            value={passwords.newPassword}
            onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })}
            required
          />
          {passwordErrors.newPassword && (
            <p className="text-xs text-danger">{passwordErrors.newPassword}</p>
          )}
        </div>

        {passwordErrors.form && <p className="text-sm text-danger">{passwordErrors.form}</p>}

        <button
          type="submit"
          disabled={passwordSaving}
          className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50"
        >
          {passwordSaving ? "Updating..." : "Update password"}
        </button>
      </form>
    </div>
  );
}

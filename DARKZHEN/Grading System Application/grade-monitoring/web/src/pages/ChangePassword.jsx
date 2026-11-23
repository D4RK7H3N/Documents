import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/client";
import { Btn, ErrorBanner, Field, inputClass } from "../components/ui";

export default function ChangePassword() {
  const navigate = useNavigate();
  const [currentPassword, setCurrent] = useState("");
  const [newPassword, setNew] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirm) {
      setError({ message: "The two new passwords do not match." });
      return;
    }
    setBusy(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      authApi.clearSession();
      navigate("/login", {
        replace: true,
        state: { notice: "Password changed. Please sign in with your new password." },
      });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-background grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-primary-container text-on-primary p-space-2xl">
        <div className="flex items-center gap-space-md">
          <img src="/logo.svg" alt="" className="w-12 h-12 rounded-xl bg-surface-container-lowest/10 p-1" />
          <div className="leading-tight">
            <p className="font-headline-sm text-headline-sm">Grade Monitoring</p>
            <p className="font-label-md text-label-md opacity-80">Sagay National High School</p>
          </div>
        </div>
        <div>
          <h2 className="font-headline-xl text-headline-xl tracking-tight">
            Keep your account<br />yours alone.
          </h2>
          <p className="mt-space-md font-body-lg text-body-lg opacity-80 max-w-md">
            Passwords are salted and hashed — nobody, including administrators, can read them. Choose
            something strong: at least 8 characters, not similar to your username.
          </p>
        </div>
        <p className="font-label-sm text-label-sm opacity-60">Security first</p>
      </div>

      <div className="flex items-center justify-center p-space-lg">
        <div className="w-full max-w-md">
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)] p-space-lg sm:p-space-2xl">
            <div className="lg:hidden flex items-center gap-space-md mb-space-lg">
              <img src="/logo.svg" alt="" className="w-10 h-10" />
              <p className="font-headline-sm text-headline-sm text-on-surface">Grade Monitoring</p>
            </div>
            <h1 className="font-headline-md text-headline-md text-on-surface">Set a new password</h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-lg">
              Required before you can use the system.
            </p>
            <form onSubmit={onSubmit} className="flex flex-col gap-space-md">
              <Field label="Current password">
                <input
                  className={inputClass}
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrent(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </Field>
              <Field
                label="New password"
                hint="At least 8 characters, not similar to your username, not a common password."
              >
                <input
                  className={inputClass}
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNew(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </Field>
              <Field label="Confirm new password">
                <input
                  className={inputClass}
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </Field>
              {error && <ErrorBanner error={error} />}
              <Btn type="submit" icon="lock_reset" className="justify-center py-space-sm" disabled={busy}>
                {busy ? "Saving…" : "Save new password"}
              </Btn>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

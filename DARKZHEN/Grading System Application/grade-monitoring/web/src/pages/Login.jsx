import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Btn, ErrorBanner, Field, inputClass } from "../components/ui";

export default function Login() {
  const { login, config } = useAuth();
  const navigate = useNavigate();
  const notice = useLocation().state?.notice;
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await login(username.trim(), password);
      if (data.me?.must_change_password) {
        navigate("/change-password", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
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
          <img src={config?.logo_url || "/logo.svg"} alt="" className="w-12 h-12 rounded-xl bg-surface-container-lowest/10 p-1" />
          <div className="leading-tight">
            <p className="font-headline-sm text-headline-sm">Grade Monitoring</p>
            <p className="font-label-md text-label-md opacity-80">{config?.school_name}</p>
          </div>
        </div>
        <div>
          <h2 className="font-headline-xl text-headline-xl tracking-tight">
            Every grade,<br />one source of truth.
          </h2>
          <p className="mt-space-md font-body-lg text-body-lg opacity-80 max-w-md">
            Score entry, automatic computation per DepEd Order No. 8, s. 2015, and a full audit
            trail — computed once on the server, identical on every device.
          </p>
        </div>
        <p className="font-label-sm text-label-sm opacity-60">Faculty and administrator portal</p>
      </div>

      <div className="flex items-center justify-center p-space-lg">
        <div className="w-full max-w-md">
          <div className="bg-surface-container-lowest border border-outline-variant/70 rounded-xl shadow-[0_1px_2px_rgba(23,35,45,0.04)] p-space-lg sm:p-space-2xl">
            <div className="lg:hidden flex items-center gap-space-md mb-space-lg">
              <img src={config?.logo_url || "/logo.svg"} alt="" className="w-10 h-10" />
              <div className="leading-tight">
                <p className="font-headline-sm text-headline-sm text-on-surface">Grade Monitoring</p>
                <p className="font-label-sm text-label-sm text-on-surface-variant">{config?.school_name}</p>
              </div>
            </div>
            <h1 className="font-headline-md text-headline-md text-on-surface">Sign in</h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant mb-space-lg">
              Use the account issued by your administrator.
            </p>
            {notice && (
              <div className="mb-space-md rounded-xl bg-tertiary-container/15 border border-tertiary-container/30 text-[#005336] px-space-md py-space-sm text-body-sm">
                {notice}
              </div>
            )}
            <form onSubmit={onSubmit} className="flex flex-col gap-space-md">
              <Field label="Username">
                <input
                  className={inputClass}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </Field>
              <Field label="Password">
                <input
                  className={inputClass}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </Field>
              {error && <ErrorBanner error={error} />}
              <Btn type="submit" icon="login" className="justify-center py-space-sm" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </Btn>
            </form>
          </div>
          <p className="text-center font-label-sm text-label-sm text-on-surface-variant/70 mt-space-md">
            Students view their grades in the mobile app
          </p>
        </div>
      </div>
    </div>
  );
}

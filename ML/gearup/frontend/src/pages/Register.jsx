import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (key) => (event) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const fields = [
    ["username", "Username", "text", true],
    ["email", "Email", "email", true],
    ["first_name", "First name", "text", false],
    ["last_name", "Last name", "text", false],
    ["password", "Password (min 8 characters)", "password", true],
  ];

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold">Create your account</h1>

      <form onSubmit={submit} className="mt-6 space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
        {fields.map(([key, label, type, required]) => (
          <div key={key}>
            <label className="mb-1 block text-sm text-slate-300" htmlFor={key}>
              {label}
            </label>
            <input
              id={key}
              type={type}
              value={form[key]}
              onChange={update(key)}
              required={required}
              autoComplete={type === "password" ? "new-password" : "on"}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            />
          </div>
        ))}
        {error && (
          <p className="rounded-lg border border-rose-900 bg-rose-950/60 px-3 py-2 text-sm text-rose-300">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-emerald-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-40"
        >
          {busy ? "Creating account…" : "Register"}
        </button>
        <p className="text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link to="/login" className="text-emerald-400 hover:underline">
            Log in
          </Link>
        </p>
      </form>
    </div>
  );
}

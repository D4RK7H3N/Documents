import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const client = useQueryClient();
  const navigate = useNavigate();

  const login = useMutation({
    mutationFn: async () => {
      await api.auth.csrf();
      const me = await api.auth.login(username, password);
      await api.auth.csrf();
      return me;
    },
    onSuccess: (me) => {
      client.setQueryData(["me"], me);
      navigate("/", { replace: true });
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate();
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-5 rounded-xl border border-zinc-200 p-6 shadow-lg dark:border-zinc-800">
        <div>
          <h1 className="text-xl font-semibold">BugFixer</h1>
          <p className="mt-1 text-sm text-zinc-500">Staff sign in</p>
        </div>
        <div>
          <label htmlFor="username" className="block text-sm font-medium">Username</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
            className="mt-1 w-full rounded-lg border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
          />
        </div>
        {login.isError && (
          <p role="alert" className="rounded-lg border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {login.error.message}
          </p>
        )}
        <button
          type="submit"
          disabled={login.isPending}
          className="w-full rounded-lg bg-purple-600 px-4 py-2 font-medium text-white hover:bg-purple-500 disabled:opacity-60"
        >
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

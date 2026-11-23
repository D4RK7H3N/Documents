import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState({
    school_name: "Sagay National High School",
    short_name: "SNHS",
    logo_url: null,
    default_school_year: "",
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/school-config/")
      .then((r) => r.json())
      .then(setConfig)
      .catch(() => {});
  }, []);

  const refreshConfig = useCallback(async () => {
    try {
      setConfig(await (await fetch("/api/v1/school-config/")).json());
    } catch {}
  }, []);

  const refreshUser = useCallback(async () => {
    if (!authApi.hasSession()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (username, password) => {
    const data = await authApi.login(username, password);
    const me = await authApi.me().catch(() => null);
    setUser(me);
    return { ...data, me };
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, config, loading, login, logout, refreshUser, refreshConfig }),
    [user, config, loading, login, logout, refreshUser, refreshConfig]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

import { createContext, useContext, useEffect, useState } from "react";
import { api, clearTokens, getToken, setTokens } from "../api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      if (getToken()) {
        try {
          setUser(await api("/auth/me/"));
        } catch {
          clearTokens();
        }
      }
      setReady(true);
    })();
  }, []);

  const login = async (identifier, password) => {
    const data = await api("/auth/token/", {
      method: "POST",
      body: { username: identifier, password },
      auth: false,
    });
    setTokens(data);
    const me = await api("/auth/me/");
    setUser(me);
    return me;
  };

  const register = async (payload) => {
    const data = await api("/auth/register/", {
      method: "POST",
      body: payload,
      auth: false,
    });
    setTokens(data);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

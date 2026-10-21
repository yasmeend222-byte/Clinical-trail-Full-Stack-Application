import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("cs-logout", onLogout);
    if (getToken()) {
      api("/api/auth/me")
        .then(setUser)
        .catch(() => setToken(null))
        .finally(() => setReady(true));
    } else setReady(true);
    return () => window.removeEventListener("cs-logout", onLogout);
  }, []);

  const login = async (email, password) => {
    const res = await api("/api/auth/login", { method: "POST", body: { email, password } });
    setToken(res.token);
    setUser(res.researcher);
  };
  const register = async (data) => {
    const res = await api("/api/auth/register", { method: "POST", body: data });
    setToken(res.token);
    setUser(res.researcher);
  };
  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, ready, login, register, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

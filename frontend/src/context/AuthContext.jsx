import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(!!tokenStore.get());

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // restore the session after a page reload
  useEffect(() => {
    if (!tokenStore.get()) return;
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setChecking(false));
  }, []);

  // the API client fires this event when the server answers 401 (expired token)
  useEffect(() => {
    window.addEventListener("asiet-unauthorized", logout);
    return () => window.removeEventListener("asiet-unauthorized", logout);
  }, [logout]);

  const login = async (email, password) => {
    const result = await api.login(email, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
    return result.user;
  };

  return <AuthContext.Provider value={{ user, checking, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

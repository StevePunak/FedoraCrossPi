import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuthStatus } from "../api/client";

interface AuthContextValue {
  status: AuthStatus | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const s = await api.getAuthStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try { await api.logout(); } catch { /* ignore */ }
    await refresh();
  };

  useEffect(() => {
    refresh();
    const onUnauthorized = () => refresh();
    window.addEventListener("auth:unauthorized", onUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", onUnauthorized);
  }, []);

  return (
    <AuthContext.Provider value={{ status, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid #dfe6e9",
  borderRadius: 4,
  fontSize: 15,
  fontFamily: "inherit",
};

const btnStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 20px",
  background: "#0984e3",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  fontSize: 15,
  cursor: "pointer",
  marginTop: 8,
};

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { refresh } = useAuth();
  const [searchParams] = useSearchParams();
  // Same-origin path only — reject anything that doesn't start with a single
  // "/", including protocol-relative "//host/" forms that browsers treat as
  // absolute and would let a crafted link open-redirect post-login.
  const nextParam = searchParams.get("next");
  const redirectTo =
    nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")
      ? nextParam
      : "/";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login(username, password);
      await refresh();
      // Hard navigation, not React Router. `redirectTo` can point at
      // /apps/<id>/... which lives outside this SPA bundle; a client-side
      // route push would fall through to the catch-all and never make the
      // real HTTP request that re-presents the new session cookie.
      window.location.href = redirectTo;
    } catch (err) {
      setError(err instanceof Error ? err.message : "login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
      <form
        onSubmit={submit}
        style={{
          background: "#fff",
          padding: 32,
          borderRadius: 8,
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          width: 360,
        }}
      >
        <h1 style={{ fontSize: 22, marginBottom: 24 }}>Gateway Admin</h1>
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4, color: "#636e72" }}>
            Username
          </label>
          <input
            style={inputStyle}
            name="username"
            id="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4, color: "#636e72" }}>
            Password
          </label>
          <input
            style={inputStyle}
            name="password"
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && (
          <div style={{ color: "#d63031", fontSize: 14, marginBottom: 12 }}>{error}</div>
        )}
        <button type="submit" style={btnStyle} disabled={busy}>
          {busy ? "Signing in…" : "Sign In"}
        </button>
      </form>
    </div>
  );
}

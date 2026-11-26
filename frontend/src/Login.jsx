import { useState } from "react";
import { api, setToken } from "./api";

export default function Login({ onLogin }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(e.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");
    try {
      const t = await api("/auth/login", { method: "POST", body: { username, password } });
      setToken(t.access_token);
      onLogin(await api("/auth/me"));
    } catch (err) {
      setError(err.status === 401 ? "Invalid username or password." : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="login-logo" aria-hidden="true">OA</span>
          <span className="login-name">Ops Agent</span>
        </div>
        <h1>Sign in</h1>
        <p className="login-sub">Approval-gated infrastructure requests</p>

        <form onSubmit={submit}>
          <label htmlFor="username">Username</label>
          <input id="username" name="username" autoComplete="username" required />
          <label htmlFor="password">Password</label>
          <input id="password" name="password" type="password" autoComplete="current-password" required />
          <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <p role="alert" className="error">{error}</p>
        </form>

        <p className="login-hint">Demo accounts: alice, bob, carol, admin (password: <code>username-pass</code>)</p>
      </div>
    </main>
  );
}
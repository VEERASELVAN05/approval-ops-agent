
import { useState } from "react";
import { api, setToken } from "./api";

export default function Login({ onLogin }) {
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");

    const form = new FormData(e.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username,
          password,
        }),
      });

      if (!response.ok) {
        throw {
          status: response.status,
          message: response.status === 401
            ? "Invalid username or password."
            : "Login failed. Please try again.",
        };
      }

      const t = await response.json();

      setToken(t.access_token);

      const user = await api("/auth/me");
      onLogin(user);

    } catch (err) {
      setError(err.message || "Something went wrong.");
    }
  }

  return (
    <main>
      <h1>Sign in</h1>

      <form onSubmit={submit}>
        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />

        <button type="submit">Sign in</button>

        <p role="alert" className="error">{error}</p>
      </form>
    </main>
  );
}

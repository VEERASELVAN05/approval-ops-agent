import { useEffect, useState } from "react";
import { api, setToken } from "./api";
import Login from "./Login";
import Chat from "./Chat";
import Approvals from "./Approvals";
import Dashboard from "./Dashboard";
import "./App.css";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("chat");

  useEffect(() => {
    api("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading…</p>;
  if (!user) return <Login onLogin={setUser} />;

  const reviewer = user.role === "approver" || user.role === "admin";
  const tabs = [["chat", "Assistant"], ...(reviewer ? [["approvals", "Approvals"], ["dashboard", "Dashboard"]] : [])];

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header>
        <strong>Ops Agent</strong>
        <nav aria-label="Main">
          {tabs.map(([key, label]) => (
            <button key={key} onClick={() => setView(key)} aria-current={view === key ? "page" : undefined}>
              {label}
            </button>
          ))}
        </nav>
        <span>{user.username} ({user.role})</span>
        <button onClick={() => { setToken(null); setUser(null); }}>Sign out</button>
      </header>
      <main id="main" tabIndex={-1}>
        {view === "chat" && <Chat />}
        {view === "approvals" && reviewer && <Approvals />}
        {view === "dashboard" && reviewer && <Dashboard user={user} />}
      </main>
    </>
  );
}
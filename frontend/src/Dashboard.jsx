import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export default function Dashboard({ user }) {
  const [m, setM] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setM(await api("/metrics"));
      if (user.role === "admin") setAudit(await api("/audit?limit=30"));
    } catch (e) { setError(e.message); }
  }, [user.role]);
  useEffect(() => { load(); }, [load]);

  if (error) return <p role="alert" className="error">{error}</p>;
  if (!m) return <p>Loading…</p>;
  const stat = (label, value) => <div className="stat"><dt>{label}</dt><dd>{value ?? "n/a"}</dd></div>;

  return (
    <>
      <h1>Dashboard</h1>
      <button onClick={load}>Refresh</button>
      <dl className="stats">
        {stat("Requests", m.requests_total)}
        {stat("Pending actions", m.actions.pending)}
        {stat("Approved / rejected", `${m.actions.approved} / ${m.actions.rejected}`)}
        {stat("Approval rate", m.approval_rate != null ? `${Math.round(m.approval_rate * 100)}%` : null)}
        {stat("Tool calls", m.tool_calls_total)}
        {stat("Tool errors", m.tool_errors_total)}
        {stat("Agent runs (failed)", `${m.agent_runs_total} (${m.agent_runs_failed})`)}
        {stat("Latency avg / p95", m.latency_ms_avg != null ? `${m.latency_ms_avg} / ${m.latency_ms_p95} ms` : null)}
      </dl>

      {user.role === "admin" && (
        <>
          <h2>Audit trail (latest 30)</h2>
          <div className="scroll">
            <table>
              <caption className="sr-only">Recent audit events</caption>
              <thead><tr><th scope="col">Time</th><th scope="col">Actor</th><th scope="col">Event</th><th scope="col">Entity</th><th scope="col">Trace</th></tr></thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id}>
                    <td>{a.ts.slice(0, 19)}</td><td>{a.actor} ({a.actor_type})</td><td>{a.event}</td>
                    <td>{a.entity ? `${a.entity} #${a.entity_id}` : ""}</td><td><code>{a.trace_id?.slice(0, 8)}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
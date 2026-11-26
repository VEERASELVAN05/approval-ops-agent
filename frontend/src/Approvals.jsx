import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export default function Approvals() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState([]);
  const [notes, setNotes] = useState({});
  const [msg, setMsg] = useState("");

  const load = useCallback(() => api(`/approvals?status=${status}`).then(setItems).catch((e) => setMsg(e.message)), [status]);
  useEffect(() => { load(); }, [load]);

  async function decide(id, decision) {
    try {
      const r = await api(`/approvals/${id}/decision`, { method: "POST", body: { decision, note: notes[id] || null } });
      setMsg(`Action #${id} is now ${r.status}${r.result?.error ? `: ${r.result.error}` : ""}.`);
      load();
    } catch (e) {
      setMsg(e.message);
    }
  }

  return (
    <>
      <h1>Approvals</h1>
      <label htmlFor="filter">Show</label>
      <select id="filter" value={status} onChange={(e) => setStatus(e.target.value)}>
        {["pending", "executed", "rejected", "failed", "all"].map((s) => <option key={s}>{s}</option>)}
      </select>
      <p role="status" aria-live="polite">{msg}</p>

      {items.length === 0 && <p>Nothing here.</p>}
      {items.map((a) => (
        <article key={a.id} className="card" aria-labelledby={`t${a.id}`}>
          <h2 id={`t${a.id}`}>#{a.id}: {a.tool} proposed by {a.proposed_by}</h2>
          <dl>
            <dt>Arguments</dt><dd><code>{JSON.stringify(a.args)}</code></dd>
            <dt>Verified details (from database)</dt>
            <dd><code>{JSON.stringify(a.context)}</code></dd>
            <dt>Capacity right now</dt><dd>{a.capacity_now.available} of {a.capacity_now.total} VMs free</dd>
            <dt>Agent's stated reasoning (unverified, written by the model)</dt><dd>{a.agent_reasoning}</dd>
            {a.status !== "pending" && <><dt>Status</dt><dd>{a.status}</dd></>}
          </dl>
          {a.status === "pending" && (
            <>
              <label htmlFor={`n${a.id}`}>Note (optional)</label>
              <input id={`n${a.id}`} maxLength={500} value={notes[a.id] || ""} onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })} />
              <div className="row">
                <button onClick={() => decide(a.id, "approve")}>Approve #{a.id}</button>
                <button className="danger" onClick={() => decide(a.id, "reject")}>Reject #{a.id}</button>
              </div>
            </>
          )}
        </article>
      ))}
    </>
  );
}
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export default function Chat() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mine, setMine] = useState([]);

  const loadMine = useCallback(() => api("/actions/mine").then(setMine).catch(() => {}), []);
  useEffect(() => { loadMine(); }, [loadMine]);

  async function send(e) {
    e.preventDefault();
    setBusy(true); setError(""); setReply("");
    try {
      const r = await api("/agent/chat", { method: "POST", body: { message } });
      setReply(r.reply);
      setMessage("");
      loadMine();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Request infrastructure</h1>
      <form onSubmit={send}>
        <label htmlFor="msg">What do you need?</label>
        <textarea id="msg" rows={3} maxLength={2000} value={message} onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g. I need a test environment with 4 VMs for two weeks" required />
        <button type="submit" disabled={busy}>{busy ? "Thinking…" : "Send"}</button>
      </form>
      <div aria-live="polite">
        {reply && <section aria-label="Assistant reply" className="card"><p>{reply}</p></section>}
      </div>
      <p role="alert" className="error">{error}</p>

      <h2>My proposed actions</h2>
      <table>
        <caption className="sr-only">Actions the assistant proposed for you</caption>
        <thead><tr><th scope="col">ID</th><th scope="col">Action</th><th scope="col">Details</th><th scope="col">Status</th></tr></thead>
        <tbody>
          {mine.map((a) => (
            <tr key={a.id}>
              <td>{a.id}</td><td>{a.tool}</td>
              <td>{a.context.vm_count} VMs{a.context.duration_days ? `, ${a.context.duration_days} days` : ""}</td>
              <td>{a.status}{a.result?.error ? ` (${a.result.error})` : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
import { Send } from "lucide-react";
import { useEffect, useState } from "react";
import { api, Escalation } from "../api";

export function Tutor() {
  const [items, setItems] = useState<Escalation[]>([]);
  const [active, setActive] = useState<Escalation | null>(null);
  const [hint, setHint] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    void load();
    const handle = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(handle);
  }, []);

  async function load() {
    const result = await api.escalations();
    setItems(result.escalations);
    setActive((current) => current ?? result.escalations[0] ?? null);
  }

  async function reply() {
    if (!active || !hint.trim()) return;
    await api.replyEscalation(active.id, hint);
    setHint("");
    setMessage("Hint sent. The session is back in TEACH mode.");
    setActive(null);
    await load();
  }

  return (
    <main className="workspace">
      <section className="status-band">
        <div>
          <h1>Human Tutor</h1>
          <p>Open escalations from stuck sessions.</p>
        </div>
      </section>
      <section className="tutor-grid">
        <section className="panel">
          <div className="panel-title">
            <h2>Queue</h2>
            <span>{items.length}</span>
          </div>
          <div className="queue">
            {items.map((item) => (
              <button key={item.id} className={active?.id === item.id ? "selected" : ""} onClick={() => setActive(item)}>
                <b>{item.stuck_concept.replaceAll("_", " ")}</b>
                <span>{item.summary}</span>
              </button>
            ))}
            {!items.length && <p className="muted">No open escalations.</p>}
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Escalation</h2>
          </div>
          {active ? (
            <div className="escalation-detail">
              <p>{active.summary}</p>
              <h3>Teacher excerpts</h3>
              {active.excerpts.map((excerpt, index) => (
                <blockquote key={index}>{excerpt}</blockquote>
              ))}
              <h3>Failed marks</h3>
              <p>{active.failed_mark_points.join(", ") || "Incorrect-note escalation"}</p>
              <textarea value={hint} onChange={(event) => setHint(event.target.value)} placeholder="Type a concise tutor hint..." />
              <button className="send-button" onClick={reply} disabled={!hint.trim()}>
                <Send size={20} />
                Send hint
              </button>
            </div>
          ) : (
            <p className="muted">{message || "Select an escalation."}</p>
          )}
        </section>
      </section>
    </main>
  );
}


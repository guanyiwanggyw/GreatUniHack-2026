import { Save, Upload } from "lucide-react";
import { useState } from "react";
import { api, Question } from "../api";

export function Ingest() {
  const [paper, setPaper] = useState<File | null>(null);
  const [scheme, setScheme] = useState<File | null>(null);
  const [drafts, setDrafts] = useState<Question[]>([]);
  const [message, setMessage] = useState("");

  async function ingest() {
    if (!paper || !scheme) return;
    const result = await api.ingest(paper, scheme);
    setDrafts(result.draft_questions);
    setMessage(`${result.draft_questions.length} draft questions extracted.`);
  }

  async function save() {
    await api.saveQuestions("alevel-cs-algorithms", drafts);
    setMessage("Saved reviewed questions to the pack.");
  }

  function update(index: number, field: keyof Question, value: string) {
    setDrafts((items) => items.map((item, i) => (i === index ? { ...item, [field]: field === "marks" ? Number(value) : value } : item)));
  }

  return (
    <main className="workspace">
      <section className="status-band">
        <div>
          <h1>Paper Ingest</h1>
          <p>Upload files, review the draft, then save to the subject pack.</p>
        </div>
      </section>
      <section className="panel">
        <div className="upload-row">
          <label>
            Paper
            <input type="file" accept=".pdf,.txt" onChange={(event) => setPaper(event.target.files?.[0] ?? null)} />
          </label>
          <label>
            Mark scheme
            <input type="file" accept=".pdf,.txt" onChange={(event) => setScheme(event.target.files?.[0] ?? null)} />
          </label>
          <button className="send-button" onClick={ingest} disabled={!paper || !scheme}>
            <Upload size={20} />
            Ingest
          </button>
        </div>
        {message && <p className="notice">{message}</p>}
      </section>
      <section className="panel">
        <div className="panel-title">
          <h2>Review Draft</h2>
          <button className="icon-button" onClick={save} disabled={!drafts.length} title="Save reviewed questions">
            <Save size={20} />
          </button>
        </div>
        <div className="draft-table">
          {drafts.map((question, index) => (
            <article className="draft-row" key={question.id}>
              <input value={question.id} onChange={(event) => update(index, "id", event.target.value)} />
              <textarea value={question.text} onChange={(event) => update(index, "text", event.target.value)} />
              <input type="number" value={question.marks} onChange={(event) => update(index, "marks", event.target.value)} />
              <pre>{JSON.stringify(question.mark_points, null, 2)}</pre>
            </article>
          ))}
          {!drafts.length && <p className="muted">No draft questions yet.</p>}
        </div>
      </section>
    </main>
  );
}


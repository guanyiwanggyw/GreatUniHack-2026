import { FileText, Loader2, Plus, Save, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { api, IngestResult, MarkPoint, PastPaper, Question } from "../api";

const PACK_ID = "gcse-maths";

export function Ingest() {
  const [paper, setPaper] = useState<File | null>(null);
  const [scheme, setScheme] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [drafts, setDrafts] = useState<Question[]>([]);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [papers, setPapers] = useState<PastPaper[]>([]);
  const [busy, setBusy] = useState<"" | "reading" | "saving">("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void loadPapers();
  }, []);

  async function loadPapers() {
    try {
      setPapers((await api.papers(PACK_ID)).papers);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load papers.");
    }
  }

  async function ingest() {
    if (!paper || !scheme) return;
    setBusy("reading");
    setError("");
    setMessage("");
    try {
      const output = await api.ingest(paper, scheme, PACK_ID);
      setResult(output);
      setDrafts(output.draft_questions);
      setTitle((current) => current || output.title);
      setMessage(`Found ${output.draft_questions.length} questions worth ${output.total_marks} marks. Check them below, then save.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the PDFs.");
    } finally {
      setBusy("");
    }
  }

  async function save() {
    if (!drafts.length) return;
    setBusy("saving");
    setError("");
    try {
      const saved = await api.savePaper(PACK_ID, title, drafts, [paper?.name ?? "", scheme?.name ?? ""].filter(Boolean));
      setMessage(`Saved "${saved.paper.title}". Go back to the whiteboard and press Sit paper to test Chud on it.`);
      setDrafts([]);
      setResult(null);
      setTitle("");
      setPaper(null);
      setScheme(null);
      await loadPapers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the paper.");
    } finally {
      setBusy("");
    }
  }

  async function remove(item: PastPaper) {
    if (!window.confirm(`Delete "${item.title}"? Chud's past results on it stay in the session.`)) return;
    await api.deletePaper(PACK_ID, item.id);
    await loadPapers();
  }

  function updateQuestion(index: number, patch: Partial<Question>) {
    setDrafts((items) => items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  function updatePoint(qIndex: number, pIndex: number, patch: Partial<MarkPoint>) {
    setDrafts((items) =>
      items.map((item, i) => {
        if (i !== qIndex) return item;
        const mark_points = item.mark_points.map((point, j) => (j === pIndex ? { ...point, ...patch } : point));
        return { ...item, mark_points, marks: mark_points.reduce((sum, point) => sum + (point.marks ?? 1), 0) };
      })
    );
  }

  function addPoint(qIndex: number) {
    const question = drafts[qIndex];
    updateQuestion(qIndex, {
      mark_points: [
        ...question.mark_points,
        { id: `${question.id}-m${question.mark_points.length + 1}`, code: "M1", marks: 1, text: "", answer: "", concept: question.concepts[0] ?? "general" },
      ],
      marks: question.marks + 1,
    });
  }

  function removePoint(qIndex: number, pIndex: number) {
    const question = drafts[qIndex];
    const mark_points = question.mark_points.filter((_, j) => j !== pIndex);
    updateQuestion(qIndex, { mark_points, marks: mark_points.reduce((sum, point) => sum + (point.marks ?? 1), 0) });
  }

  const totalMarks = drafts.reduce((sum, question) => sum + question.marks, 0);

  return (
    <main className="workspace">
      <section className="status-band">
        <div>
          <h1>Past papers</h1>
          <p>Upload a GCSE Maths past paper and its mark scheme. Chud sits the paper, and the Marker marks it against the scheme.</p>
        </div>
      </section>

      <section className="panel">
        <div className="upload-grid">
          <label className="file-drop">
            <FileText size={22} />
            <span>{paper ? paper.name : "Past paper PDF"}</span>
            <input type="file" accept=".pdf,.txt" onChange={(event) => setPaper(event.target.files?.[0] ?? null)} />
          </label>
          <label className="file-drop">
            <FileText size={22} />
            <span>{scheme ? scheme.name : "Mark scheme PDF"}</span>
            <input type="file" accept=".pdf,.txt" onChange={(event) => setScheme(event.target.files?.[0] ?? null)} />
          </label>
          <button className="send-button" onClick={ingest} disabled={!paper || !scheme || busy !== ""}>
            {busy === "reading" ? <Loader2 className="spin" size={20} /> : <Upload size={20} />}
            {busy === "reading" ? "Reading..." : "Read paper"}
          </button>
        </div>
        {message && <p className="notice">{message}</p>}
        {error && <p className="error">{error}</p>}
        {result && (
          <p className="muted small">
            Read by the {result.extractor === "llm" ? "AI extractor" : "offline parser (add an LLM key for better extraction)"}.
          </p>
        )}
        {result?.warnings.map((warning) => (
          <p className="warning" key={warning}>
            {warning}
          </p>
        ))}
      </section>

      {drafts.length > 0 && (
        <section className="panel">
          <div className="panel-title">
            <input className="paper-title-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Paper title" aria-label="Paper title" />
            <span className="marks-total">{totalMarks} marks</span>
            <button className="send-button" onClick={save} disabled={busy !== "" || !title.trim()}>
              <Save size={20} />
              Save paper
            </button>
          </div>
          <div className="draft-list">
            {drafts.map((question, qIndex) => (
              <article className="draft-card" key={question.id}>
                <header>
                  <b>Question {qIndex + 1}</b>
                  <span className="concept-chip">{question.concepts.map((c) => c.replaceAll("_", " ")).join(", ")}</span>
                  <span className="marks-total">{question.marks} marks</span>
                  <button className="icon-button" title="Remove question" onClick={() => setDrafts((items) => items.filter((_, i) => i !== qIndex))}>
                    <Trash2 size={18} />
                  </button>
                </header>
                <textarea value={question.text} onChange={(event) => updateQuestion(qIndex, { text: event.target.value })} aria-label={`Question ${qIndex + 1} text`} />
                <table className="scheme-table">
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Marks</th>
                      <th>Mark scheme</th>
                      <th>Expected answer</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {question.mark_points.map((point, pIndex) => (
                      <tr key={point.id}>
                        <td>
                          <input value={point.code ?? ""} onChange={(event) => updatePoint(qIndex, pIndex, { code: event.target.value })} aria-label="Mark code" />
                        </td>
                        <td>
                          <input type="number" min={1} value={point.marks ?? 1} onChange={(event) => updatePoint(qIndex, pIndex, { marks: Math.max(1, Number(event.target.value)) })} aria-label="Marks" />
                        </td>
                        <td>
                          <input value={point.text} onChange={(event) => updatePoint(qIndex, pIndex, { text: event.target.value })} aria-label="Mark scheme wording" />
                        </td>
                        <td>
                          <input value={point.answer ?? ""} onChange={(event) => updatePoint(qIndex, pIndex, { answer: event.target.value })} placeholder="method mark" aria-label="Expected answer" />
                        </td>
                        <td>
                          <button className="icon-button" title="Remove mark" onClick={() => removePoint(qIndex, pIndex)}>
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button className="text-button" onClick={() => addPoint(qIndex)}>
                  <Plus size={16} />
                  Add mark
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="panel">
        <div className="panel-title">
          <h2>Saved papers</h2>
          <span>{papers.length}</span>
        </div>
        <div className="paper-list">
          {papers.map((item) => (
            <article className="paper-row" key={item.id}>
              <FileText size={20} />
              <div>
                <b>{item.title}</b>
                <span>
                  {item.questions.length} questions · {item.total_marks} marks
                </span>
              </div>
              <button className="icon-button" title="Delete paper" onClick={() => remove(item)}>
                <Trash2 size={18} />
              </button>
            </article>
          ))}
          {!papers.length && <p className="muted">No papers yet. Try the sample in content/packs/gcse-maths/sample-paper.</p>}
        </div>
        <a className="text-button" href="/">
          Back to the whiteboard
        </a>
      </section>
    </main>
  );
}

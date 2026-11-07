import { FileText, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { Attempt, PaperAttempt, PastPaper, Question } from "../../api";

export function ExamPanel({
  questions,
  papers,
  attempt,
  paperAttempt,
  review,
  sitting,
  onTest,
  onSitPaper,
  onReteach,
}: {
  questions: Question[];
  papers: PastPaper[];
  attempt: Attempt | null;
  paperAttempt: PaperAttempt | null;
  review: Record<string, unknown> | null;
  sitting: string;
  onTest: (questionId: string) => void;
  onSitPaper: (paperId: string) => void;
  onReteach: () => void;
}) {
  const [tab, setTab] = useState<"papers" | "practice">("papers");
  const [open, setOpen] = useState<string | null>(null);
  const gaps = (review?.gaps as Array<Record<string, unknown>> | undefined) ?? [];
  const diagnosis = (review?.diagnosis as string[] | undefined) ?? [];

  return (
    <section className="exam-panel" aria-label="Exam panel">
      <div className="exam-tabs" role="tablist">
        <button role="tab" aria-selected={tab === "papers"} className={tab === "papers" ? "active" : ""} onClick={() => setTab("papers")}>
          Past papers
        </button>
        <button role="tab" aria-selected={tab === "practice"} className={tab === "practice" ? "active" : ""} onClick={() => setTab("practice")}>
          Practice questions
        </button>
      </div>

      {tab === "papers" && (
        <>
          <div className="paper-picker">
            {papers.map((paper) => (
              <div className="paper-pick" key={paper.id}>
                <FileText size={18} />
                <span>
                  <b>{paper.title}</b>
                  <small>
                    {paper.questions.length} questions · {paper.total_marks} marks
                  </small>
                </span>
                <button className="primary-button" onClick={() => onSitPaper(paper.id)} disabled={Boolean(sitting)}>
                  {sitting === paper.id ? <Loader2 className="spin" size={16} /> : null}
                  {sitting === paper.id ? "Chud is sitting it..." : "Sit paper"}
                </button>
              </div>
            ))}
            {!papers.length && (
              <a className="upload-cta" href="/ingest">
                <Upload size={18} />
                Upload a past paper and mark scheme
              </a>
            )}
          </div>

          {paperAttempt && (
            <div className="paper-result">
              <div className="paper-score">
                <div className="score-ring big" style={{ ["--score" as string]: `${paperAttempt.percentage}%` }}>
                  {Math.round(paperAttempt.percentage)}%
                </div>
                <div>
                  <b>{paperAttempt.paper_title}</b>
                  <p>{paperAttempt.summary}</p>
                  <small className="muted">Marked by the {paperAttempt.marker === "llm" ? "AI Marker" : "offline Marker"} against the mark scheme.</small>
                </div>
              </div>
              <ol className="question-results">
                {paperAttempt.results.map((result, index) => (
                  <li key={result.question_id} className={result.score === result.max_score ? "full" : result.score ? "part" : "none"}>
                    <button className="result-row" onClick={() => setOpen(open === result.question_id ? null : result.question_id)} aria-expanded={open === result.question_id}>
                      <span>Q{index + 1}</span>
                      <span className="result-text">{result.question_text.replace(/^\d+\s*[.)]?\s*/, "").slice(0, 70)}</span>
                      <b>
                        {result.score}/{result.max_score}
                      </b>
                    </button>
                    {open === result.question_id && (
                      <div className="result-detail">
                        <p className="chud-answer">
                          <b>Chud wrote:</b> {result.answer}
                        </p>
                        {result.marks.map((mark) => (
                          <p key={mark.mark_point_id} className={mark.awarded ? "mark-ok" : "mark-miss"}>
                            <b>{mark.awarded ? "✓" : "✗"}</b> {mark.reason}
                          </p>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}

      {tab === "practice" && (
        <>
          <div className="question-picker">
            {questions.map((question, index) => (
              <button key={question.id} onClick={() => onTest(question.id)} title={question.text}>
                Q{index + 1}
              </button>
            ))}
          </div>
          {attempt && (
            <>
              <p className="practice-question">{questions.find((q) => q.id === attempt.question_id)?.text}</p>
              <div className="score-ring" style={{ ["--score" as string]: `${(attempt.score / Math.max(attempt.max_score, 1)) * 100}%` }}>
                {attempt.score}/{attempt.max_score}
              </div>
              <div className="marks">
                {attempt.marks.map((mark) => (
                  <p key={mark.mark_point_id} className={mark.awarded ? "mark-ok" : "mark-miss"}>
                    <b>{mark.awarded ? "✓" : "✗"}</b> {mark.reason}
                  </p>
                ))}
              </div>
            </>
          )}
          <div className="coach-feedback">
            {diagnosis.map((item) => (
              <span className="diagnosis" key={item}>
                {item.replaceAll("_", " ")}
              </span>
            ))}
            {gaps.map((gap, index) => (
              <p key={index}>{String(gap.detail ?? "")}</p>
            ))}
          </div>
        </>
      )}

      {(attempt || paperAttempt) && (
        <button className="primary-button" onClick={onReteach}>
          Teach again
        </button>
      )}
    </section>
  );
}

import { Attempt, Question } from "../../api";

export function ExamPanel({
  questions,
  attempt,
  review,
  onTest,
  onReteach,
}: {
  questions: Question[];
  attempt: Attempt | null;
  review: Record<string, unknown> | null;
  onTest: (questionId: string) => void;
  onReteach: () => void;
}) {
  const gaps = (review?.gaps as Array<Record<string, unknown>> | undefined) ?? [];
  const diagnosis = (review?.diagnosis as string[] | undefined) ?? [];
  return (
    <section className="exam-panel" aria-label="Exam panel">
      <h2>Test Chud</h2>
      <div className="question-picker">
        {questions.map((question) => (
          <button key={question.id} onClick={() => onTest(question.id)}>
            {question.id}
          </button>
        ))}
      </div>
      {attempt && (
        <>
          <div className="score-ring" style={{ ["--score" as string]: `${(attempt.score / Math.max(attempt.max_score, 1)) * 100}%` }}>
            {attempt.score}/{attempt.max_score}
          </div>
          <div className="marks">
            {attempt.marks.map((mark) => (
              <p key={mark.mark_point_id} className={mark.awarded ? "mark-ok" : "mark-miss"}>
                <b>{mark.awarded ? "ok" : "x"} {mark.mark_point_id}</b> {mark.reason}
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
        {attempt && (
          <button className="primary-button" onClick={onReteach}>
            Teach again
          </button>
        )}
      </div>
    </section>
  );
}

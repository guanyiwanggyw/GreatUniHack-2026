import { ArrowLeft, Repeat2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, Attempt, Profile, Question, Session } from "../api";
import { ModeBadge } from "../components/ModeBadge";

export function Results({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [review, setReview] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, [sessionId]);

  async function load() {
    try {
      const [state, profileData] = await Promise.all([api.getSession(sessionId), api.profiles()]);
      const questionData = await api.questions(state.session.pack_id);
      const reviewData = await api.review(sessionId);
      setSession(state.session);
      setProfiles(profileData.profiles);
      setQuestions(questionData.questions);
      setReview(reviewData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load results");
    }
  }

  const question = questions.find((item) => item.id === session?.current_question_id) ?? questions[0];
  const latestRound = Math.max(0, ...(session?.attempts ?? []).map((attempt) => attempt.round));
  const attempts = (session?.attempts ?? []).filter((attempt) => attempt.round === latestRound);
  const profileNames = new Map(profiles.map((profile) => [profile.id, profile.name]));
  const scoreHistory = useMemo(() => buildScoreHistory(session?.attempts ?? []), [session?.attempts]);

  async function reteach() {
    if (!session) return;
    await api.reteach(session.id);
    window.location.href = "/";
  }

  return (
    <main className="workspace">
      <section className="status-band">
        <div>
          <h1>Class Results</h1>
          <p>{question?.text ?? "No question selected"}</p>
        </div>
        <div className="status-actions">
          {session && <ModeBadge mode={session.mode} />}
          <a className="button-link" href="/">
            <ArrowLeft size={20} />
            Dashboard
          </a>
        </div>
      </section>
      {error && <p className="error">{error}</p>}
      <section className="results-grid">
        <section className="panel wide">
          <div className="panel-title">
            <h2>Heatmap</h2>
            <span>Round {latestRound}</span>
          </div>
          <div className="heatmap">
            <div className="heat-row heat-head">
              <span>Chud</span>
              {question?.mark_points.map((mark) => (
                <span key={mark.id} title={mark.text}>
                  {mark.id}
                </span>
              ))}
              <span>Score</span>
            </div>
            {attempts.map((attempt) => (
              <div className="heat-row" key={attempt.id}>
                <b>{profileNames.get(attempt.chud_id) ?? attempt.chud_id}</b>
                {question?.mark_points.map((mark) => {
                  const result = attempt.marks.find((item) => item.mark_point_id === mark.id);
                  return (
                    <span key={mark.id} className={result?.awarded ? "cell ok" : "cell miss"} title={result?.reason}>
                      {result?.awarded ? "✓" : "✕"}
                    </span>
                  );
                })}
                <b>
                  {attempt.score}/{attempt.max_score}
                </b>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Coach</h2>
          </div>
          <Feedback review={review} />
          <button className="send-button full" onClick={reteach}>
            <Repeat2 size={20} />
            Re-teach
          </button>
        </section>
        <section className="panel wide">
          <div className="panel-title">
            <h2>Score History</h2>
          </div>
          <div className="sparkline">
            {scoreHistory.map((point) => (
              <div key={point.round} style={{ height: `${Math.max(point.average * 100, 4)}%` }} title={`Round ${point.round}: ${Math.round(point.average * 100)}%`}>
                <span>{point.round}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="panel wide">
          <div className="panel-title">
            <h2>Written Answers</h2>
          </div>
          <div className="answers">
            {attempts.map((attempt) => (
              <article className="answer" key={attempt.id}>
                <h3>{profileNames.get(attempt.chud_id) ?? attempt.chud_id}</h3>
                <p>{attempt.answer}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function Feedback({ review }: { review: Record<string, unknown> | null }) {
  const gaps = (review?.gaps as Array<Record<string, unknown>> | undefined) ?? [];
  const suggestions = (review?.reteach_suggestions as string[] | undefined) ?? [];
  return (
    <div className="feedback">
      {gaps.map((gap, index) => (
        <p key={index}>{String(gap.detail ?? gap.concept)}</p>
      ))}
      {suggestions.map((item, index) => (
        <p key={`s-${index}`} className="suggestion">
          {item}
        </p>
      ))}
      {!gaps.length && <p className="muted">No gaps reported.</p>}
    </div>
  );
}

function buildScoreHistory(attempts: Attempt[]) {
  const byRound = new Map<number, Attempt[]>();
  attempts.forEach((attempt) => byRound.set(attempt.round, [...(byRound.get(attempt.round) ?? []), attempt]));
  return Array.from(byRound.entries()).map(([round, roundAttempts]) => ({
    round,
    average: roundAttempts.reduce((sum, attempt) => sum + attempt.score / attempt.max_score, 0) / roundAttempts.length,
  }));
}


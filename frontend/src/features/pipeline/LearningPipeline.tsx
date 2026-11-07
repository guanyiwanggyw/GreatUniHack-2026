import { BookOpenCheck, Brain, Ear, FileText, MessageCircle, NotebookPen, PenLine, RefreshCw, ScanSearch, ShieldCheck, Target } from "lucide-react";
import type { ReactNode } from "react";
import { Mode, PaperAttempt, TeachResponse } from "../../api";

type StepState = "done" | "warn" | "stop" | "idle";

const METHOD_LABEL: Record<string, string> = {
  DEFINITION: "Definition",
  ANALOGY: "Analogy",
  WORKED_EXAMPLE: "Worked example",
  DIAGRAM: "Diagram",
  STEP_BY_STEP: "Step by step",
};

const LOOP = ["Teach", "Remember", "Sit paper", "Marked", "Reteach"] as const;

function Step({ icon, title, state, children }: { icon: ReactNode; title: string; state: StepState; children?: ReactNode }) {
  return (
    <li className={`lp-step ${state}`}>
      <span className="lp-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="lp-body">
        <b>{title}</b>
        {children}
      </div>
    </li>
  );
}

function Phase({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="lp-phase">
      <h3>{label}</h3>
      <ol>{children}</ol>
    </section>
  );
}

const pct = (value = 0) => `${Math.round(value * 100)}%`;
const statusWord = (status: string) => status.toLowerCase();

export function LearningPipeline({
  teach,
  paper,
  lastEvent,
  mode,
  thinking,
  status,
}: {
  teach: TeachResponse | null;
  paper: PaperAttempt | null;
  lastEvent: "teach" | "paper" | null;
  mode: Mode;
  thinking: boolean;
  status: string;
}) {
  const loopIndex = lastEvent === "paper" ? (mode === "REVIEW" ? 3 : 4) : lastEvent === "teach" ? 1 : 0;

  return (
    <section className="pipeline-panel learning-pipeline" aria-label="How Chud is learning">
      <div className="lp-header">
        <h2>How Chud learned that</h2>
        {thinking && <span className="lp-live">thinking...</span>}
      </div>

      <ol className="lp-loop" aria-label="Learning loop">
        {LOOP.map((name, index) => (
          <li key={name} className={index < loopIndex ? "past" : index === loopIndex ? "current" : ""}>
            {name}
          </li>
        ))}
      </ol>

      {lastEvent === "paper" && paper ? <PaperSteps paper={paper} /> : teach ? <TeachSteps teach={teach} /> : <IdleSteps />}

      <p className="lp-status" aria-live="polite">
        {status}
      </p>
    </section>
  );
}

function IdleSteps() {
  return (
    <>
      <Phase label="Input">
        <Step icon={<Ear size={16} />} title="Hear your explanation" state="idle">
          <p>Talk or type. Chud only learns from what you commit.</p>
        </Step>
      </Phase>
      <Phase label="Process">
        <Step icon={<NotebookPen size={16} />} title="Take notes, check facts, remember" state="idle">
          <p>Each sentence becomes a note tagged with a GCSE topic. Wrong facts are flagged, and some notes fade from memory.</p>
        </Step>
      </Phase>
      <Phase label="Output">
        <Step icon={<MessageCircle size={16} />} title="Reply and update the brain" state="idle">
          <p>Chud asks about what he is missing, and his topic map updates.</p>
        </Step>
      </Phase>
    </>
  );
}

function TeachSteps({ teach }: { teach: TeachResponse }) {
  const learning = teach.learning ?? {};
  const heard = learning.heard;
  const notes = learning.notes ?? [];
  const stopped = learning.stopped;
  const blocked = learning.stopped_by === "block";
  const wrong = notes.filter((note) => note.status === "incorrect").length;
  const offTopic = notes.filter((note) => note.status === "unsupported").length;
  const stuck = notes.filter((note) => note.retained).length;
  const rememberedWrong = notes.filter((note) => note.retained && note.status === "incorrect").length;
  const before = learning.understanding_before ?? 0;
  const after = learning.understanding_after ?? before;
  const delta = Math.round((after - before) * 100);

  return (
    <>
      <Phase label="Input">
        <Step icon={<Ear size={16} />} title={heard ? `Heard ${heard.words} words (${heard.source === "voice" ? "spoken" : "typed"})` : "Heard you"} state="done">
          {heard && <q className="lp-quote">{heard.text.length > 140 ? `${heard.text.slice(0, 140)}...` : heard.text}</q>}
        </Step>
        <Step icon={<ShieldCheck size={16} />} title={stopped ? (blocked ? "Blocked by the safety check" : "Sent back to rephrase") : "Passed the safety check"} state={stopped ? (blocked ? "stop" : "warn") : "done"}>
          {stopped && <p>{stopped}</p>}
        </Step>
      </Phase>

      {stopped ? (
        <Phase label="Process">
          <Step icon={<NotebookPen size={16} />} title="Nothing learned this time" state="idle">
            <p>Chud only takes notes from your own explanations.</p>
          </Step>
        </Phase>
      ) : (
        <Phase label="Process">
          <Step icon={<NotebookPen size={16} />} title={`Took ${notes.length} note${notes.length === 1 ? "" : "s"}`} state={notes.length ? "done" : "warn"}>
            <ul className="lp-notes">
              {notes.map((note) => (
                <li key={note.id}>
                  <span className="lp-chip topic">{note.concept_name}</span>
                  <span className="lp-chip">{METHOD_LABEL[note.method] ?? note.method}</span>
                  <span className={`lp-chip ${note.has_reason ? "yes" : "no"}`}>{note.has_reason ? "has a why" : "no why"}</span>
                  <span className={`lp-chip ${note.has_example ? "yes" : "no"}`}>{note.has_example ? "has an example" : "no example"}</span>
                </li>
              ))}
            </ul>
          </Step>
          <Step
            icon={<ScanSearch size={16} />}
            title={wrong ? `Fact check: ${wrong} wrong` : offTopic ? `Fact check: ${offTopic} off-topic` : "Fact check: all correct"}
            state={wrong ? "stop" : offTopic ? "warn" : "done"}
          >
            {notes
              .filter((note) => note.status !== "correct")
              .map((note) => (
                <p key={note.id} className={note.status === "incorrect" ? "lp-bad" : "lp-meh"}>
                  {note.status === "incorrect" ? "✗" : "?"} "{note.text.length > 90 ? `${note.text.slice(0, 90)}...` : note.text}" — {note.check_reason}
                </p>
              ))}
          </Step>
          <Step
            icon={<Brain size={16} />}
            title={`Memory: ${stuck} of ${notes.length} stuck`}
            state={rememberedWrong ? "stop" : stuck === notes.length ? "done" : stuck ? "warn" : "stop"}
          >
            {notes.map((note) => (
              <div className="lp-memory" key={note.id}>
                <span className="lp-bar">
                  <i style={{ width: pct(note.retention) }} />
                </span>
                <span>
                  {note.retained ? "remembered" : "forgot"} · {pct(note.retention)}
                </span>
              </div>
            ))}
            {(learning.forgotten ?? []).map((note) => (
              <p key={note.id} className="lp-meh">
                Faded: "{note.text.slice(0, 60)}"
              </p>
            ))}
            {rememberedWrong > 0 && <p className="lp-bad">Chud now believes something wrong. Reteach it correctly before the paper.</p>}
            {notes.some((note) => !note.retained) && <p className="lp-tip">Tip: a reason plus a worked example makes notes stick.</p>}
          </Step>
        </Phase>
      )}

      <Phase label="Output">
        <Step icon={<MessageCircle size={16} />} title="Chud replied" state={teach.reply_text ? "done" : "idle"}>
          {teach.reply_text && <q className="lp-quote">{teach.reply_text}</q>}
          {teach.reply_reason && <p className="lp-why">Why: {teach.reply_reason}</p>}
        </Step>
        {!stopped && (
          <Step icon={<Target size={16} />} title={`Understanding ${pct(before)} → ${pct(after)}${delta ? ` (${delta > 0 ? "+" : ""}${delta})` : ""}`} state={delta > 0 ? "done" : "idle"}>
            <div className="lp-changes">
              {(learning.coverage_changes ?? []).map((change) => (
                <span key={change.concept} className={`lp-chip ${change.after === "SOLID" ? "yes" : change.after === "SHAKY" ? "meh" : "no"}`}>
                  {change.name}: {statusWord(change.before)} → {statusWord(change.after)}
                </span>
              ))}
              {!learning.coverage_changes?.length && <p>No topic changed status this turn.</p>}
            </div>
          </Step>
        )}
      </Phase>
    </>
  );
}

function PaperSteps({ paper }: { paper: PaperAttempt }) {
  const blank = paper.results.filter((result) => /don't know|do not really know|do not know/i.test(result.answer)).length;
  const full = paper.results.filter((result) => result.score === result.max_score).length;
  const teachNext = paper.summary.match(/Teach next: ([^.]+)/)?.[1];
  return (
    <>
      <Phase label="Input">
        <Step icon={<FileText size={16} />} title={paper.paper_title} state="done">
          <p>
            {paper.results.length} questions · {paper.max_score} marks
          </p>
        </Step>
      </Phase>
      <Phase label="Process">
        <Step icon={<PenLine size={16} />} title={`Chud answered ${paper.results.length - blank} of ${paper.results.length}`} state={blank ? "warn" : "done"}>
          <p>He used only his remembered notes. {blank ? `${blank} left as "I don't know".` : ""}</p>
        </Step>
        <Step icon={<BookOpenCheck size={16} />} title={`${paper.marker === "llm" ? "AI Marker" : "Offline Marker"} checked the mark scheme`} state="done">
          <p>
            {full} question{full === 1 ? "" : "s"} got full marks.
          </p>
        </Step>
      </Phase>
      <Phase label="Output">
        <Step icon={<Target size={16} />} title={`Score ${paper.score}/${paper.max_score} (${Math.round(paper.percentage)}%)`} state={paper.percentage >= 70 ? "done" : paper.percentage >= 40 ? "warn" : "stop"}>
          <p>{paper.summary}</p>
        </Step>
        {teachNext && (
          <Step icon={<RefreshCw size={16} />} title="Reteach next" state="warn">
            <p>{teachNext}</p>
          </Step>
        )}
      </Phase>
    </>
  );
}

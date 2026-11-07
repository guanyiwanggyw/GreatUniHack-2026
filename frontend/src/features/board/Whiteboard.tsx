import { LivePhrase } from "../listening/useLiveTranscription";
import { BoardSegment, StickyNote } from "./useBoardState";

export function Whiteboard({
  segments,
  phrases,
  stickies,
  onEditPhrase,
  answer,
}: {
  segments: BoardSegment[];
  phrases: LivePhrase[];
  stickies: StickyNote[];
  onEditPhrase: (seq: number, text: string) => void;
  answer: string;
}) {
  return (
    <section className="whiteboard" aria-label="Whiteboard">
      <div className="board-writing">
        {segments.map((segment) => (
          <div className="segment" key={segment.id}>
            <p>{segment.text}</p>
          </div>
        ))}
        {phrases.map((phrase) => (
          <textarea
            key={phrase.seq}
            className={`live-phrase ${phrase.pending ? "pending" : ""}`}
            value={phrase.text}
            onChange={(event) => onEditPhrase(phrase.seq, event.target.value)}
            aria-label="Editable live transcription phrase"
          />
        ))}
        {!segments.length && !phrases.length && <p className="board-empty">Start talking or type a segment. Chud will only learn from committed segments.</p>}
        {answer && (
          <article className="answer-card">
            <b>Chud's answer</b>
            <p>{answer}</p>
          </article>
        )}
      </div>
      <aside className="sticky-stack" aria-label="Chud's notes">
        {stickies.slice(-8).map(({ note, retained, retention }) => (
          <article className={`sticky ${retained ? "remembered" : "forgotten"}`} key={note.id} style={{ opacity: Math.max(retention, 0.28) }}>
            <span>{String(note.features.method ?? "DEFINITION").replaceAll("_", " ")}</span>
            <p>{note.text}</p>
          </article>
        ))}
      </aside>
    </section>
  );
}

import { BrainView } from "../../api";

export function BrainDrawer({ brain, open, onClose }: { brain: BrainView | null; open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <aside className="drawer" aria-label="Chud's brain">
      <div className="drawer-head">
        <h2>Chud's Brain</h2>
        <button className="icon-button" onClick={onClose} aria-label="Close brain drawer">
          x
        </button>
      </div>
      <div className="coverage">
        {brain?.coverage.map((item) => (
          <span className={`coverage-chip ${item.status.toLowerCase()}`} key={item.concept_id}>
            {item.name}: {item.status}
          </span>
        ))}
      </div>
      <div className="brain-notes">
        {brain?.notes.map(({ note, retained, retention, reason }) => (
          <article className="brain-note" key={note.id}>
            <div>
              <b>{retained ? "Remembered" : "Forgotten"}</b>
              {brain.show_correctness && <span className={`chip ${note.status}`}>{note.status}</span>}
            </div>
            <p>{note.text}</p>
            <div className="retention-meter">
              <i style={{ width: `${Math.round(retention * 100)}%` }} />
            </div>
            <small>{reason}</small>
          </article>
        ))}
      </div>
    </aside>
  );
}

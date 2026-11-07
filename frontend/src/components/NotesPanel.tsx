import type { Knowledge, Note, Profile } from "../api";

export function NotesPanel({ notes, knowledge, profiles }: { notes: Note[]; knowledge: Record<string, Knowledge>; profiles: Profile[] }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <h2>Notes</h2>
        <span>{notes.length}</span>
      </div>
      <div className="notes-list">
        {notes.map((note) => {
          const retained = profiles.filter((profile) => knowledge[profile.id]?.retained_note_ids.includes(note.id)).map((profile) => profile.name);
          return (
            <article className="note" key={note.id}>
              <div>
                <span className={`chip ${note.status}`}>{statusLabel(note.status)}</span>
                {note.concept && <span className="concept">{note.concept.replaceAll("_", " ")}</span>}
              </div>
              <p>{note.text}</p>
              <small>Retained by {retained.length ? retained.join(", ") : "no one yet"}</small>
            </article>
          );
        })}
        {notes.length === 0 && <p className="muted">Teach a turn to generate notes.</p>}
      </div>
    </section>
  );
}

function statusLabel(status: Note["status"]) {
  if (status === "correct") return "✓ correct";
  if (status === "incorrect") return "✕ incorrect";
  if (status === "unsupported") return "? unsupported";
  return "pending";
}


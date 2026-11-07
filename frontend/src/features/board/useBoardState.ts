import { Note, Session } from "../../api";

export type BoardSegment = {
  id: string;
  text: string;
};

export type StickyNote = {
  note: Note;
  retained: boolean;
  retention: number;
};

export function useBoardState(session: Session | null) {
  const segments: BoardSegment[] = (session?.transcript ?? [])
    .filter((line) => line.role === "teacher")
    .map((line, index) => ({ id: `${index}`, text: String(line.text ?? "") }));
  const remembered = new Set(session?.knowledge.retained_note_ids ?? []);
  const stickies: StickyNote[] = (session?.notes ?? []).map((note) => ({
    note,
    retained: remembered.has(note.id),
    retention: session?.knowledge.retention_scores[note.id] ?? 0,
  }));
  return { segments, stickies };
}

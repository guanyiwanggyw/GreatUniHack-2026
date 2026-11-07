export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type Mode = "TEACH" | "TEST" | "REVIEW" | "RETEACH" | "ESCALATED" | "FINISHED";
export type Emotion = "NEUTRAL" | "CURIOUS" | "CONFUSED" | "HAPPY" | "THINKING";
export type NoteStatus = "correct" | "incorrect" | "unsupported" | "pending";
export type TeachingMethod = "DEFINITION" | "ANALOGY" | "WORKED_EXAMPLE" | "DIAGRAM" | "STEP_BY_STEP";

export type MarkPoint = { id: string; text: string; concept: string };
export type Question = {
  id: string;
  text: string;
  marks: number;
  type: "recall" | "application" | "edge_case";
  concepts: string[];
  mark_points: MarkPoint[];
};
export type Pack = {
  id: string;
  subject: string;
  topic: string;
  exam_board_credit: string;
  reference_summary: string;
  prototype_content_notice: string;
};
export type ChudProfile = {
  id: string;
  name: string;
  voice_id: string;
  avatar: string;
  method_weights: Record<TeachingMethod, number>;
  attention_span: number;
  question_style: string;
  persona: string;
  base_rate: number;
};
export type Note = {
  id: string;
  text: string;
  turn: number;
  concept: string | null;
  status: NoteStatus;
  source: "teacher" | "tutor";
  features: Record<string, boolean | number | string>;
};
export type Knowledge = {
  chud_id: string;
  retained_note_ids: string[];
  retention_by_concept: Record<string, number>;
  retention_scores: Record<string, number>;
  explanations: Record<string, string>;
};
export type MarkResult = { mark_point_id: string; awarded: boolean; reason: string };
export type Attempt = {
  id: string;
  question_id: string;
  chud_id: string;
  answer: string;
  marks: MarkResult[];
  score: number;
  max_score: number;
  round: number;
};
export type Session = {
  id: string;
  pack_id: string;
  mode: Mode;
  chud_id: string;
  current_question_id: string | null;
  turn: number;
  notes: Note[];
  knowledge: Knowledge;
  transcript: Array<Record<string, unknown>>;
  attempts: Attempt[];
  feedback: Array<Record<string, unknown>>;
  metrics: Record<string, unknown>;
  transitions: Array<Record<string, unknown>>;
  escalation_id: string | null;
};
export type PipelineStage = {
  name: string;
  status: "ran" | "skipped" | "blocked" | "redirected";
  latency_ms: number;
  detail: string;
};
export type TeachResponse = {
  transcript: string;
  pipeline: PipelineStage[];
  notes_added: Note[];
  reply_text: string;
  reply_audio_url: string;
  emotion: Emotion;
  knowledge: Knowledge;
  metrics: Record<string, unknown>;
  mode: Mode;
};
export type BrainView = {
  chud: ChudProfile;
  notes: Array<{ note: Note; retained: boolean; retention: number; reason: string }>;
  coverage: Array<{ concept_id: string; name: string; status: "UNTAUGHT" | "SHAKY" | "SOLID" }>;
  understanding: number;
  last_score: { score: number; max: number } | null;
  show_correctness: boolean;
};
export type Escalation = {
  id: string;
  session_id: string;
  status: "open" | "resolved";
  stuck_concept: string;
  summary: string;
  excerpts: string[];
  failed_mark_points: string[];
  tutor_reply: string | null;
};
export type SttResponse = { text: string; words: Array<Record<string, unknown>>; duration_ms: number };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

export const api = {
  health: () => request<{ ok: boolean; mock_mode: boolean }>("/api/health"),
  packs: () => request<{ packs: Pack[] }>("/api/packs"),
  questions: (packId: string) => request<{ questions: Question[] }>(`/api/packs/${packId}/questions`),
  chud: () => request<{ chud: ChudProfile }>("/api/chud"),
  createSession: (pack_id: string) =>
    request<{ session: Session; intro_line: { text: string; audio_url: string; emotion: Emotion } }>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ pack_id }),
    }),
  getSession: (id: string) => request<{ session: Session }>(`/api/sessions/${id}`),
  stt: (blob: Blob, mime = "audio/webm") => {
    const form = new FormData();
    form.append("audio", blob, "phrase.webm");
    form.append("mime", mime);
    return request<SttResponse>("/api/stt", { method: "POST", body: form });
  },
  teachSegment: (id: string, text: string, source: "VOICE" | "TYPED", words: Array<Record<string, unknown>> = []) =>
    request<TeachResponse>(`/api/sessions/${id}/teach`, {
      method: "POST",
      body: JSON.stringify({ text, source, words }),
    }),
  testChud: (id: string, question_id?: string) =>
    request<{ question: Question; attempt: Attempt; class_summary: Record<string, unknown> }>(`/api/sessions/${id}/test`, {
      method: "POST",
      body: JSON.stringify({ question_id }),
    }),
  review: (id: string) => request<Record<string, unknown>>(`/api/sessions/${id}/review`),
  reteach: (id: string) => request<{ mode: Mode; prompt: string }>(`/api/sessions/${id}/reteach`, { method: "POST" }),
  recap: (id: string) => request<{ reply_text: string; reply_audio_url: string; emotion: Emotion }>(`/api/sessions/${id}/chud/recap`, { method: "POST" }),
  brain: (id: string) => request<BrainView>(`/api/sessions/${id}/brain`),
  ingest: (paper: File, markScheme: File, packId = "alevel-cs-algorithms") => {
    const form = new FormData();
    form.append("paper", paper);
    form.append("mark_scheme", markScheme);
    form.append("pack_id", packId);
    return request<{ draft_questions: Question[] }>("/api/ingest", { method: "POST", body: form });
  },
  saveQuestions: (packId: string, questions: Question[]) =>
    request<{ ok: boolean; count: number }>(`/api/packs/${packId}/questions`, {
      method: "POST",
      body: JSON.stringify({ questions }),
    }),
  escalations: () => request<{ escalations: Escalation[] }>("/api/escalations"),
  replyEscalation: (id: string, hint: string) =>
    request<{ ok: boolean; session: Session }>(`/api/escalations/${id}/reply`, {
      method: "POST",
      body: JSON.stringify({ hint }),
    }),
  audioUrl: (path: string) => (path.startsWith("http") ? path : `${API_BASE}${path}`),
};

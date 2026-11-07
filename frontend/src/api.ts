export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type Mode = "TEACH" | "TEST" | "REVIEW" | "RETEACH" | "ESCALATED" | "FINISHED";

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
  sample_content_notice: string;
};
export type Profile = {
  id: string;
  name: string;
  avatar: string;
  description: string;
  questioning_style: string;
};
export type Note = {
  id: string;
  text: string;
  turn: number;
  concept: string | null;
  status: "correct" | "incorrect" | "unsupported" | "pending";
  source: "teacher" | "tutor";
  features: Record<string, boolean | number>;
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
  chud_ids: string[];
  current_question_id: string | null;
  turn: number;
  notes: Note[];
  knowledge: Record<string, Knowledge>;
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
  replies: Array<{ chud_id: string; text: string; audio_url: string }>;
  knowledge: Record<string, Knowledge>;
  metrics: Record<string, unknown>;
  mode: Mode;
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
  profiles: () => request<{ profiles: Profile[] }>("/api/profiles"),
  createSession: (pack_id: string, chud_ids?: string[]) =>
    request<{ session: Session; intro_lines: Array<{ chud_id: string; text: string; audio_url: string }> }>("/api/session", {
      method: "POST",
      body: JSON.stringify({ pack_id, chud_ids }),
    }),
  getSession: (id: string) => request<{ session: Session }>(`/api/session/${id}`),
  teachText: (id: string, text: string) =>
    request<TeachResponse>(`/api/session/${id}/teach`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  teachAudio: (id: string, blob: Blob) => {
    const form = new FormData();
    form.append("audio", blob, "teacher.webm");
    return request<TeachResponse>(`/api/session/${id}/teach`, { method: "POST", body: form });
  },
  testClass: (id: string, question_id?: string) =>
    request<{ question: Question; attempts: Attempt[]; class_summary: Record<string, unknown> }>(`/api/session/${id}/test`, {
      method: "POST",
      body: JSON.stringify({ question_id }),
    }),
  review: (id: string) => request<Record<string, unknown>>(`/api/session/${id}/review`),
  reteach: (id: string) => request<{ mode: Mode; prompt: string }>(`/api/session/${id}/reteach`, { method: "POST" }),
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


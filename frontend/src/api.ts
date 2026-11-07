export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export type Mode = "TEACH" | "TEST" | "REVIEW" | "RETEACH" | "ESCALATED" | "FINISHED";
export type Emotion = "NEUTRAL" | "CURIOUS" | "CONFUSED" | "HAPPY" | "THINKING";
export type NoteStatus = "correct" | "incorrect" | "unsupported" | "pending";
export type TeachingMethod = "DEFINITION" | "ANALOGY" | "WORKED_EXAMPLE" | "DIAGRAM" | "STEP_BY_STEP";

export type MarkPoint = { id: string; text: string; concept: string; code?: string; answer?: string; marks?: number };
export type Question = {
  id: string;
  text: string;
  marks: number;
  type: "recall" | "application" | "edge_case" | "calculation";
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
export type PastPaper = {
  id: string;
  pack_id: string;
  title: string;
  questions: Question[];
  total_marks: number;
  source_files: string[];
  created_at: number;
};
export type PaperQuestionResult = {
  question_id: string;
  question_text: string;
  answer: string;
  marks: MarkResult[];
  score: number;
  max_score: number;
};
export type PaperAttempt = {
  id: string;
  paper_id: string;
  paper_title: string;
  results: PaperQuestionResult[];
  score: number;
  max_score: number;
  percentage: number;
  marker: "llm" | "heuristic";
  summary: string;
  created_at: number;
};
export type IngestResult = {
  draft_questions: Question[];
  title: string;
  total_marks: number;
  extractor: "llm" | "heuristic";
  warnings: string[];
};
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
  paper_attempts?: PaperAttempt[];
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
export type LearnedNote = {
  id: string;
  text: string;
  concept: string | null;
  concept_name: string;
  method: TeachingMethod;
  has_reason: boolean;
  has_example: boolean;
  status: NoteStatus;
  check_reason: string;
  retained: boolean;
  retention: number;
  memory_reason: string;
};
export type LearningSummary = {
  heard?: { source: string; words: number; text: string };
  stopped?: string;
  stopped_by?: "block" | "redirect";
  notes?: LearnedNote[];
  forgotten?: Array<{ id: string; text: string; concept_name: string }>;
  coverage_changes?: Array<{ concept: string; name: string; before: string; after: string }>;
  understanding_before?: number;
  understanding_after?: number;
  remembered_total?: number;
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
  reply_reason?: string;
  learning?: LearningSummary;
};
export type BrainView = {
  chud: ChudProfile;
  notes: Array<{ note: Note; retained: boolean; retention: number; reason: string }>;
  coverage: Array<{ concept_id: string; name: string; status: "UNTAUGHT" | "SHAKY" | "SOLID" }>;
  understanding: number;
  last_score: { score: number; max: number } | null;
  last_paper: { paper_id: string; title: string; score: number; max: number; percentage: number } | null;
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
  health: () => request<{ ok: boolean; mock_mode: boolean; voice: boolean; llm: boolean; default_pack: string }>("/api/health"),
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
    form.append("audio", blob, mime.includes("mp4") ? "phrase.mp4" : mime.includes("ogg") ? "phrase.ogg" : "phrase.webm");
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
  ingest: (paper: File, markScheme: File, packId = "gcse-maths") => {
    const form = new FormData();
    form.append("paper", paper);
    form.append("mark_scheme", markScheme);
    form.append("pack_id", packId);
    return request<IngestResult>("/api/ingest", { method: "POST", body: form });
  },
  papers: (packId: string) => request<{ papers: PastPaper[] }>(`/api/packs/${packId}/papers`),
  savePaper: (packId: string, title: string, questions: Question[], sourceFiles: string[] = []) =>
    request<{ paper: PastPaper }>(`/api/packs/${packId}/papers`, {
      method: "POST",
      body: JSON.stringify({ title, questions, source_files: sourceFiles }),
    }),
  deletePaper: (packId: string, paperId: string) => request<{ ok: boolean }>(`/api/packs/${packId}/papers/${paperId}`, { method: "DELETE" }),
  sitPaper: (sessionId: string, paperId: string) =>
    request<{ attempt: PaperAttempt; session: Session }>(`/api/sessions/${sessionId}/papers/${paperId}/sit`, { method: "POST" }),
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

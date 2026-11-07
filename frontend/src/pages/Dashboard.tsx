import { Mic, Square, Send, TestTube2, RefreshCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, Pack, PipelineStage, Profile, Session, TeachResponse } from "../api";
import { ChudCard } from "../components/ChudCard";
import { ModeBadge } from "../components/ModeBadge";
import { NotesPanel } from "../components/NotesPanel";
import { PipelineStrip } from "../components/PipelineStrip";
import { Transcript } from "../components/Transcript";

export function Dashboard() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [text, setText] = useState("");
  const [pipeline, setPipeline] = useState<PipelineStage[]>([]);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    void boot();
  }, []);

  async function boot() {
    try {
      const [packData, profileData] = await Promise.all([api.packs(), api.profiles()]);
      setPacks(packData.packs);
      setProfiles(profileData.profiles);
      const existing = localStorage.getItem("teach-chud-session");
      if (existing) {
        try {
          const state = await api.getSession(existing);
          setSession(state.session);
          return;
        } catch {
          localStorage.removeItem("teach-chud-session");
        }
      }
      const created = await api.createSession(packData.packs[0]?.id ?? "alevel-cs-algorithms");
      localStorage.setItem("teach-chud-session", created.session.id);
      setSession(created.session);
      await playReplies(created.intro_lines);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    }
  }

  async function refresh() {
    if (!session) return;
    const state = await api.getSession(session.id);
    setSession(state.session);
  }

  async function teach() {
    if (!session || !text.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.teachText(session.id, text);
      applyTeachResult(result);
      setText("");
      await refresh();
      await playReplies(result.replies);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Teaching failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecording() {
    if (recording) {
      recorder.current?.stop();
      setRecording(false);
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks.current = [];
    const media = new MediaRecorder(stream);
    recorder.current = media;
    media.ondataavailable = (event) => chunks.current.push(event.data);
    media.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      if (!session) return;
      setBusy(true);
      const blob = new Blob(chunks.current, { type: "audio/webm" });
      const result = await api.teachAudio(session.id, blob);
      applyTeachResult(result);
      await refresh();
      await playReplies(result.replies);
      setBusy(false);
    };
    media.start();
    setRecording(true);
  }

  function applyTeachResult(result: TeachResponse) {
    setPipeline(result.pipeline);
    setSession((previous) =>
      previous
        ? {
            ...previous,
            mode: result.mode,
            notes: [...previous.notes, ...result.notes_added],
            knowledge: result.knowledge,
            metrics: result.metrics,
          }
        : previous
    );
  }

  async function testClass() {
    if (!session) return;
    setBusy(true);
    await api.testClass(session.id, session.current_question_id ?? undefined);
    window.location.href = `/results/${session.id}`;
  }

  async function playReplies(replies: Array<{ chud_id: string; text: string; audio_url: string }>) {
    for (const reply of replies.filter((item) => item.audio_url)) {
      setSpeaking(reply.chud_id);
      await new Promise<void>((resolve) => {
        const audio = new Audio(api.audioUrl(reply.audio_url));
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        void audio.play().catch(() => resolve());
      });
    }
    setSpeaking(null);
  }

  const activePack = packs.find((pack) => pack.id === session?.pack_id);

  return (
    <main className="workspace">
      <section className="status-band">
        <div>
          <h1>{activePack?.topic ?? "Algorithms Classroom"}</h1>
          <p>{activePack?.sample_content_notice ?? "Mock mode ready."}</p>
        </div>
        <div className="status-actions">
          {session && <ModeBadge mode={session.mode} />}
          <button className="icon-button" onClick={refresh} title="Refresh session">
            <RefreshCcw size={20} />
          </button>
        </div>
      </section>

      <section className="class-grid">
        {profiles.map((profile) => (
          <ChudCard key={profile.id} profile={profile} knowledge={session?.knowledge[profile.id]} speaking={speaking === profile.id} />
        ))}
      </section>

      <section className="teach-surface">
        <div className="teacher-input">
          <button className={`talk-button ${recording ? "recording" : ""}`} onClick={toggleRecording} disabled={busy} title={recording ? "Stop recording" : "Start recording"}>
            {recording ? <Square size={36} /> : <Mic size={42} />}
          </button>
          <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Teach the class here..." />
          <button className="send-button" onClick={teach} disabled={busy || !text.trim()} title="Send typed teaching">
            <Send size={22} />
            Teach
          </button>
          <button className="test-button" onClick={testClass} disabled={busy || !session} title="Test the class">
            <TestTube2 size={22} />
            Test the class
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      <PipelineStrip stages={pipeline} />

      <section className="lower-grid">
        <Transcript session={session} profiles={profiles} />
        <NotesPanel notes={session?.notes ?? []} knowledge={session?.knowledge ?? {}} profiles={profiles} />
        <section className="panel">
          <div className="panel-title">
            <h2>Speech Metrics</h2>
          </div>
          <div className="metrics">
            <Metric label="WPM" value={String(session?.metrics.wpm ?? "N/A")} />
            <Metric label="Fillers" value={String(session?.metrics.filler_count ?? 0)} />
            <Metric label="Long pauses" value={String(session?.metrics.long_pauses ?? 0)} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Transitions</h2>
          </div>
          <details>
            <summary>History</summary>
            <pre>{JSON.stringify(session?.transitions ?? [], null, 2)}</pre>
          </details>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}


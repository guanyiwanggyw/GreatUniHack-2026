import { Brain, Check, Mic, Pause, Play, Send, Settings, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, Attempt, BrainView, ChudProfile, Emotion, Pack, PaperAttempt, PastPaper, Question, Session, TeachResponse } from "../api";
import { useBoardState } from "../features/board/useBoardState";
import { Whiteboard } from "../features/board/Whiteboard";
import { BrainDrawer } from "../features/chud/BrainDrawer";
import { ChudAvatar, SMART_THRESHOLD } from "../features/chud/ChudAvatar";
import { ExamPanel } from "../features/exam/ExamPanel";
import { useLiveTranscription } from "../features/listening/useLiveTranscription";
import { LearningPipeline } from "../features/pipeline/LearningPipeline";

export function Dashboard() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [papers, setPapers] = useState<PastPaper[]>([]);
  const [paperAttempt, setPaperAttempt] = useState<PaperAttempt | null>(null);
  const [sitting, setSitting] = useState("");
  const [profile, setProfile] = useState<ChudProfile | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [brain, setBrain] = useState<BrainView | null>(null);
  const [lastTeach, setLastTeach] = useState<TeachResponse | null>(null);
  const [lastEvent, setLastEvent] = useState<"teach" | "paper" | null>(null);
  const [teaching, setTeaching] = useState(false);
  const [typed, setTyped] = useState("");
  const [listening, setListening] = useState(false);
  const [caption, setCaption] = useState("Tap Chud to hear what he remembers.");
  const [emotion, setEmotion] = useState<Emotion>("NEUTRAL");
  const [speaking, setSpeaking] = useState(false);
  const [mouthLevel, setMouthLevel] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [review, setReview] = useState<Record<string, unknown> | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const meterRef = useRef<number>(0);

  useEffect(() => {
    void boot();
    return () => window.clearInterval(meterRef.current);
  }, []);

  async function boot() {
    try {
      const [packData, chudData] = await Promise.all([api.packs(), api.chud()]);
      setPacks(packData.packs);
      setProfile(chudData.chud);
      const packId = packData.packs[0]?.id ?? "alevel-cs-algorithms";
      const questionData = await api.questions(packId);
      setQuestions(questionData.questions);
      void loadPapers(packId);
      const stored = localStorage.getItem("teach-chud-session");
      if (stored) {
        try {
          const state = await api.getSession(stored);
          // Sessions from another subject (for example the old algorithms pack) are replaced with a fresh one.
          if (state.session.pack_id === packId) {
            setSession(state.session);
            setPaperAttempt(state.session.paper_attempts?.[state.session.paper_attempts.length - 1] ?? null);
            await loadBrain(state.session.id);
            return;
          }
        } catch {
          /* fall through to a new session */
        }
        localStorage.removeItem("teach-chud-session");
      }
      const created = await api.createSession(packId);
      localStorage.setItem("teach-chud-session", created.session.id);
      setSession(created.session);
      setCaption(created.intro_line.text);
      setEmotion(created.intro_line.emotion);
      await loadBrain(created.session.id);
      await play(created.intro_line.audio_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Teach-Chud.");
    }
  }

  async function loadPapers(packId = session?.pack_id ?? packs[0]?.id ?? "gcse-maths") {
    try {
      setPapers((await api.papers(packId)).papers);
    } catch {
      /* papers are optional */
    }
  }

  // Pick up papers uploaded in another tab when the teacher comes back to the whiteboard.
  useEffect(() => {
    const onVisible = () => document.visibilityState === "visible" && void loadPapers();
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  });

  async function refresh(id = session?.id) {
    if (!id) return;
    const state = await api.getSession(id);
    setSession(state.session);
    await loadBrain(id);
  }

  async function loadBrain(id = session?.id) {
    if (!id) return;
    setBrain(await api.brain(id));
  }

  const commitSegment = useCallback(
    async (text: string, words: Array<Record<string, unknown>> = [], source: "VOICE" | "TYPED" = "VOICE") => {
      if (!session || !text.trim()) return;
      setError("");
      setTeaching(true);
      try {
        const result = await api.teachSegment(session.id, text.trim(), source, words);
        setTeaching(false);
        applyTeachResult(result);
        await refresh(session.id);
        if (result.reply_text) {
          setCaption(result.reply_text);
          setEmotion(result.emotion);
          await play(result.reply_audio_url);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Teaching failed.");
      } finally {
        setTeaching(false);
      }
    },
    [session]
  );

  const stopAudio = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setSpeaking(false);
    setMouthLevel(0);
    window.clearInterval(meterRef.current);
  }, []);

  const live = useLiveTranscription({
    enabled: listening && Boolean(session),
    chudSpeaking: speaking,
    onSegment: async (text, words) => commitSegment(text, words, "VOICE"),
    onBargeIn: stopAudio,
  });

  const board = useBoardState(session);
  const pack = packs.find((item) => item.id === session?.pack_id);
  const smart = (brain?.understanding ?? 0) >= SMART_THRESHOLD || (brain?.last_paper?.percentage ?? 0) >= SMART_THRESHOLD * 100;
  const chudState = speaking ? "speaking" : live.status === "Chud thinking" ? "thinking" : listening ? "listening" : emotion === "CONFUSED" ? "confused" : emotion === "HAPPY" ? "happy" : "idle";

  function applyTeachResult(result: TeachResponse) {
    setLastTeach(result);
    setLastEvent("teach");
    setSession((previous) => (previous ? { ...previous, mode: result.mode, knowledge: result.knowledge, metrics: result.metrics, notes: [...previous.notes, ...result.notes_added] } : previous));
  }

  async function play(audioUrl: string) {
    if (!audioUrl) return;
    stopAudio();
    setSpeaking(true);
    const audio = new Audio(api.audioUrl(audioUrl));
    audioRef.current = audio;
    meterRef.current = window.setInterval(() => setMouthLevel(Math.random()), 90);
    await new Promise<void>((resolve) => {
      audio.onended = () => resolve();
      audio.onerror = () => resolve();
      void audio.play().catch(() => resolve());
    });
    stopAudio();
  }

  async function submitTyped() {
    if (!typed.trim()) return;
    const value = typed;
    setTyped("");
    await commitSegment(value, [], "TYPED");
  }

  async function doneExplaining() {
    if (typed.trim()) {
      await submitTyped();
      return;
    }
    await live.commit();
  }

  async function askRecap() {
    if (!session) return;
    const result = await api.recap(session.id);
    setCaption(result.reply_text);
    setEmotion(result.emotion);
    await refresh(session.id);
    await play(result.reply_audio_url);
  }

  async function testChud(questionId: string) {
    if (!session) return;
    const result = await api.testChud(session.id, questionId);
    setAttempt(result.attempt);
    setAnswer(result.attempt.answer);
    setReview(await api.review(session.id));
    await refresh(session.id);
  }

  async function sitPaper(paperId: string) {
    if (!session || sitting) return;
    setSitting(paperId);
    setError("");
    setCaption("Okay, I'll try the paper using only what you taught me...");
    setEmotion("THINKING");
    try {
      const result = await api.sitPaper(session.id, paperId);
      setPaperAttempt(result.attempt);
      setLastEvent("paper");
      setSession(result.session);
      await loadBrain(session.id);
      const pct = result.attempt.percentage;
      setCaption(pct >= 70 ? `I got ${Math.round(pct)}%! You taught me well.` : pct >= 40 ? `I got ${Math.round(pct)}%. Some of it clicked, some didn't.` : `I only got ${Math.round(pct)}%. Can you teach me more?`);
      setEmotion(pct >= 70 ? "HAPPY" : pct >= 40 ? "THINKING" : "CONFUSED");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chud could not sit the paper.");
    } finally {
      setSitting("");
    }
  }

  async function reteach() {
    if (!session) return;
    await api.reteach(session.id);
    await refresh(session.id);
  }

  return (
    <main className="app-shell">
      <header className="app-topbar">
        <a className="brand-mark" href="/" aria-label="Teach-Chud home">
          <Sparkles size={22} />
          Teach-Chud
        </a>
        <span className="topic-chip">{pack?.subject ?? "GCSE Mathematics"}</span>
        {brain?.last_paper && (
          <span className="paper-chip" title={brain.last_paper.title}>
            Last paper {Math.round(brain.last_paper.percentage)}%
          </span>
        )}
        <span className={`mode-badge mode-${session?.mode?.toLowerCase() ?? "teach"}`}>{session?.mode ?? "TEACH"}</span>
        <div className="understanding-ring" style={{ ["--understanding" as string]: `${Math.round((brain?.understanding ?? 0) * 100)}%` }}>
          {Math.round((brain?.understanding ?? 0) * 100)}%
        </div>
        <details className="settings-menu">
          <summary aria-label="Settings">
            <Settings size={20} />
          </summary>
          <a href="/ingest">Past papers</a>
          <a href="/tutor">Tutor queue</a>
        </details>
      </header>

      <section className="stage">
        <Whiteboard segments={board.segments} phrases={live.phrases} stickies={board.stickies} onEditPhrase={live.editPhrase} answer={answer} notice={live.error} />
        <div className="chud-stage">
          <div className="speech-bubble" aria-live="polite">
            {caption}
          </div>
          <ChudAvatar state={chudState} emotion={emotion} mouthLevel={mouthLevel} smart={smart} onClick={askRecap} onLongPress={() => setDrawerOpen(true)} />
        </div>
      </section>

      <section className="bottom-dock" aria-label="Teaching controls">
        <button className="dock-button" onClick={() => setListening((value) => !value)} aria-label={listening ? "Pause listening" : "Start listening"}>
          {listening ? <Pause size={20} /> : <Play size={20} />}
          {listening ? "Listening" : "Paused"}
        </button>
        <div className="level-meter" aria-label="Input level">
          <i style={{ width: `${Math.min(live.level * 900, 100)}%` }} />
        </div>
        <input value={typed} onChange={(event) => setTyped(event.target.value)} placeholder="Type a segment..." aria-label="Typed teaching fallback" />
        <button className="dock-button primary" onClick={submitTyped} disabled={!typed.trim()}>
          <Send size={20} />
          Send
        </button>
        <button className="dock-button" onClick={doneExplaining}>
          <Check size={20} />
          Done explaining
        </button>
        <button className="dock-button" onClick={askRecap}>
          <Mic size={20} />
          Ask recap
        </button>
        <button className="dock-button" onClick={() => setDrawerOpen(true)}>
          <Brain size={20} />
          Chud's brain
        </button>
      </section>

      <section className="side-panels">
        <ExamPanel
          questions={questions}
          papers={papers}
          attempt={attempt}
          paperAttempt={paperAttempt}
          review={review}
          sitting={sitting}
          onTest={testChud}
          onSitPaper={sitPaper}
          onReteach={reteach}
        />
        <div className="pipeline-column">
          <LearningPipeline
            teach={lastTeach}
            paper={paperAttempt}
            lastEvent={lastEvent}
            mode={session?.mode ?? "TEACH"}
            thinking={teaching || Boolean(sitting)}
            status={`${live.status}${live.engine ? ` · ${live.engine === "browser" ? "browser speech recognition" : "server transcription"}` : ""}`}
          />
          {error && <p className="error">{error}</p>}
        </div>
      </section>

      <BrainDrawer brain={brain} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </main>
  );
}

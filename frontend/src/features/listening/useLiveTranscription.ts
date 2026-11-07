import { useEffect, useRef, useState } from "react";
import { api, SttResponse } from "../../api";
import { LISTENING_CONFIG } from "./config";
import { createVad } from "./vad";

export type LivePhrase = {
  seq: number;
  text: string;
  pending: boolean;
  words: Array<Record<string, unknown>>;
};

type Status = "Paused" | "Listening" | "Transcribing" | "Chud thinking" | "Chud speaking";

type Options = {
  enabled: boolean;
  chudSpeaking: boolean;
  onSegment: (text: string, words: Array<Record<string, unknown>>) => Promise<void>;
  onBargeIn: () => void;
};

export function useLiveTranscription({ enabled, chudSpeaking, onSegment, onBargeIn }: Options) {
  const [status, setStatus] = useState<Status>("Paused");
  const [level, setLevel] = useState(0);
  const [phrases, setPhrases] = useState<LivePhrase[]>([]);
  const seq = useRef(0);
  const media = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const phraseStarted = useRef(0);
  const lastSpeechAt = useRef(0);
  const bargeStarted = useRef(0);
  const committing = useRef(false);

  useEffect(() => {
    if (!enabled) {
      setStatus("Paused");
      return;
    }
    let stream: MediaStream | null = null;
    let vad: { stop: () => void } | null = null;
    let timer = 0;

    async function start() {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      media.current = new MediaRecorder(stream);
      chunks.current = [];
      phraseStarted.current = performance.now();
      lastSpeechAt.current = performance.now();
      media.current.ondataavailable = (event) => chunks.current.push(event.data);
      media.current.onstop = () => void closePhrase();
      media.current.start();
      setStatus("Listening");
      vad = createVad(stream, ({ level: current, speaking }) => {
        setLevel(current);
        const now = performance.now();
        if (chudSpeaking && speaking) {
          if (!bargeStarted.current) bargeStarted.current = now;
          if (now - bargeStarted.current > LISTENING_CONFIG.BARGE_IN_MS) onBargeIn();
        } else {
          bargeStarted.current = 0;
        }
        if (speaking) lastSpeechAt.current = now;
      });
      timer = window.setInterval(() => void maybeClose(), 120);
    }

    async function maybeClose() {
      const recorder = media.current;
      if (!recorder || recorder.state !== "recording") return;
      const now = performance.now();
      const age = now - phraseStarted.current;
      const silent = now - lastSpeechAt.current;
      if ((silent > LISTENING_CONFIG.PHRASE_PAUSE_MS && age > LISTENING_CONFIG.MIN_PHRASE_MS) || age > LISTENING_CONFIG.MAX_PHRASE_MS) {
        recorder.stop();
      }
    }

    async function closePhrase() {
      const blob = new Blob(chunks.current, { type: "audio/webm" });
      chunks.current = [];
      const currentSeq = seq.current++;
      setPhrases((items) => [...items, { seq: currentSeq, text: "transcribing...", pending: true, words: [] }]);
      setStatus("Transcribing");
      let result: SttResponse | null = null;
      try {
        result = await api.stt(blob);
      } catch {
        result = { text: "", words: [], duration_ms: 0 };
      }
      setPhrases((items) => items.map((item) => (item.seq === currentSeq ? { ...item, text: result?.text || "", pending: false, words: result?.words || [] } : item)));
      phraseStarted.current = performance.now();
      lastSpeechAt.current = performance.now();
      media.current?.start();
      setStatus("Listening");
    }

    void start();
    return () => {
      window.clearInterval(timer);
      vad?.stop();
      if (media.current?.state === "recording") media.current.stop();
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [enabled, chudSpeaking, onBargeIn]);

  useEffect(() => {
    if (!enabled || committing.current) return;
    const handle = window.setInterval(() => {
      const ready = phrases.filter((phrase) => !phrase.pending && phrase.text.trim());
      const wordCount = ready.reduce((sum, phrase) => sum + phrase.text.trim().split(/\s+/).length, 0);
      if (ready.length && wordCount >= LISTENING_CONFIG.MIN_SEGMENT_WORDS && performance.now() - lastSpeechAt.current > LISTENING_CONFIG.SEGMENT_PAUSE_MS) {
        void commit();
      }
    }, 250);
    return () => window.clearInterval(handle);
  }, [enabled, phrases]);

  async function commit() {
    const ready = phrases.filter((phrase) => !phrase.pending && phrase.text.trim());
    if (!ready.length || committing.current) return;
    committing.current = true;
    setStatus("Chud thinking");
    await onSegment(
      ready.map((phrase) => phrase.text.trim()).join(" "),
      ready.flatMap((phrase) => phrase.words)
    );
    setPhrases([]);
    committing.current = false;
    setStatus(enabled ? "Listening" : "Paused");
  }

  function editPhrase(seqId: number, text: string) {
    setPhrases((items) => items.map((item) => (item.seq === seqId ? { ...item, text } : item)));
  }

  return { status, level, phrases, commit, editPhrase };
}

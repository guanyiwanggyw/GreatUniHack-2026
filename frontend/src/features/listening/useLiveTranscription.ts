import { useCallback, useEffect, useRef, useState } from "react";
import { api, SttResponse } from "../../api";
import { LISTENING_CONFIG } from "./config";
import { createVad } from "./vad";

export type LivePhrase = {
  seq: number;
  text: string;
  pending: boolean;
  words: Array<Record<string, unknown>>;
};

type Status = "Paused" | "Starting" | "Listening" | "Transcribing" | "Chud thinking" | "Chud speaking";

/**
 * "browser": the browser's own speech recognition (Chrome, Edge, Safari). Free, live interim text, no API key.
 * "server": record phrases and transcribe them through POST /api/stt (ElevenLabs Scribe when keys are set).
 */
export type SttEngine = "browser" | "server";

type Options = {
  enabled: boolean;
  chudSpeaking: boolean;
  onSegment: (text: string, words: Array<Record<string, unknown>>) => Promise<void>;
  onBargeIn: () => void;
};

type Recognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};
type RecognitionEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

function recognitionClass(): (new () => Recognition) | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recognition) | null;
}

function engineOverride(): SttEngine | null {
  const value = new URLSearchParams(window.location.search).get("stt");
  return value === "browser" || value === "server" ? value : null;
}

function wordsFor(text: string): Array<Record<string, unknown>> {
  return text.split(/\s+/).filter(Boolean).map((word) => ({ text: word, type: "word" }));
}

function micErrorMessage(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";
  if (!navigator.mediaDevices?.getUserMedia) return "Microphone needs a secure page. Open the app at http://127.0.0.1 or localhost in Chrome.";
  if (name === "NotAllowedError") return "Microphone access is blocked. Allow it in the browser's address bar, then press Start listening again.";
  if (name === "NotFoundError") return "No microphone was found.";
  return `Could not start the microphone${error instanceof Error ? `: ${error.message}` : "."}`;
}

export function useLiveTranscription({ enabled, chudSpeaking, onSegment, onBargeIn }: Options) {
  const [status, setStatus] = useState<Status>("Paused");
  const [level, setLevel] = useState(0);
  const [phrases, setPhrasesState] = useState<LivePhrase[]>([]);
  const [error, setError] = useState("");
  const [engine, setEngine] = useState<SttEngine | null>(null);

  const phrasesRef = useRef<LivePhrase[]>([]);
  const seq = useRef(0);
  const lastSpeechAt = useRef(0);
  const committing = useRef(false);
  const enabledRef = useRef(enabled);
  // Callbacks and Chud's speaking state live in refs so the microphone is not restarted every time they change.
  const chudSpeakingRef = useRef(chudSpeaking);
  const onSegmentRef = useRef(onSegment);
  const onBargeInRef = useRef(onBargeIn);
  enabledRef.current = enabled;
  chudSpeakingRef.current = chudSpeaking;
  onSegmentRef.current = onSegment;
  onBargeInRef.current = onBargeIn;

  const setPhrases = useCallback((update: (items: LivePhrase[]) => LivePhrase[]) => {
    phrasesRef.current = update(phrasesRef.current);
    setPhrasesState(phrasesRef.current);
  }, []);

  // Pick the engine once: real server transcription when the backend has keys, otherwise the browser's recogniser.
  useEffect(() => {
    let cancelled = false;
    const forced = engineOverride();
    if (forced) {
      setEngine(forced);
      return;
    }
    api
      .health()
      .then((health) => !cancelled && setEngine(health.mock_mode && recognitionClass() ? "browser" : "server"))
      .catch(() => !cancelled && setEngine(recognitionClass() ? "browser" : "server"));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!enabled || !engine) {
      setStatus("Paused");
      setLevel(0);
      return;
    }
    let stopped = false;
    let stream: MediaStream | null = null;
    let vad: { stop: () => void } | null = null;
    let recognition: Recognition | null = null;
    let recorder: MediaRecorder | null = null;
    let timer = 0;
    let chunks: Blob[] = [];
    let phraseStarted = 0;
    let phraseSpeechMs = 0;
    let lastFrame = 0;
    let bargeStarted = 0;

    setError("");
    setStatus("Starting");


    function startBrowserRecognition() {
      const Recognition = recognitionClass();
      if (!Recognition) {
        setError("This browser has no built-in speech recognition. Use Chrome or Edge, or type your explanation.");
        return;
      }
      const rec = new Recognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = navigator.language || "en-GB";
      rec.onresult = (event) => {
        let interim = "";
        const finals: string[] = [];
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const text = result[0].transcript.trim();
          if (!text) continue;
          if (result.isFinal) finals.push(text);
          else interim += `${text} `;
        }
        // The browser recogniser has no echo cancellation, so ignore what it hears while Chud is talking.
        if (chudSpeakingRef.current) return;
        lastSpeechAt.current = performance.now();
        setPhrases((items) => {
          const settled = items.filter((item) => !item.pending);
          for (const text of finals) settled.push({ seq: seq.current++, text, pending: false, words: wordsFor(text) });
          const live = interim.trim();
          return live ? [...settled, { seq: -1, text: live, pending: true, words: [] }] : settled;
        });
      };
      rec.onerror = (event) => {
        if (event.error === "no-speech" || event.error === "aborted") return;
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          setError("Speech recognition is blocked. Allow the microphone for this page, then press Start listening again.");
          stopped = true;
        } else if (event.error === "network") {
          setError("The browser's speech service is unreachable. Check your internet connection.");
        } else {
          setError(`Speech recognition error: ${event.error}`);
        }
      };
      // Chrome ends recognition after a pause or about a minute; restart while listening is on.
      rec.onend = () => {
        setPhrases((items) => items.filter((item) => !item.pending || item.text.trim()).map((item) => (item.seq === -1 ? { ...item, seq: seq.current++, pending: false, words: wordsFor(item.text) } : item)));
        if (!stopped && enabledRef.current) {
          try {
            rec.start();
          } catch {
            /* already started */
          }
        }
      };
      rec.start();
      recognition = rec;
    }

    async function transcribe(blob: Blob, mime: string) {
      const currentSeq = seq.current++;
      setPhrases((items) => [...items, { seq: currentSeq, text: "transcribing...", pending: true, words: [] }]);
      setStatus("Transcribing");
      let result: SttResponse = { text: "", words: [], duration_ms: 0 };
      try {
        result = await api.stt(blob, mime);
      } catch (err) {
        setError(err instanceof Error ? `Transcription failed: ${err.message.slice(0, 160)}` : "Transcription failed.");
      }
      const text = result.text.trim();
      setPhrases((items) =>
        text ? items.map((item) => (item.seq === currentSeq ? { ...item, text, pending: false, words: result.words } : item)) : items.filter((item) => item.seq !== currentSeq)
      );
      if (!stopped) setStatus("Listening");
    }

    function startServerRecording(source: MediaStream) {
      const rec = new MediaRecorder(source);
      const mime = rec.mimeType || "audio/webm";
      rec.ondataavailable = (event) => event.data.size && chunks.push(event.data);
      rec.onstop = () => {
        const blob = new Blob(chunks, { type: mime });
        const hadSpeech = phraseSpeechMs >= LISTENING_CONFIG.MIN_SPEECH_MS;
        chunks = [];
        // Start the next phrase straight away so nothing said during transcription is lost.
        if (!stopped && source.active) {
          phraseStarted = performance.now();
          phraseSpeechMs = 0;
          rec.start();
        }
        if (hadSpeech) void transcribe(blob, mime);
      };
      phraseStarted = performance.now();
      phraseSpeechMs = 0;
      rec.start();
      recorder = rec;
    }

    function maybeClosePhrase() {
      if (!recorder || recorder.state !== "recording") return;
      const now = performance.now();
      const age = now - phraseStarted;
      const silent = now - lastSpeechAt.current;
      const hadSpeech = phraseSpeechMs >= LISTENING_CONFIG.MIN_SPEECH_MS;
      // Only close phrases that contain speech; long silent stretches are thrown away instead of uploaded.
      if (hadSpeech && ((silent > LISTENING_CONFIG.PHRASE_PAUSE_MS && age > LISTENING_CONFIG.MIN_PHRASE_MS) || age > LISTENING_CONFIG.MAX_PHRASE_MS)) {
        recorder.stop();
      } else if (!hadSpeech && age > LISTENING_CONFIG.MAX_PHRASE_MS) {
        phraseSpeechMs = 0;
        recorder.stop();
      }
    }

    async function start() {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("insecure");
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        });
      } catch (err) {
        setError(micErrorMessage(err));
        setStatus("Paused");
        return;
      }
      if (stopped) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      lastSpeechAt.current = 0;
      lastFrame = performance.now();
      vad = createVad(stream, ({ level: current, speaking }) => {
        const now = performance.now();
        setLevel(current);
        if (speaking) {
          phraseSpeechMs += now - lastFrame;
          if (engine === "server") lastSpeechAt.current = now;
        }
        lastFrame = now;
        if (chudSpeakingRef.current && speaking) {
          if (!bargeStarted) bargeStarted = now;
          if (now - bargeStarted > LISTENING_CONFIG.BARGE_IN_MS) onBargeInRef.current();
        } else {
          bargeStarted = 0;
        }
      });
      if (engine === "browser") startBrowserRecognition();
      else {
        startServerRecording(stream);
        timer = window.setInterval(maybeClosePhrase, 120);
      }
      setStatus("Listening");
    }

    void start();
    return () => {
      stopped = true;
      window.clearInterval(timer);
      vad?.stop();
      recognition?.abort();
      if (recorder?.state === "recording") recorder.stop();
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [enabled, engine, setPhrases]);

  const commit = useCallback(async () => {
    const ready = phrasesRef.current.filter((phrase) => !phrase.pending && phrase.text.trim());
    if (!ready.length || committing.current) return;
    committing.current = true;
    const committedSeqs = new Set(ready.map((phrase) => phrase.seq));
    setStatus("Chud thinking");
    try {
      await onSegmentRef.current(
        ready.map((phrase) => phrase.text.trim()).join(" "),
        ready.flatMap((phrase) => phrase.words)
      );
    } finally {
      // Keep anything spoken while Chud was thinking.
      setPhrases((items) => items.filter((item) => !committedSeqs.has(item.seq)));
      committing.current = false;
      setStatus(enabledRef.current ? "Listening" : "Paused");
    }
  }, [setPhrases]);

  // Commit automatically once the teacher has paused long enough after saying enough.
  useEffect(() => {
    if (!enabled) return;
    const handle = window.setInterval(() => {
      if (committing.current || !lastSpeechAt.current) return;
      const items = phrasesRef.current;
      if (items.some((phrase) => phrase.pending)) return;
      const wordCount = items.reduce((sum, phrase) => sum + phrase.text.trim().split(/\s+/).filter(Boolean).length, 0);
      if (wordCount >= LISTENING_CONFIG.MIN_SEGMENT_WORDS && performance.now() - lastSpeechAt.current > LISTENING_CONFIG.SEGMENT_PAUSE_MS) {
        void commit();
      }
    }, 250);
    return () => window.clearInterval(handle);
  }, [enabled, commit]);

  const editPhrase = useCallback(
    (seqId: number, text: string) => setPhrases((items) => items.map((item) => (item.seq === seqId ? { ...item, text } : item))),
    [setPhrases]
  );

  return { status, level, phrases, error, engine, commit, editPhrase };
}

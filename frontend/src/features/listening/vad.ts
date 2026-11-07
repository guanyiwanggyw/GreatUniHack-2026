import { LISTENING_CONFIG } from "./config";

export type VadState = {
  level: number;
  speaking: boolean;
};

export function createVad(stream: MediaStream, onFrame: (state: VadState) => void) {
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const data = new Float32Array(analyser.fftSize);
  let raf = 0;
  let speaking = false;

  function tick() {
    analyser.getFloatTimeDomainData(data);
    let sum = 0;
    for (const frame of data) sum += frame * frame;
    const level = Math.sqrt(sum / data.length);
    if (!speaking && level > LISTENING_CONFIG.RMS_ON) speaking = true;
    if (speaking && level < LISTENING_CONFIG.RMS_OFF) speaking = false;
    onFrame({ level, speaking });
    raf = requestAnimationFrame(tick);
  }

  tick();
  return {
    stop() {
      cancelAnimationFrame(raf);
      void context.close();
    },
  };
}

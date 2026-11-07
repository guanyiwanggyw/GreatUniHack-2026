import { Emotion } from "../../api";
import chudAfter from "../../assets/chud-after.png";
import chudBefore from "../../assets/chud-before.png";

/** Chud starts as the confused slime and becomes the graduate once he understands enough of the topic. */
export const SMART_THRESHOLD = 0.6;

export function ChudAvatar({
  state,
  emotion,
  mouthLevel,
  smart,
  onClick,
  onLongPress,
}: {
  state: "idle" | "listening" | "thinking" | "speaking" | "confused" | "happy";
  emotion: Emotion;
  mouthLevel: number;
  smart: boolean;
  onClick: () => void;
  onLongPress: () => void;
}) {
  let timer = 0;
  return (
    <button
      className={`chud-avatar ${state} emotion-${emotion.toLowerCase()} ${smart ? "smart" : "learning"}`}
      onClick={onClick}
      onPointerDown={() => {
        timer = window.setTimeout(onLongPress, 550);
      }}
      onPointerUp={() => window.clearTimeout(timer)}
      title="Ask me what I know"
      aria-label={smart ? "Chud, graduated. Ask what he knows" : "Chud, still learning. Ask what he knows"}
      style={{ ["--mouth" as string]: String(mouthLevel) }}
    >
      <img className={`chud-img before ${smart ? "hidden" : ""}`} src={chudBefore} alt="" draggable={false} />
      <img className={`chud-img after ${smart ? "" : "hidden"}`} src={chudAfter} alt="" draggable={false} />
    </button>
  );
}

import { Emotion } from "../../api";

export function ChudAvatar({
  state,
  emotion,
  mouthLevel,
  onClick,
  onLongPress,
}: {
  state: "idle" | "listening" | "thinking" | "speaking" | "confused" | "happy";
  emotion: Emotion;
  mouthLevel: number;
  onClick: () => void;
  onLongPress: () => void;
}) {
  let timer = 0;
  return (
    <button
      className={`chud-avatar ${state} emotion-${emotion.toLowerCase()}`}
      onClick={onClick}
      onPointerDown={() => {
        timer = window.setTimeout(onLongPress, 550);
      }}
      onPointerUp={() => window.clearTimeout(timer)}
      title="Ask me what I know"
      aria-label="Ask Chud what he knows"
    >
      <svg viewBox="0 0 180 220" role="img" aria-label="Chud">
        <ellipse className="shadow" cx="90" cy="202" rx="54" ry="10" />
        <path className="body" d="M42 86c0-42 25-70 48-70s48 28 48 70v52c0 36-21 58-48 58s-48-22-48-58z" />
        <path className="belly" d="M62 113c0-24 13-39 28-39s28 15 28 39v29c0 22-12 35-28 35s-28-13-28-35z" />
        <circle className="eye" cx="72" cy="74" r="10" />
        <circle className="eye" cx="108" cy="74" r="10" />
        <circle className="pupil" cx="74" cy="75" r="4" />
        <circle className="pupil" cx="110" cy="75" r="4" />
        <path className="mouth" d={`M76 ${112 + mouthLevel * 3} Q90 ${124 + mouthLevel * 16} 104 ${112 + mouthLevel * 3}`} />
        <path className="arm left" d="M45 118c-22 8-30 22-24 34" />
        <path className="arm right" d="M135 118c22 8 30 22 24 34" />
      </svg>
    </button>
  );
}

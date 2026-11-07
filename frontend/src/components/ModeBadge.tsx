import type { Mode } from "../api";

export function ModeBadge({ mode }: { mode: Mode }) {
  return <span className={`mode mode-${mode.toLowerCase()}`}>{mode}</span>;
}


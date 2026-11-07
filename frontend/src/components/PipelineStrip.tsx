import type { PipelineStage } from "../api";

const defaultStages = [
  "STT",
  "Input guardrail",
  "Extractor",
  "FactChecker",
  "Retention",
  "Chud response",
  "Output guardrail",
  "TTS",
  "Escalation check",
];

export function PipelineStrip({ stages }: { stages: PipelineStage[] }) {
  const byName = new Map(stages.map((stage) => [stage.name, stage]));
  return (
    <div className="pipeline" aria-label="pipeline">
      {defaultStages.map((name) => {
        const stage = byName.get(name);
        return (
          <div key={name} className={`pipe ${stage?.status ?? "idle"}`} title={stage ? `${stage.detail} (${stage.latency_ms}ms)` : ""}>
            <span>{name}</span>
            <small>{stage ? `${stage.latency_ms}ms` : "idle"}</small>
          </div>
        );
      })}
    </div>
  );
}


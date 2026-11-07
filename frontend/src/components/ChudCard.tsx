import type { Knowledge, Profile } from "../api";

export function ChudCard({ profile, knowledge, speaking }: { profile: Profile; knowledge?: Knowledge; speaking?: boolean }) {
  const concepts = Object.entries(knowledge?.retention_by_concept ?? {});
  return (
    <article className={`chud ${speaking ? "speaking" : ""}`}>
      <div className="chud-head">
        <div className="avatar">{profile.avatar}</div>
        <div>
          <h3>{profile.name}</h3>
          <p>{profile.description}</p>
        </div>
      </div>
      <div className="retention-bars">
        {concepts.length === 0 && <small className="muted">No retained concepts yet</small>}
        {concepts.slice(0, 5).map(([concept, value]) => (
          <div key={concept} className="retention-row" title={knowledge?.explanations?.[concept] ?? concept}>
            <span>{concept.replaceAll("_", " ")}</span>
            <div className="bar">
              <i style={{ width: `${Math.round(value * 100)}%` }} />
            </div>
            <b>{Math.round(value * 100)}%</b>
          </div>
        ))}
      </div>
    </article>
  );
}


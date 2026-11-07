import type { Profile, Session } from "../api";

export function Transcript({ session, profiles }: { session: Session | null; profiles: Profile[] }) {
  const profileNames = new Map(profiles.map((profile) => [profile.id, profile.name]));
  return (
    <section className="panel transcript-panel">
      <div className="panel-title">
        <h2>Transcript</h2>
        <span>{session?.transcript.length ?? 0}</span>
      </div>
      <div className="transcript">
        {(session?.transcript ?? []).map((line, index) => {
          const role = String(line.role ?? "system");
          const chudId = String(line.chud_id ?? "");
          const speaker = String(line.speaker ?? profileNames.get(chudId) ?? role);
          return (
            <p key={index} className={`line ${role}`}>
              <b>{speaker}</b>
              <span>{String(line.text ?? "")}</span>
            </p>
          );
        })}
      </div>
    </section>
  );
}


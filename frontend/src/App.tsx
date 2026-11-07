import { GraduationCap, Inbox, LayoutDashboard, Upload } from "lucide-react";
import { Dashboard } from "./pages/Dashboard";
import { Ingest } from "./pages/Ingest";
import { Results } from "./pages/Results";
import { Tutor } from "./pages/Tutor";

export function App() {
  const path = window.location.pathname;
  let page = <Dashboard />;
  if (path.startsWith("/results/")) page = <Results sessionId={path.split("/").pop() ?? ""} />;
  if (path.startsWith("/ingest")) page = <Ingest />;
  if (path.startsWith("/tutor")) page = <Tutor />;

  return (
    <div>
      <nav className="topbar">
        <a className="brand" href="/">
          <GraduationCap size={28} />
          <span>Teach-Chud</span>
        </a>
        <div className="navlinks">
          <a href="/" title="Dashboard">
            <LayoutDashboard size={20} />
            Dashboard
          </a>
          <a href="/ingest" title="Paper ingest">
            <Upload size={20} />
            Ingest
          </a>
          <a href="/tutor" title="Tutor queue">
            <Inbox size={20} />
            Tutor
          </a>
        </div>
      </nav>
      {page}
    </div>
  );
}


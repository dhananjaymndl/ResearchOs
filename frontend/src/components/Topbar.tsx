import { Link } from "react-router-dom";

export default function Topbar({ action }: { action?: React.ReactNode }) {
  return (
    <div className="topbar">
      <div className="topbar-inner">
        <Link to="/" className="brand-mark">
          <div className="brand-logo">R</div>
          <div>
            <div className="brand">ResearchOS</div>
            <div className="brand-sub">Autonomous ML Experimentation</div>
          </div>
        </Link>
        {action}
      </div>
    </div>
  );
}

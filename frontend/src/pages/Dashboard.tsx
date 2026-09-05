import { useEffect, useState } from "react";
import type { MouseEvent } from "react";
import { Link } from "react-router-dom";
import { api, ProjectSummary } from "../api/client";
import Topbar from "../components/Topbar";

function statusBadgeClass(status: string): string {
  if (["RESEARCHING", "BASELINE_RUNNING", "PROFILING"].includes(status)) return "badge badge-running";
  if (status === "COMPLETED") return "badge badge-completed";
  if (status === "FAILED") return "badge badge-failed";
  return "badge";
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function load() {
    setError(null);
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  async function handleDelete(e: MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm("Delete this project? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await api.deleteProject(id);
      setProjects((prev) => prev?.filter((p) => p.id !== id) ?? prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <Topbar
        action={
          <Link to="/new">
            <button className="btn">+ New Research Project</button>
          </Link>
        }
      />
      <div className="page">
        {error && (
          <div className="error-box">
            {error}
            <button className="btn-link" style={{ marginLeft: 12 }} onClick={load}>
              Retry
            </button>
          </div>
        )}

        <div className="section-title">
          Recent Projects
          {projects && projects.length > 0 && <span className="count">{projects.length}</span>}
        </div>

        {projects === null && !error && (
          <div className="loading-row">
            <div className="spinner" />
            Loading projects…
          </div>
        )}

        {projects && projects.length === 0 && (
          <div className="card empty-state">
            No research projects yet.
            <div style={{ marginTop: 16 }}>
              <Link to="/new">
                <button className="btn">+ New Research Project</button>
              </Link>
            </div>
          </div>
        )}

        <div className="grid grid-cards">
          {projects?.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="card project-card">
              <div className="exp-header">
                <div className="exp-title" style={{ fontSize: 15 }}>
                  {p.name}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className={statusBadgeClass(p.status)}>{statusLabel(p.status)}</span>
                  <button
                    className="icon-btn"
                    title="Delete project"
                    disabled={deletingId === p.id}
                    onClick={(e) => handleDelete(e, p.id)}
                  >
                    {deletingId === p.id ? "…" : "✕"}
                  </button>
                </div>
              </div>
              <div className="muted" style={{ marginTop: 10 }}>
                {p.dataset_filename || "No dataset uploaded"}
              </div>
              <hr className="divider" />
              <div className="stat-row">
                <div>
                  <div className="stat-label">Experiments</div>
                  <div className="stat-value small">
                    {p.experiment_count}/{p.experiment_budget + 1}
                  </div>
                </div>
                <div>
                  <div className="stat-label">Baseline {p.primary_metric.toUpperCase()}</div>
                  <div className="stat-value small">{p.baseline_metric?.toFixed(3) ?? "—"}</div>
                </div>
                <div>
                  <div className="stat-label">Best {p.primary_metric.toUpperCase()}</div>
                  <div className="stat-value small good">{p.best_metric?.toFixed(3) ?? "—"}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

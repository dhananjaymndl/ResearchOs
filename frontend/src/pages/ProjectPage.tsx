import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  DatasetProfile,
  ExperimentDetail,
  ProjectSummary,
  ResearchEvent,
} from "../api/client";
import MetricChart from "../components/MetricChart";
import Topbar from "../components/Topbar";

const ACTIVE_STATUSES = ["PROFILING", "BASELINE_RUNNING", "RESEARCHING"];

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function eventClass(eventType: string): string {
  if (eventType === "warning") return "event-warning";
  if (eventType === "failure" || eventType === "error") return "event-failure";
  if (eventType === "completed" || eventType === "experiment_completed") return "event-completed";
  return "";
}

function statusBadgeClass(status: string): string {
  if (["RESEARCHING", "BASELINE_RUNNING", "PROFILING"].includes(status)) return "badge badge-running";
  if (status === "COMPLETED") return "badge badge-completed";
  if (status === "FAILED") return "badge badge-failed";
  return "badge";
}

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [events, setEvents] = useState<ResearchEvent[]>([]);
  const [experiments, setExperiments] = useState<ExperimentDetail[]>([]);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  async function refresh() {
    if (!projectId) return;
    try {
      const [p, e, exps] = await Promise.all([
        api.getProject(projectId),
        api.getEvents(projectId),
        api.listExperiments(projectId),
      ]);
      setProject(p);
      setEvents(e);
      setExperiments(exps);
      if (p.dataset_filename) {
        api.getDatasetProfile(projectId).then(setProfile).catch(() => {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    refresh();
    intervalRef.current = window.setInterval(refresh, 2500);
    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    if (!project) return;
    const shouldPoll = ACTIVE_STATUSES.includes(project.status);
    if (!shouldPoll && intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    } else if (shouldPoll && !intervalRef.current) {
      intervalRef.current = window.setInterval(refresh, 2500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.status]);

  const [pauseToggling, setPauseToggling] = useState(false);

  async function togglePause() {
    if (!project) return;
    setPauseToggling(true);
    try {
      if (project.status === "RESEARCHING") {
        await api.pauseResearch(project.id);
      } else if (project.status === "PAUSED") {
        await api.resumeResearch(project.id);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPauseToggling(false);
    }
  }

  if (error) {
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="error-box">
            {error}
            <button className="btn-link" style={{ marginLeft: 12 }} onClick={refresh}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="loading-row">
            <div className="spinner" />
            Loading project…
          </div>
        </div>
      </div>
    );
  }

  const improvement =
    project.baseline_metric != null && project.best_metric != null && project.baseline_metric !== 0
      ? (((project.best_metric - project.baseline_metric) / project.baseline_metric) * 100).toFixed(1)
      : null;

  const completedExperiments = experiments.filter((e) => e.status === "COMPLETED");
  const chartPoints = completedExperiments.map((e) => ({
    label: e.sequence_number === 0 ? "Base" : `E${e.sequence_number}`,
    value: e.metrics[project.primary_metric] ?? null,
    isBest: e.id === project.best_experiment_id,
  }));

  return (
    <div>
      <Topbar />
      <div className="page">
        <Link to="/" className="back-link">
          ← Dashboard
        </Link>
        <div className="exp-header" style={{ marginBottom: 28, alignItems: "flex-start" }}>
          <div>
            <div className="page-title">{project.name}</div>
            <div className="muted" style={{ marginTop: 4 }}>
              {project.objective}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {(project.status === "RESEARCHING" || project.status === "PAUSED") && (
              <button className="btn btn-secondary" disabled={pauseToggling} onClick={togglePause}>
                {project.status === "RESEARCHING" ? "Pause" : "Resume"}
              </button>
            )}
            {experiments.length > 0 && (
              <Link to={`/projects/${project.id}/report`}>
                <button className="btn btn-secondary">View Report</button>
              </Link>
            )}
            <span className={statusBadgeClass(project.status)}>{project.status.replace(/_/g, " ")}</span>
          </div>
        </div>

        {/* B. Dataset Summary */}
        {profile && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Dataset Summary</div>
            <div className="stat-row">
              <div>
                <div className="stat-label">Rows</div>
                <div className="stat-value">{profile.rows.toLocaleString()}</div>
              </div>
              <div>
                <div className="stat-label">Features</div>
                <div className="stat-value">{profile.features}</div>
              </div>
              <div>
                <div className="stat-label">Problem</div>
                <div className="stat-value small">Binary Classification</div>
              </div>
              <div>
                <div className="stat-label">Minority Class</div>
                <div className="stat-value">
                  {profile.target_distribution.minority_percentage?.toFixed(2) ?? "—"}%
                </div>
              </div>
              <div>
                <div className="stat-label">Primary Metric</div>
                <div className="stat-value small">{project.primary_metric.toUpperCase()}</div>
              </div>
              <div>
                <div className="stat-label">Budget</div>
                <div className="stat-value small">{project.experiment_budget}</div>
              </div>
            </div>
            {profile.warnings.length > 0 && (
              <div style={{ marginTop: 18 }}>
                {profile.warnings.map((w, i) => (
                  <div key={i} className="warning-box">
                    <span>⚠</span>
                    <span>{w}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* C. Performance Summary */}
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="section-title">Performance Summary</div>
          <div className="stat-row">
            <div>
              <div className="stat-label">Baseline {project.primary_metric.toUpperCase()}</div>
              <div className="stat-value">{project.baseline_metric?.toFixed(4) ?? "—"}</div>
            </div>
            <div>
              <div className="stat-label">Best {project.primary_metric.toUpperCase()}</div>
              <div className="stat-value good">{project.best_metric?.toFixed(4) ?? "—"}</div>
            </div>
            <div>
              <div className="stat-label">Improvement</div>
              <div className="stat-value good">{improvement != null ? `+${improvement}%` : "—"}</div>
            </div>
            <div>
              <div className="stat-label">Experiments</div>
              <div className="stat-value">
                {Math.max(project.experiment_count - 1, 0)} / {project.experiment_budget}
              </div>
            </div>
          </div>
          {chartPoints.length > 1 && (
            <div style={{ marginTop: 20 }}>
              <MetricChart points={chartPoints} metricLabel={project.primary_metric} />
            </div>
          )}
        </div>

        <div className="grid grid-2">
          {/* D. Research Timeline */}
          <div className="card">
            <div className="section-title">
              Research Timeline
              {project.status !== "COMPLETED" && ACTIVE_STATUSES.includes(project.status) && (
                <span className="spinner" style={{ width: 13, height: 13, borderWidth: 2 }} />
              )}
            </div>
            {events.length === 0 && <div className="empty-state">No events yet.</div>}
            <div className="timeline">
              {[...events].reverse().map((e) => (
                <div key={e.id} className={`timeline-item ${eventClass(e.event_type)}`}>
                  <div className="timeline-time">{formatTime(e.created_at)}</div>
                  <div className="timeline-msg">{e.message}</div>
                </div>
              ))}
            </div>
          </div>

          {/* E. Experiment List */}
          <div className="card">
            <div className="section-title">
              Experiments
              {experiments.length > 0 && <span className="count">{experiments.length}</span>}
            </div>
            {experiments.length === 0 && <div className="empty-state">No experiments yet.</div>}
            {[...experiments].reverse().map((exp) => {
              const isBest = exp.id === project.best_experiment_id;
              const metricVal = exp.metrics[project.primary_metric];
              const parent = experiments.find((e) => e.id === exp.parent_experiment_id);
              return (
                <Link key={exp.id} to={`/experiments/${exp.id}`}>
                  <div className={`experiment-card ${isBest ? "best" : ""}`}>
                    <div className="exp-header">
                      <div className="exp-title">
                        Experiment {String(exp.sequence_number).padStart(2, "0")} — {exp.model}
                      </div>
                      <span
                        className={
                          isBest
                            ? "badge badge-best"
                            : exp.status === "COMPLETED"
                            ? "badge badge-completed"
                            : exp.status === "FAILED"
                            ? "badge badge-failed"
                            : "badge badge-running"
                        }
                      >
                        {isBest ? "Best" : exp.status}
                      </span>
                    </div>
                    <div className="exp-hypothesis">{exp.hypothesis}</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                      <div>
                        <span className="exp-metric">{metricVal != null ? metricVal.toFixed(4) : "—"}</span>
                        <span className="exp-metric-label">{project.primary_metric}</span>
                      </div>
                      {parent && (
                        <span className="muted" style={{ fontSize: 11 }}>
                          ↳ from E{String(parent.sequence_number).padStart(2, "0")}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

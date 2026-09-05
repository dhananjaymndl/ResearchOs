import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import Topbar from "../components/Topbar";

interface ExperimentSummary {
  sequence_number: number;
  model: string;
  hypothesis?: string;
  metrics?: Record<string, number>;
  status?: string;
  hypothesis_outcome?: string | null;
}

interface Report {
  research_objective: string;
  primary_metric: string;
  dataset_concerns: string[];
  baseline: { model: string | null; metrics: Record<string, number> } | null;
  best_experiment: (ExperimentSummary & { metrics: Record<string, number> }) | null;
  improvement_over_baseline: { absolute: number; relative_percent: number } | null;
  key_findings: ExperimentSummary[];
  failed_hypotheses: ExperimentSummary[];
  limitations: string[];
  recommended_future_experiments: string[];
  experiment_count: number;
  failed_experiment_count: number;
}

export default function ReportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    if (!projectId) return;
    setError(null);
    api
      .getReport(projectId)
      .then((r) => setReport(r as unknown as Report))
      .catch((e) => setError(e.message));
  }

  useEffect(load, [projectId]);

  if (error) {
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="error-box">
            {error}
            <button className="btn-link" style={{ marginLeft: 12 }} onClick={load}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="loading-row">
            <div className="spinner" />
            Generating report…
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Topbar />
      <div className="page">
        <Link to={`/projects/${projectId}`} className="back-link">
          ← Back to project
        </Link>

        <div className="page-title" style={{ marginBottom: 4 }}>
          Research Report
        </div>
        <div className="muted" style={{ marginBottom: 28 }}>
          {report.research_objective}
        </div>

        <div className="card" style={{ marginBottom: 18 }}>
          <div className="section-title">Summary</div>
          <div className="stat-row">
            <div>
              <div className="stat-label">Baseline {report.primary_metric.toUpperCase()}</div>
              <div className="stat-value">
                {report.baseline?.metrics?.[report.primary_metric]?.toFixed(4) ?? "—"}
              </div>
            </div>
            <div>
              <div className="stat-label">Best {report.primary_metric.toUpperCase()}</div>
              <div className="stat-value good">
                {report.best_experiment?.metrics?.[report.primary_metric]?.toFixed(4) ?? "—"}
              </div>
            </div>
            <div>
              <div className="stat-label">Improvement</div>
              <div className="stat-value good">
                {report.improvement_over_baseline
                  ? `+${report.improvement_over_baseline.relative_percent.toFixed(1)}%`
                  : "—"}
              </div>
            </div>
            <div>
              <div className="stat-label">Experiments Run</div>
              <div className="stat-value">{report.experiment_count}</div>
            </div>
            <div>
              <div className="stat-label">Failed Runs</div>
              <div className="stat-value">{report.failed_experiment_count}</div>
            </div>
          </div>
          {report.best_experiment && (
            <>
              <hr className="divider" />
              <div className="stat-label">Best Model</div>
              <div style={{ marginTop: 4 }}>
                Experiment {String(report.best_experiment.sequence_number).padStart(2, "0")} —{" "}
                <strong>{report.best_experiment.model}</strong>
              </div>
            </>
          )}
        </div>

        {report.dataset_concerns.length > 0 && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Dataset Concerns</div>
            {report.dataset_concerns.map((w, i) => (
              <div key={i} className="warning-box">
                <span>⚠</span>
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-2">
          <div className="card">
            <div className="section-title">
              Key Findings
              {report.key_findings.length > 0 && <span className="count">{report.key_findings.length}</span>}
            </div>
            {report.key_findings.length === 0 && <div className="empty-state">No supported hypotheses yet.</div>}
            {report.key_findings.map((f, i) => (
              <div key={i} style={{ marginBottom: 14 }}>
                <div className="stat-label">
                  E{String(f.sequence_number).padStart(2, "0")} — {f.model}
                </div>
                <div style={{ marginTop: 4, lineHeight: 1.5 }}>{f.hypothesis}</div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="section-title">
              Failed Hypotheses
              {report.failed_hypotheses.length > 0 && (
                <span className="count">{report.failed_hypotheses.length}</span>
              )}
            </div>
            {report.failed_hypotheses.length === 0 && <div className="empty-state">No regressions recorded.</div>}
            {report.failed_hypotheses.map((f, i) => (
              <div key={i} style={{ marginBottom: 14 }}>
                <div className="stat-label">
                  E{String(f.sequence_number).padStart(2, "0")} — {f.model}
                </div>
                <div style={{ marginTop: 4, lineHeight: 1.5 }}>{f.hypothesis}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ marginTop: 18, marginBottom: 18 }}>
          <div className="section-title">Recommended Next Experiments</div>
          <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
            {report.recommended_future_experiments.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>

        <div className="card">
          <div className="section-title">Limitations</div>
          <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }} className="muted">
            {report.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

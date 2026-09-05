import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ExperimentDetail as ExperimentDetailType } from "../api/client";
import Topbar from "../components/Topbar";

const OUTCOME_COLOR: Record<string, string> = {
  SUPPORTED: "badge-completed",
  NOT_SUPPORTED: "badge-failed",
  INCONCLUSIVE: "",
};

function ConfusionMatrixGrid({ matrix }: { matrix: number[][] }) {
  const [[tn, fp], [fn, tp]] = matrix;
  const cellStyle = (kind: "tn" | "fp" | "fn" | "tp"): CSSProperties => ({
    padding: "16px 20px",
    borderRadius: 8,
    textAlign: "center",
    background: kind === "tn" || kind === "tp" ? "var(--good-soft)" : "var(--bad-soft)",
    border: `1px solid ${kind === "tn" || kind === "tp" ? "var(--good)" : "var(--bad)"}`,
  });
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "auto auto auto", gap: 6, fontSize: 12 }}>
        <div />
        <div className="stat-label" style={{ textAlign: "center" }}>Pred 0</div>
        <div className="stat-label" style={{ textAlign: "center" }}>Pred 1</div>

        <div className="stat-label" style={{ display: "flex", alignItems: "center" }}>Actual 0</div>
        <div style={cellStyle("tn")}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{tn}</div>
          <div className="muted" style={{ fontSize: 11 }}>TN</div>
        </div>
        <div style={cellStyle("fp")}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{fp}</div>
          <div className="muted" style={{ fontSize: 11 }}>FP</div>
        </div>

        <div className="stat-label" style={{ display: "flex", alignItems: "center" }}>Actual 1</div>
        <div style={cellStyle("fn")}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{fn}</div>
          <div className="muted" style={{ fontSize: 11 }}>FN</div>
        </div>
        <div style={cellStyle("tp")}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{tp}</div>
          <div className="muted" style={{ fontSize: 11 }}>TP</div>
        </div>
      </div>
    </div>
  );
}

export default function ExperimentDetail() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const [exp, setExp] = useState<ExperimentDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!experimentId) return;
    api.getExperiment(experimentId).then(setExp).catch((e) => setError(e.message));
  }, [experimentId]);

  if (error)
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="error-box">{error}</div>
        </div>
      </div>
    );

  if (!exp)
    return (
      <div>
        <Topbar />
        <div className="page">
          <div className="loading-row">
            <div className="spinner" />
            Loading experiment…
          </div>
        </div>
      </div>
    );

  return (
    <div>
      <Topbar />
      <div className="page">
        <Link to={`/projects/${exp.project_id}`} className="back-link">
          ← Back to project
        </Link>

        <div className="exp-header" style={{ marginBottom: 28, alignItems: "flex-start" }}>
          <div>
            <div className="page-title">
              Experiment {String(exp.sequence_number).padStart(2, "0")} — {exp.model}
            </div>
          </div>
          <span
            className={
              exp.status === "COMPLETED"
                ? "badge badge-completed"
                : exp.status === "FAILED"
                ? "badge badge-failed"
                : "badge badge-running"
            }
          >
            {exp.status}
          </span>
        </div>

        <div className="card" style={{ marginBottom: 18 }}>
          <div className="section-title">Hypothesis</div>
          <div style={{ lineHeight: 1.6 }}>{exp.hypothesis}</div>
          <hr className="divider" />
          <div className="section-title">Reasoning</div>
          <div className="muted" style={{ lineHeight: 1.6 }}>
            {exp.reasoning}
          </div>
          {exp.parent_experiment_id && (
            <>
              <hr className="divider" />
              <div className="stat-label">Branched From</div>
              <Link to={`/experiments/${exp.parent_experiment_id}`} className="muted" style={{ textDecoration: "underline" }}>
                {exp.parent_experiment_id}
              </Link>
            </>
          )}
        </div>

        {exp.failure_reason && <div className="error-box">Failed: {exp.failure_reason}</div>}

        {Object.keys(exp.metrics).length > 0 && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Metrics</div>
            <div className="stat-row" style={{ flexWrap: "wrap" }}>
              {Object.entries(exp.metrics).map(([k, v]) => (
                <div key={k}>
                  <div className="stat-label">{k.replace(/_/g, " ")}</div>
                  <div className="stat-value">{v.toFixed(4)}</div>
                </div>
              ))}
            </div>
            <hr className="divider" />
            <div className="stat-row">
              <div>
                <div className="stat-label">Training Time</div>
                <div className="stat-value small">
                  {exp.training_time_seconds != null ? `${exp.training_time_seconds.toFixed(2)}s` : "—"}
                </div>
              </div>
              <div>
                <div className="stat-label">Inference Latency</div>
                <div className="stat-value small">
                  {exp.inference_latency_ms != null ? `${exp.inference_latency_ms.toFixed(3)}ms` : "—"}
                </div>
              </div>
            </div>
          </div>
        )}

        {exp.diagnostics?.confusion_matrix && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Confusion Matrix &amp; Error Breakdown</div>
            <div style={{ display: "flex", gap: 32, flexWrap: "wrap", alignItems: "flex-start" }}>
              <ConfusionMatrixGrid matrix={exp.diagnostics.confusion_matrix} />
              {exp.diagnostics.class_report && (
                <div style={{ flex: 1, minWidth: 220 }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ color: "var(--text-faint)", textAlign: "left" }}>
                        <th style={{ paddingBottom: 8 }}>Class</th>
                        <th style={{ paddingBottom: 8 }}>Precision</th>
                        <th style={{ paddingBottom: 8 }}>Recall</th>
                        <th style={{ paddingBottom: 8 }}>F1</th>
                        <th style={{ paddingBottom: 8 }}>Support</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(exp.diagnostics.class_report).map(([cls, s]) => (
                        <tr key={cls} style={{ borderTop: "1px solid var(--border-soft)" }}>
                          <td style={{ padding: "8px 0", fontWeight: 600 }}>{cls}</td>
                          <td>{s.precision.toFixed(3)}</td>
                          <td>{s.recall.toFixed(3)}</td>
                          <td>{s.f1.toFixed(3)}</td>
                          <td>{s.support}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {exp.interpretation && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Interpretation</div>
            <div style={{ marginBottom: 14 }}>
              <div className="stat-label">Observation</div>
              <div style={{ lineHeight: 1.6 }}>{exp.interpretation.observation}</div>
            </div>
            <div style={{ marginBottom: 14 }}>
              <div className="stat-label">Interpretation</div>
              <div style={{ lineHeight: 1.6 }}>{exp.interpretation.interpretation}</div>
            </div>
            {exp.interpretation.error_analysis && (
              <div style={{ marginBottom: 14 }}>
                <div className="stat-label">Error Analysis</div>
                <div style={{ lineHeight: 1.6 }}>{exp.interpretation.error_analysis}</div>
              </div>
            )}
            <div style={{ marginBottom: 14 }}>
              <div className="stat-label">Hypothesis Outcome</div>
              <span className={`badge ${OUTCOME_COLOR[exp.interpretation.hypothesis_outcome] ?? ""}`}>
                {exp.interpretation.hypothesis_outcome}
              </span>
            </div>
            <div>
              <div className="stat-label">Recommended Next Step</div>
              <div style={{ lineHeight: 1.6 }}>{exp.interpretation.recommended_next_step}</div>
            </div>
          </div>
        )}

        {exp.diagnostics?.feature_importance && (
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="section-title">Top Feature Importance</div>
            {Object.entries(exp.diagnostics.feature_importance)
              .slice(0, 10)
              .map(([name, score]) => {
                const maxScore = Math.max(...Object.values(exp.diagnostics!.feature_importance!));
                const pct = maxScore > 0 ? (score / maxScore) * 100 : 0;
                return (
                  <div key={name} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
                      <span className="mono muted">{name}</span>
                      <span className="mono">{score.toFixed(4)}</span>
                    </div>
                    <div style={{ height: 6, background: "var(--surface-alt)", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: "var(--accent)", borderRadius: 4 }} />
                    </div>
                  </div>
                );
              })}
          </div>
        )}

        <div className="card">
          <div className="section-title">Experiment Specification</div>
          <pre className="json-view">{JSON.stringify(exp.experiment_spec, null, 2)}</pre>
        </div>
      </div>
    </div>
  );
}

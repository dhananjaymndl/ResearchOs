import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import Topbar from "../components/Topbar";

export default function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [primaryMetric, setPrimaryMetric] = useState("f1");
  const [budget, setBudget] = useState(5);
  const [file, setFile] = useState<File | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = name.trim() && objective.trim() && file && targetColumn.trim() && !submitting;

  async function handleSubmit() {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await api.createProject({
        name,
        objective,
        primary_metric: primaryMetric,
        experiment_budget: budget,
      });
      await api.uploadDataset(project.id, file, targetColumn);
      await api.startResearch(project.id);
      navigate(`/projects/${project.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Topbar />
      <div className="page" style={{ maxWidth: 640 }}>
        <a className="back-link" href="/">
          ← Back to dashboard
        </a>
        <div className="page-title" style={{ marginBottom: 24 }}>
          New Research Project
        </div>

        {error && <div className="error-box">{error}</div>}

        <div className="card">
          <div className="form-group">
            <label>Project Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Fraud Detection Optimization" />
          </div>

          <div className="form-group">
            <label>Research Objective</label>
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Improve F1 score while maintaining reasonable model complexity."
            />
          </div>

          <div className="form-group">
            <label>Dataset Upload (CSV)</label>
            <div className="file-input-wrap">
              <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
            <div className="form-hint">Phase 1 supports tabular binary classification, up to 500MB.</div>
          </div>

          <div className="form-group">
            <label>Target Column</label>
            <input
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              placeholder="e.g. churn, fraud, default"
            />
          </div>

          <div className="field-row">
            <div className="form-group">
              <label>Primary Metric</label>
              <select value={primaryMetric} onChange={(e) => setPrimaryMetric(e.target.value)}>
                <option value="f1">F1</option>
                <option value="roc_auc">ROC-AUC</option>
                <option value="precision">Precision</option>
                <option value="recall">Recall</option>
                <option value="accuracy">Accuracy</option>
              </select>
            </div>

            <div className="form-group">
              <label>Experiment Budget</label>
              <select value={budget} onChange={(e) => setBudget(Number(e.target.value))}>
                <option value={3}>3 experiments</option>
                <option value={5}>5 experiments</option>
                <option value={10}>10 experiments</option>
              </select>
            </div>
          </div>

          <button className="btn btn-block" disabled={!canSubmit} onClick={handleSubmit}>
            {submitting ? "Starting…" : "Start Research"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import Topbar from "../components/Topbar";

function parseCsvPreview(text: string, maxRows = 5): { columns: string[]; rows: string[][] } {
  const lines = text.split(/\r\n|\n/).filter((l) => l.length > 0);
  const splitLine = (line: string) => line.split(",").map((cell) => cell.trim());
  const columns = lines.length > 0 ? splitLine(lines[0]) : [];
  const rows = lines.slice(1, 1 + maxRows).map(splitLine);
  return { columns, rows };
}

export default function NewProject() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [objective, setObjective] = useState("");
  const [primaryMetric, setPrimaryMetric] = useState("f1");
  const [budget, setBudget] = useState(5);
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const MAX_SIZE_MB = 500;

  async function handleFileChange(selected: File | null) {
    setFile(selected);
    setColumns([]);
    setPreviewRows([]);
    setTargetColumn("");
    setFileError(null);
    if (!selected) return;

    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setFileError("Only CSV files are supported.");
      setFile(null);
      return;
    }
    if (selected.size > MAX_SIZE_MB * 1024 * 1024) {
      setFileError(`File exceeds the ${MAX_SIZE_MB}MB limit.`);
      setFile(null);
      return;
    }

    try {
      const headChunk = await selected.slice(0, 65536).text();
      const { columns: cols, rows } = parseCsvPreview(headChunk);
      if (cols.length === 0) {
        setFileError("Couldn't read any columns from this file.");
        return;
      }
      setColumns(cols);
      setPreviewRows(rows);
    } catch {
      setFileError("Couldn't read this file.");
    }
  }

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
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
              />
            </div>
            {fileError ? (
              <div className="form-hint form-hint-error">{fileError}</div>
            ) : (
              <div className="form-hint">Phase 1 supports tabular binary classification, up to {MAX_SIZE_MB}MB.</div>
            )}
          </div>

          {previewRows.length > 0 && (
            <div className="form-group">
              <label>Preview (first {previewRows.length} rows)</label>
              <div className="csv-preview">
                <table>
                  <thead>
                    <tr>
                      {columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="form-group">
            <label>Target Column</label>
            {columns.length > 0 ? (
              <select value={targetColumn} onChange={(e) => setTargetColumn(e.target.value)}>
                <option value="" disabled>
                  Select the column to predict…
                </option>
                {columns.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            ) : (
              <select value="" disabled>
                <option value="">Upload a dataset first…</option>
              </select>
            )}
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

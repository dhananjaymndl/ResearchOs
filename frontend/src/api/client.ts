const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export interface ProjectSummary {
  id: string;
  name: string;
  objective: string;
  status: string;
  dataset_filename: string | null;
  experiment_count: number;
  baseline_metric: number | null;
  best_metric: number | null;
  best_experiment_id: string | null;
  primary_metric: string;
  experiment_budget: number;
  created_at: string;
}

export interface DatasetProfile {
  task: string;
  rows: number;
  columns: number;
  features: number;
  target: string;
  column_names: string[];
  numeric_columns: string[];
  categorical_columns: string[];
  target_distribution: {
    classes?: string[];
    distribution?: Record<string, number>;
    percentages?: Record<string, number>;
    minority_percentage?: number;
  };
  warnings: string[];
}

export interface ResearchEvent {
  id: string;
  experiment_id: string | null;
  event_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ExperimentDetail {
  id: string;
  project_id: string;
  parent_experiment_id: string | null;
  sequence_number: number;
  hypothesis: string;
  reasoning: string;
  model: string;
  status: string;
  failure_reason: string | null;
  experiment_spec: Record<string, unknown>;
  metrics: Record<string, number>;
  evaluation: Record<string, unknown>;
  diagnostics: {
    confusion_matrix: number[][] | null;
    class_report: Record<string, { precision: number; recall: number; f1: number; support: number }> | null;
    feature_importance: Record<string, number> | null;
  } | null;
  training_time_seconds: number | null;
  inference_latency_ms: number | null;
  artifacts: { type: string; storage_path: string }[];
  interpretation: {
    observation: string;
    interpretation: string;
    error_analysis: string;
    hypothesis_outcome: string;
    recommended_next_step: string;
  } | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export const api = {
  listProjects: () => request<ProjectSummary[]>("/projects"),
  getProject: (id: string) => request<ProjectSummary>(`/projects/${id}`),
  createProject: (payload: {
    name: string;
    objective: string;
    primary_metric: string;
    experiment_budget: number;
  }) =>
    request<ProjectSummary>("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: string) => request(`/projects/${id}`, { method: "DELETE" }),

  uploadDataset: (projectId: string, file: File, targetColumn: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("target_column", targetColumn);
    return request<{ dataset_id: string; profile: DatasetProfile }>(
      `/projects/${projectId}/dataset`,
      { method: "POST", body: form }
    );
  },
  getDatasetProfile: (projectId: string) =>
    request<DatasetProfile>(`/projects/${projectId}/dataset/profile`),

  startResearch: (projectId: string) =>
    request<{ started: boolean }>(`/projects/${projectId}/start`, { method: "POST" }),

  getEvents: (projectId: string) => request<ResearchEvent[]>(`/projects/${projectId}/events`),

  listExperiments: (projectId: string) =>
    request<ExperimentDetail[]>(`/projects/${projectId}/experiments`),
  getExperiment: (experimentId: string) =>
    request<ExperimentDetail>(`/experiments/${experimentId}`),

  getReport: (projectId: string) => request<Record<string, unknown>>(`/projects/${projectId}/report`),
};

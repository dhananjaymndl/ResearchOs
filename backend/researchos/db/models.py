import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from researchos.core.database import Base


def _uuid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("usr"))
    email: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("ds"))
    filename: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    row_count: Mapped[int] = mapped_column(default=0)
    column_count: Mapped[int] = mapped_column(default=0)
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("proj"))
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    objective: Mapped[str] = mapped_column(Text)
    dataset_id: Mapped[str | None] = mapped_column(String, ForeignKey("datasets.id"), nullable=True)
    target_column: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_metric: Mapped[str] = mapped_column(String, default="f1")
    experiment_budget: Mapped[int] = mapped_column(default=5)
    status: Mapped[str] = mapped_column(String, default="CREATED")
    best_experiment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    split_seed: Mapped[int] = mapped_column(default=42)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    dataset: Mapped["Dataset"] = relationship(lazy="joined")
    experiments: Mapped[list["Experiment"]] = relationship(
        back_populates="project", order_by="Experiment.sequence_number", cascade="all, delete-orphan"
    )


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("exp"))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("research_projects.id"))
    parent_experiment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sequence_number: Mapped[int] = mapped_column(default=0)
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String, default="")
    experiment_spec_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="PROPOSED")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    inference_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnostics_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped["ResearchProject"] = relationship(back_populates="experiments")
    metrics: Mapped[list["ExperimentMetric"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")
    artifacts: Mapped[list["ExperimentArtifact"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")
    interpretation: Mapped["ExperimentInterpretation | None"] = relationship(back_populates="experiment", uselist=False, cascade="all, delete-orphan")

    def metrics_dict(self) -> dict[str, float]:
        return {m.metric_name: m.metric_value for m in self.metrics}


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("met"))
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id"))
    metric_name: Mapped[str] = mapped_column(String)
    metric_value: Mapped[float] = mapped_column(Float)

    experiment: Mapped["Experiment"] = relationship(back_populates="metrics")


class ExperimentArtifact(Base):
    __tablename__ = "experiment_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("art"))
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id"))
    artifact_type: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    experiment: Mapped["Experiment"] = relationship(back_populates="artifacts")


class ExperimentInterpretation(Base):
    __tablename__ = "experiment_interpretations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("interp"))
    experiment_id: Mapped[str] = mapped_column(String, ForeignKey("experiments.id"), unique=True)
    observation: Mapped[str] = mapped_column(Text, default="")
    interpretation: Mapped[str] = mapped_column(Text, default="")
    error_analysis: Mapped[str] = mapped_column(Text, default="")
    hypothesis_outcome: Mapped[str] = mapped_column(String, default="INCONCLUSIVE")
    recommended_next_step: Mapped[str] = mapped_column(Text, default="")

    experiment: Mapped["Experiment"] = relationship(back_populates="interpretation")


class ResearchEvent(Base):
    __tablename__ = "research_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: _uuid("evt"))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("research_projects.id"))
    experiment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

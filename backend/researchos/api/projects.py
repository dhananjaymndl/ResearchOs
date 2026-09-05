from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from researchos.api.schemas import CreateProjectRequest, ProjectSummary
from researchos.core.database import get_db
from researchos.db.models import ResearchProject

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_summary(project: ResearchProject) -> ProjectSummary:
    completed = [e for e in project.experiments if e.status == "COMPLETED"]
    baseline = completed[0] if completed else None
    best = None
    if project.best_experiment_id:
        best = next((e for e in project.experiments if e.id == project.best_experiment_id), None)

    return ProjectSummary(
        id=project.id,
        name=project.name,
        objective=project.objective,
        status=project.status,
        dataset_filename=project.dataset.filename if project.dataset else None,
        experiment_count=len(project.experiments),
        baseline_metric=baseline.metrics_dict().get(project.primary_metric) if baseline else None,
        best_metric=best.metrics_dict().get(project.primary_metric) if best else None,
        best_experiment_id=project.best_experiment_id,
        primary_metric=project.primary_metric,
        experiment_budget=project.experiment_budget,
        created_at=project.created_at,
    )


@router.post("", response_model=ProjectSummary)
def create_project(payload: CreateProjectRequest, db: Session = Depends(get_db)):
    project = ResearchProject(
        name=payload.name,
        objective=payload.objective,
        primary_metric=payload.primary_metric,
        experiment_budget=payload.experiment_budget,
        status="CREATED",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_summary(project)


@router.get("", response_model=list[ProjectSummary])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).all()
    return [_to_summary(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return _to_summary(project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
    return {"deleted": True}

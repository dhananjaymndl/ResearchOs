from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from researchos.core.database import get_db
from researchos.db.models import ResearchProject
from researchos.reports.generator import generate_report
from researchos.research.orchestrator import run_research

router = APIRouter(prefix="/projects", tags=["research"])


@router.post("/{project_id}/start")
def start_research(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.dataset_id is None or project.target_column is None:
        raise HTTPException(400, "Upload a dataset and select a target column before starting research.")
    if project.status in ("PROFILING", "BASELINE_RUNNING", "RESEARCHING"):
        raise HTTPException(400, "Research is already running for this project.")

    project.status = "PROFILING"
    db.commit()

    background_tasks.add_task(_run_research_sync, project_id)
    return {"started": True}


def _run_research_sync(project_id: str) -> None:
    import asyncio

    asyncio.run(run_research(project_id))


@router.post("/{project_id}/pause")
def pause_research(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.status != "RESEARCHING":
        raise HTTPException(400, "Project is not currently researching.")
    project.status = "PAUSED"
    db.commit()
    return {"paused": True}


@router.post("/{project_id}/resume")
def resume_research(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.status != "PAUSED":
        raise HTTPException(400, "Project is not paused.")
    project.status = "RESEARCHING"
    db.commit()
    background_tasks.add_task(_run_research_sync, project_id)
    return {"resumed": True}


@router.get("/{project_id}/best-experiment")
def get_best_experiment(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if not project.best_experiment_id:
        raise HTTPException(404, "No best experiment yet.")
    best = next((e for e in project.experiments if e.id == project.best_experiment_id), None)
    if best is None:
        raise HTTPException(404, "Best experiment not found.")
    return {
        "id": best.id,
        "sequence_number": best.sequence_number,
        "model": best.model_name,
        "hypothesis": best.hypothesis,
        "metrics": best.metrics_dict(),
    }


@router.get("/{project_id}/report")
def get_report(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return generate_report(project)

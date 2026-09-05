from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from researchos.core.database import get_db
from researchos.db.models import ResearchEvent, ResearchProject

router = APIRouter(prefix="/projects", tags=["events"])


@router.get("/{project_id}/events")
def list_events(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    events = (
        db.query(ResearchEvent)
        .filter(ResearchEvent.project_id == project_id)
        .order_by(ResearchEvent.created_at.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "experiment_id": e.experiment_id,
            "event_type": e.event_type,
            "message": e.message,
            "metadata": e.metadata_json,
            "created_at": e.created_at,
        }
        for e in events
    ]

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from researchos.core.config import settings
from researchos.core.database import get_db
from researchos.datasets.loader import load_dataset, store_uploaded_dataset
from researchos.datasets.profiler import profile_dataset
from researchos.db.models import Dataset, ResearchProject

router = APIRouter(prefix="/projects", tags=["dataset"])


@router.post("/{project_id}/dataset")
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    target_column: str = Form(...),
    db: Session = Depends(get_db),
):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported in Phase 1.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        content = await file.read()
        max_bytes = settings.max_dataset_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(400, f"Dataset exceeds the {settings.max_dataset_size_mb}MB Phase 1 limit.")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        stored = store_uploaded_dataset(tmp_path, file.filename)
    finally:
        tmp_path.unlink(missing_ok=True)

    df = load_dataset(stored["storage_path"])
    if target_column not in df.columns:
        raise HTTPException(400, f"Target column '{target_column}' not found in dataset columns: {list(df.columns)}")

    profile = profile_dataset(df, target_column)

    dataset = Dataset(
        id=stored["dataset_id"],
        filename=stored["filename"],
        storage_path=stored["storage_path"],
        checksum=stored["checksum"],
        row_count=stored["row_count"],
        column_count=stored["column_count"],
        profile_json=profile,
    )
    db.add(dataset)

    project.dataset_id = dataset.id
    project.target_column = target_column
    project.status = "DATASET_UPLOADED"
    db.commit()

    return {"dataset_id": dataset.id, "profile": profile}


@router.get("/{project_id}/dataset/profile")
def get_dataset_profile(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.dataset is None:
        raise HTTPException(404, "No dataset uploaded for this project yet.")
    return project.dataset.profile_json

import hashlib
import re
import shutil
import uuid
from pathlib import Path

import pandas as pd

from researchos.core.config import settings

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name  # strips any directory components / path traversal
    name = _SAFE_NAME_RE.sub("_", name)
    return name or "dataset.csv"


def compute_checksum(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def store_uploaded_dataset(source_path: Path, original_filename: str) -> dict:
    safe_name = sanitize_filename(original_filename)
    dataset_id = f"ds_{uuid.uuid4().hex[:20]}"
    dest_dir = settings.dataset_storage_dir / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name

    shutil.copyfile(source_path, dest_path)

    checksum = compute_checksum(dest_path)
    df = load_dataset(dest_path)

    return {
        "dataset_id": dataset_id,
        "filename": safe_name,
        "storage_path": str(dest_path),
        "checksum": checksum,
        "row_count": len(df),
        "column_count": len(df.columns),
    }


def load_dataset(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path)

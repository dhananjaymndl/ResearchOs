import pandas as pd


def profile_dataset(df: pd.DataFrame, target_column: str) -> dict:
    rows, cols = df.shape

    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    bool_cols = list(df.select_dtypes(include=["bool"]).columns)
    categorical_cols = [
        c for c in df.columns if c not in numeric_cols and c not in bool_cols
    ]

    missing_counts = df.isna().sum()
    missing_pct = (missing_counts / max(rows, 1) * 100).round(2)

    duplicate_rows = int(df.duplicated().sum())

    constant_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    near_constant_cols = [
        c
        for c in df.columns
        if c not in constant_cols and df[c].nunique(dropna=True) / max(rows, 1) < 0.01
    ]
    high_cardinality_cols = [
        c
        for c in categorical_cols
        if df[c].nunique(dropna=True) / max(rows, 1) > 0.9
    ]

    warnings: list[str] = []

    target_info: dict = {}
    if target_column in df.columns:
        value_counts = df[target_column].value_counts(dropna=True)
        total = int(value_counts.sum())
        distribution = {str(k): int(v) for k, v in value_counts.items()}
        percentages = {
            str(k): round(v / total * 100, 4) if total else 0.0
            for k, v in value_counts.items()
        }
        minority_pct = min(percentages.values()) if percentages else 0.0
        target_info = {
            "classes": list(distribution.keys()),
            "distribution": distribution,
            "percentages": percentages,
            "minority_percentage": minority_pct,
            "n_classes": len(distribution),
        }
        if minority_pct < 5.0:
            warnings.append("Severe target class imbalance detected.")
        if len(distribution) != 2:
            warnings.append(
                f"Target column has {len(distribution)} classes; Phase 1 supports binary classification only."
            )
    else:
        warnings.append(f"Target column '{target_column}' not found in dataset.")

    for c in df.columns:
        if missing_pct.get(c, 0) > 30:
            warnings.append(f"Column '{c}' has excessive missing values ({missing_pct[c]}%).")

    if constant_cols:
        warnings.append(f"Constant columns detected: {', '.join(constant_cols)}.")

    if duplicate_rows > 0:
        warnings.append(f"{duplicate_rows} duplicate rows detected.")

    for c in high_cardinality_cols:
        warnings.append(f"Column '{c}' appears to be a high-cardinality identifier-like column.")

    profile = {
        "task": "binary_classification",
        "rows": rows,
        "columns": cols,
        "features": cols - (1 if target_column in df.columns else 0),
        "target": target_column,
        "column_names": list(df.columns),
        "numeric_columns": [c for c in numeric_cols if c != target_column],
        "categorical_columns": [c for c in categorical_cols if c != target_column],
        "boolean_columns": [c for c in bool_cols if c != target_column],
        "missing_values": {c: int(missing_counts[c]) for c in df.columns},
        "missing_value_percentage": {c: float(missing_pct[c]) for c in df.columns},
        "duplicate_rows": duplicate_rows,
        "constant_columns": constant_cols,
        "near_constant_columns": near_constant_cols,
        "high_cardinality_columns": high_cardinality_cols,
        "target_distribution": target_info,
        "warnings": warnings,
    }
    return profile

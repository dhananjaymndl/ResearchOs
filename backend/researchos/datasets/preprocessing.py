import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_preprocessing_pipeline(
    numeric_columns: list[str],
    categorical_columns: list[str],
    scale_numeric: bool = True,
    encode_categorical: bool = True,
) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(numeric_steps)

    categorical_steps = [("imputer", SimpleImputer(strategy="most_frequent"))]
    if encode_categorical:
        categorical_steps.append(
            ("encoder", OneHotEncoder(handle_unknown="ignore"))
        )
    categorical_pipeline = Pipeline(categorical_steps)

    transformers = []
    if numeric_columns:
        transformers.append(("numeric", numeric_pipeline, numeric_columns))
    if categorical_columns:
        transformers.append(("categorical", categorical_pipeline, categorical_columns))

    return ColumnTransformer(transformers=transformers, remainder="drop")


def encode_target(series: pd.Series) -> pd.Series:
    """Map the target column to {0, 1} deterministically (sorted class order)."""
    classes = sorted(series.dropna().unique().tolist(), key=str)
    mapping = {cls: idx for idx, cls in enumerate(classes)}
    return series.map(mapping)

import pandas as pd
from sklearn.model_selection import train_test_split


def split_dataset(
    df: pd.DataFrame,
    target_column: str,
    train_ratio: float = 0.8,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_df, val_df = train_test_split(
        df,
        train_size=train_ratio,
        random_state=seed,
        stratify=df[target_column],
    )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)

from pathlib import Path

import pandas as pd


class DatasetProfiler:
    """Profile datasets and return structured metadata."""

    def profile_csv(self, file_path: str) -> dict:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {file_path}"
            )

        if path.suffix.lower() != ".csv":
            raise ValueError(
                "DatasetProfiler currently supports CSV files only."
            )

        dataframe = pd.read_csv(path)

        return self.profile_dataframe(dataframe)

    def profile_dataframe(
        self,
        dataframe: pd.DataFrame,
    ) -> dict:
        """Profile an existing pandas DataFrame."""

        columns = []

        for column in dataframe.columns:
            series = dataframe[column]

            columns.append(
                {
                    "name": column,
                    "dtype": str(series.dtype),
                    "row_count": int(len(series)),
                    "null_count": int(series.isna().sum()),
                    "null_percentage": round(
                        float(series.isna().mean() * 100),
                        2,
                    ),
                    "unique_count": int(
                        series.nunique(dropna=True)
                    ),
                    "duplicate_count": int(
                        series.duplicated().sum()
                    ),
                }
            )

        return {
            "row_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
            "columns": columns,
        }
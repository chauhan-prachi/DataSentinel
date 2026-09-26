from pathlib import Path
import pandas as pd


class DatasetProfiler:
    """Profile datasets and return structured metadata."""

    def profile_csv(self, file_path: str) -> dict:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        if path.suffix.lower() != ".csv":
            raise ValueError("DatasetProfiler currently supports CSV files only.")

        dataframe = pd.read_csv(path)
        return self.profile_dataframe(dataframe)

    def profile_dataframe(self, dataframe: pd.DataFrame) -> dict:
        """Profile an existing pandas DataFrame."""

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError("dataframe must be a pandas DataFrame.")

        columns = []
        for column in dataframe.columns:
            series = dataframe[column]

            null_count = int(series.isna().sum())
            null_percentage = round(float(series.isna().mean() * 100), 2)
            unique_count = self._safe_unique_count(series)
            duplicate_count = self._safe_duplicate_count(series)

            columns.append({
                "name": str(column),
                "dtype": str(series.dtype),
                "row_count": int(len(series)),
                "null_count": null_count,
                "null_percentage": null_percentage,
                "unique_count": unique_count,
                "duplicate_count": duplicate_count,
            })

        return {
            "row_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
            "columns": columns,
        }

    @staticmethod
    def _contains_complex_values(series: pd.Series) -> bool:
        """Return True when a series contains nested values."""
        for value in series:
            if isinstance(value, (dict, list, tuple, set)):
                return True
        return False

    @classmethod
    def _safe_unique_count(cls, series: pd.Series) -> int:
        """Return the number of unique values safely."""
        if cls._contains_complex_values(series):
            values = []
            for value in series.dropna():
                try:
                    values.append(repr(value))
                except Exception:
                    values.append(str(type(value)))
            return int(len(set(values)))

        try:
            return int(series.nunique(dropna=True))
        except TypeError:
            values = []
            for value in series.dropna():
                try:
                    values.append(repr(value))
                except Exception:
                    values.append(str(type(value)))
            return int(len(set(values)))

    @classmethod
    def _safe_duplicate_count(cls, series: pd.Series) -> int:
        """Count duplicate values safely."""
        if cls._contains_complex_values(series):
            values = []
            for value in series:
                if pd.isna(value) and not isinstance(value, (dict, list, tuple, set)):
                    values.append("__DATASENTINEL_NULL__")
                    continue
                try:
                    values.append(repr(value))
                except Exception:
                    values.append(str(type(value)))

            duplicate_flags = pd.Series(values).duplicated()
            return int(duplicate_flags.sum())

        try:
            return int(series.duplicated().sum())
        except TypeError:
            values = []
            for value in series:
                try:
                    values.append(repr(value))
                except Exception:
                    values.append(str(type(value)))
            duplicate_flags = pd.Series(values).duplicated()
            return int(duplicate_flags.sum())

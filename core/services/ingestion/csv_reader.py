from pathlib import Path

import pandas as pd

from .base import DataSourceReader


class CSVReader(DataSourceReader):
    """Read CSV files into pandas DataFrames."""

    def read(self, source: str) -> pd.DataFrame:
        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {source}"
            )

        if not path.is_file():
            raise ValueError(
                f"CSV source is not a file: {source}"
            )

        if path.suffix.lower() != ".csv":
            raise ValueError(
                "CSVReader only supports .csv files."
            )

        return pd.read_csv(path)
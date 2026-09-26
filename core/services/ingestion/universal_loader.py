from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .csv_reader import CSVReader


class UniversalLoader:
    SUPPORTED_FORMATS = {
        ".csv": "CSV",
        ".json": "JSON",
        ".xlsx": "EXCEL",
        ".xls": "EXCEL",
        ".parquet": "PARQUET",
        ".tsv": "TSV",
        ".xml": "XML",
    }

    def __init__(self):
        self.csv_reader = CSVReader()

    def read(
        self,
        source: str | Path,
        file_format: str | None = None,
    ) -> pd.DataFrame:
        path = Path(source)

        self._validate_file(path)

        detected_format = self._detect_format(
            path,
            file_format,
        )

        if detected_format == "CSV":
            return self.csv_reader.read(str(path))

        if detected_format == "JSON":
            return self._read_json(path)

        if detected_format == "EXCEL":
            return self._read_excel(path)

        if detected_format == "PARQUET":
            return self._read_parquet(path)

        if detected_format == "TSV":
            return self._read_tsv(path)

        if detected_format == "XML":
            return self._read_xml(path)

        raise ValueError(
            f"Unsupported dataset format: {detected_format}"
        )

    @classmethod
    def _detect_format(
        cls,
        path: Path,
        file_format: str | None = None,
    ) -> str:
        if file_format:
            normalized = file_format.upper().strip()

            aliases = {
                "XLS": "EXCEL",
                "XLSX": "EXCEL",
                "EXCEL": "EXCEL",
                "PARQUET": "PARQUET",
                "CSV": "CSV",
                "JSON": "JSON",
                "TSV": "TSV",
                "XML": "XML",
            }

            if normalized not in aliases:
                raise ValueError(
                    f"Unsupported dataset format: {file_format}"
                )

            return aliases[normalized]

        suffix = path.suffix.lower()

        if suffix not in cls.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported dataset file extension: {suffix or 'none'}"
            )

        return cls.SUPPORTED_FORMATS[suffix]

    @staticmethod
    def _validate_file(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Dataset source is not a file: {path}"
            )

    @staticmethod
    def _read_json(path: Path) -> pd.DataFrame:
        try:
            dataframe = pd.read_json(path)

            if not dataframe.empty or dataframe.shape[1] > 0:
                return dataframe

        except (ValueError, TypeError):
            pass

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if isinstance(data, list):
                return pd.json_normalize(data)

            if isinstance(data, dict):
                return pd.json_normalize(data)

            raise ValueError(
                "JSON dataset must contain an object or array."
            )

        except Exception as exc:
            raise ValueError(
                f"Unable to read JSON dataset: {path}"
            ) from exc

    @staticmethod
    def _read_excel(path: Path) -> pd.DataFrame:
        try:
            return pd.read_excel(
                path,
                engine="openpyxl",
            )
        except Exception as exc:
            raise ValueError(
                f"Unable to read Excel dataset: {path}"
            ) from exc

    @staticmethod
    def _read_parquet(path: Path) -> pd.DataFrame:
        try:
            return pd.read_parquet(path)
        except Exception as exc:
            raise ValueError(
                f"Unable to read Parquet dataset: {path}"
            ) from exc

    @staticmethod
    def _read_tsv(path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(
                path,
                sep="\t",
            )
        except Exception as exc:
            raise ValueError(
                f"Unable to read TSV dataset: {path}"
            ) from exc

    @staticmethod
    def _read_xml(path: Path) -> pd.DataFrame:
        try:
            return pd.read_xml(path)
        except Exception as exc:
            raise ValueError(
                f"Unable to read XML dataset: {path}"
            ) from exc
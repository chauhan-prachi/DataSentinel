from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .checks import CheckResult, QualityChecks
from .profiler import DatasetProfiler
from .rule_suggester import RuleSuggester


class QualityEngine:

    def __init__(self):
        self.profiler = DatasetProfiler()
        self.rule_suggester = RuleSuggester()

    def run_csv_checks(
        self,
        file_path: str,
        check_config: list[dict],
    ) -> dict:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {file_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Dataset path is not a file: {file_path}"
            )

        if path.suffix.lower() != ".csv":
            raise ValueError(
                "QualityEngine currently supports CSV files only."
            )

        try:
            dataframe = pd.read_csv(path)
        except Exception as exc:
            raise ValueError(
                f"Unable to read CSV dataset: {exc}"
            ) from exc

        return self.run_dataframe_checks(
            dataframe=dataframe,
            dataset_name=str(path),
            check_config=check_config,
        )

    def run_dataframe_checks(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str = "dataset",
        check_config: list[dict] | None = None,
    ) -> dict:

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "dataframe must be a pandas DataFrame."
            )

        schema = self._detect_schema(dataframe)

        automatic = check_config is None

        if automatic:
            suggestions = self.rule_suggester.suggest(schema)

            check_config = [
                {
                    "check": suggestion["rule"],
                    "column": suggestion["column"],
                    "confidence": suggestion["confidence"],
                    "reason": suggestion["reason"],
                }
                for suggestion in suggestions
            ]
        else:
            suggestions = []

            if not isinstance(check_config, list):
                raise TypeError(
                    "check_config must be a list of dictionaries."
                )

        result = self._run_dataframe_checks(
            dataframe=dataframe,
            dataset_name=dataset_name,
            check_config=check_config,
        )

        result["schema"] = schema
        result["suggestions"] = suggestions
        result["automatic"] = automatic

        return result

    def _run_dataframe_checks(
        self,
        dataframe: pd.DataFrame,
        dataset_name: str,
        check_config: list[dict],
    ) -> dict:

        profile = self.profiler.profile_dataframe(dataframe)

        results: list[CheckResult] = []

        for config in check_config:

            if not isinstance(config, dict):
                raise ValueError(
                    "Each quality check configuration "
                    "must be a dictionary."
                )

            check_type = config.get("check")

            if not check_type:
                raise ValueError(
                    "Quality check configuration "
                    "is missing 'check'."
                )

            column = config.get("column")

            result = self._run_check(
                dataframe=dataframe,
                check_type=check_type,
                column=column,
                config=config,
            )

            results.append(result)

        return {
            "dataset": dataset_name,
            "profile": profile,
            "checks": [
                asdict(result)
                for result in results
            ],
            "summary": self._build_summary(results),
        }

    def _detect_schema(
        self,
        dataframe: pd.DataFrame,
    ):
        from ..schema.detector import SchemaDetector

        detector = SchemaDetector()

        return detector.detect(dataframe)

    def _run_check(
        self,
        dataframe: pd.DataFrame,
        check_type: str,
        column: str | None,
        config: dict,
    ):

        if check_type == "NOT_NULL":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.not_null(
                dataframe,
                column,
            )

        if check_type == "UNIQUE":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.unique(
                dataframe,
                column,
            )

        if check_type == "VALID_EMAIL":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.valid_email(
                dataframe,
                column,
            )

        if check_type == "NUMERIC_VALIDITY":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.numeric_validity(
                dataframe,
                column,
            )

        if check_type == "VALID_DATE":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.valid_date(
                dataframe,
                column,
            )

        if check_type == "RANGE":
            self._require_column(
                dataframe,
                column,
                check_type,
            )

            return QualityChecks.range_check(
                dataframe,
                column,
                minimum=config.get("minimum"),
                maximum=config.get("maximum"),
            )

        if check_type == "DUPLICATE":
            return QualityChecks.duplicate_rows(
                dataframe
            )

        raise ValueError(
            f"Unsupported quality check: {check_type}"
        )

    @staticmethod
    def _require_column(
        dataframe: pd.DataFrame,
        column: str | None,
        check_type: str,
    ):
        if not column:
            raise ValueError(
                f"{check_type} check requires a column."
            )

        if column not in dataframe.columns:
            raise ValueError(
                f"{check_type} check references "
                f"unknown column '{column}'."
            )

    @staticmethod
    def _build_summary(
        results: list[CheckResult],
    ) -> dict:

        total_checks = len(results)

        passed_checks = sum(
            1
            for result in results
            if result.passed
        )

        failed_checks = (
            total_checks - passed_checks
        )

        quality_score = (
            round(
                (passed_checks / total_checks) * 100,
                2,
            )
            if total_checks
            else 0
        )

        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "quality_score": quality_score,
        }
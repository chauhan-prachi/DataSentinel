from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .checks import CheckResult, QualityChecks
from .profiler import DatasetProfiler
from .rule_suggester import RuleSuggester


class QualityEngine:
    """Orchestrates profiling and quality checks for datasets."""

    def __init__(self):
        self.profiler = DatasetProfiler()
        self.rule_suggester = RuleSuggester()

    def run_csv_checks(
        self,
        file_path: str,
        check_config: list[dict],
    ) -> dict:
        """
        Run explicitly configured quality checks
        on a local CSV file.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Dataset not found: {file_path}"
            )

        if path.suffix.lower() != ".csv":
            raise ValueError(
                "QualityEngine currently supports CSV files only."
            )

        dataframe = pd.read_csv(path)

        return self._run_dataframe_checks(
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
        """
        Run quality checks against a DataFrame.

        If check_config is None, quality rules are generated
        automatically from the detected schema.
        """

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "dataframe must be a pandas DataFrame."
            )

        # Remember whether rules were generated automatically.
        automatic = check_config is None

        # Detect the schema for every dataset.
        schema = self._detect_schema(dataframe)

        if automatic:
            # Generate quality rules from the detected schema.
            suggestions = self.rule_suggester.suggest(
                schema
            )

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
            # Explicit/manual rules were supplied.
            suggestions = []

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
        """Execute a list of quality checks against a DataFrame."""

        profile = self.profiler.profile_dataframe(
            dataframe
        )

        results: list[CheckResult] = []

        for config in check_config:
            check_type = config["check"]
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
    ) -> list[dict]:
        """Detect semantic types for all dataset columns."""

        from ..schema.detector import SchemaDetector

        detector = SchemaDetector()

        return detector.detect(dataframe)

    def _run_check(
        self,
        dataframe: pd.DataFrame,
        check_type: str,
        column: str | None,
        config: dict,
    ) -> CheckResult:

        if check_type == "NOT_NULL":
            return QualityChecks.not_null(
                dataframe,
                column,
            )

        if check_type == "UNIQUE":
            return QualityChecks.unique(
                dataframe,
                column,
            )

        if check_type == "VALID_EMAIL":
            return QualityChecks.valid_email(
                dataframe,
                column,
            )

        if check_type == "NUMERIC_VALIDITY":
            return QualityChecks.numeric_validity(
                dataframe,
                column,
            )

        if check_type == "VALID_DATE":
            return QualityChecks.valid_date(
                dataframe,
                column,
            )

        if check_type == "RANGE":
            return QualityChecks.range_check(
                dataframe,
                column,
                minimum=config.get("minimum"),
                maximum=config.get("maximum"),
            )

        if check_type == "DUPLICATE":
            return QualityChecks.duplicate_rows(
                dataframe,
            )

        raise ValueError(
            f"Unsupported quality check: {check_type}"
        )

    @staticmethod
    def _build_summary(
        results: list[CheckResult],
    ) -> dict:
        """Build aggregate quality metrics."""

        total_checks = len(results)

        passed_checks = sum(
            1
            for result in results
            if result.passed
        )

        failed_checks = (
            total_checks - passed_checks
        )

        score = (
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
            "quality_score": score,
        }
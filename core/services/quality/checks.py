import re

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class CheckResult:
    """Result returned by a single quality check."""

    check_name: str
    passed: bool
    rows_checked: int
    rows_passed: int
    rows_failed: int
    details: dict[str, Any]


class QualityChecks:
    """Collection of reusable data-quality checks."""

    @staticmethod
    def _missing_column_result(
        check_name: str,
        column: str,
    ) -> CheckResult:
        """Return a consistent result when a column does not exist."""

        return CheckResult(
            check_name=check_name,
            passed=False,
            rows_checked=0,
            rows_passed=0,
            rows_failed=0,
            details={
                "error": f"Column '{column}' does not exist.",
            },
        )

    @staticmethod
    def not_null(
        dataframe: pd.DataFrame,
        column: str,
    ) -> CheckResult:
        """Check whether a column contains null values."""

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "NOT_NULL",
                column,
            )

        null_mask = dataframe[column].isna()

        rows_checked = len(dataframe)
        rows_failed = int(null_mask.sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="NOT_NULL",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "null_count": rows_failed,
                "null_percentage": round(
                    (
                        rows_failed / rows_checked * 100
                    )
                    if rows_checked
                    else 0,
                    2,
                ),
            },
        )

    @staticmethod
    def unique(
        dataframe: pd.DataFrame,
        column: str,
    ) -> CheckResult:
        """Check whether all values in a column are unique."""

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "UNIQUE",
                column,
            )

        duplicated_mask = dataframe[column].duplicated(
            keep=False,
        )

        rows_checked = len(dataframe)
        rows_failed = int(duplicated_mask.sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="UNIQUE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "duplicate_rows": rows_failed,
            },
        )

    @staticmethod
    def valid_email(
        dataframe: pd.DataFrame,
        column: str,
    ) -> CheckResult:
        """
        Check whether non-null values are valid email addresses.

        Null values are reported separately and are not counted
        as malformed email addresses. Missing values should be
        handled by the NOT_NULL check.
        """

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "VALID_EMAIL",
                column,
            )

        email_pattern = re.compile(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        )

        values = dataframe[column]

        non_null_mask = values.notna()

        non_null_values = values[non_null_mask]

        valid_mask = non_null_values.astype(str).str.strip().str.match(
            email_pattern,
            na=False,
        )

        invalid_email_count = int(
            (~valid_mask).sum()
        )

        null_count = int(
            values.isna().sum()
        )

        rows_checked = len(dataframe)

        rows_failed = invalid_email_count
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="VALID_EMAIL",
            passed=invalid_email_count == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "invalid_email_count": invalid_email_count,
                "null_count": null_count,
            },
        )

    @staticmethod
    def numeric_validity(
        dataframe: pd.DataFrame,
        column: str,
    ) -> CheckResult:
        """
        Check whether non-null values can be interpreted as numbers.

        Null values are reported separately and are handled by
        the NOT_NULL check.
        """

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "NUMERIC_VALIDITY",
                column,
            )

        values = dataframe[column]

        numeric_values = pd.to_numeric(
            values,
            errors="coerce",
        )

        null_mask = values.isna()

        invalid_mask = (
            values.notna()
            & numeric_values.isna()
        )

        rows_checked = len(dataframe)

        rows_failed = int(
            invalid_mask.sum()
        )

        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="NUMERIC_VALIDITY",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "invalid_numeric_count": rows_failed,
                "null_count": int(
                    null_mask.sum()
                ),
            },
        )

    @staticmethod
    def valid_date(
        dataframe: pd.DataFrame,
        column: str,
    ) -> CheckResult:
        """
        Check whether non-null values can be interpreted as dates.

        Null values are reported separately and are handled by
        the NOT_NULL check.
        """

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "VALID_DATE",
                column,
            )

        values = dataframe[column]

        non_null_mask = values.notna()

        non_null_values = values[non_null_mask]

        converted = pd.to_datetime(
            non_null_values,
            errors="coerce",
            format="mixed",
        )

        invalid_mask = converted.isna()

        invalid_date_count = int(
            invalid_mask.sum()
        )

        null_count = int(
            values.isna().sum()
        )

        rows_checked = len(dataframe)

        rows_failed = invalid_date_count
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="VALID_DATE",
            passed=invalid_date_count == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "invalid_date_count": invalid_date_count,
                "null_count": null_count,
            },
        )

    @staticmethod
    def range_check(
        dataframe: pd.DataFrame,
        column: str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> CheckResult:
        """Check whether numeric values fall within a specified range."""

        if column not in dataframe.columns:
            return QualityChecks._missing_column_result(
                "RANGE",
                column,
            )

        values = dataframe[column]

        numeric_values = pd.to_numeric(
            values,
            errors="coerce",
        )

        valid_mask = numeric_values.notna()

        if minimum is not None:
            valid_mask &= numeric_values >= minimum

        if maximum is not None:
            valid_mask &= numeric_values <= maximum

        rows_checked = len(dataframe)

        rows_passed = int(
            valid_mask.sum()
        )

        rows_failed = rows_checked - rows_passed

        return CheckResult(
            check_name="RANGE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "minimum": minimum,
                "maximum": maximum,
                "invalid_range_count": rows_failed,
            },
        )

    @staticmethod
    def duplicate_rows(
        dataframe: pd.DataFrame,
    ) -> CheckResult:
        """Check whether the dataset contains duplicate rows."""

        duplicate_mask = dataframe.duplicated(
            keep=False,
        )

        rows_checked = len(dataframe)

        rows_failed = int(
            duplicate_mask.sum()
        )

        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="DUPLICATE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "duplicate_rows": rows_failed,
            },
        )
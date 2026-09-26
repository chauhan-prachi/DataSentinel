from dataclasses import dataclass
from typing import Any
import re
import pandas as pd


@dataclass
class CheckResult:
    check_name: str
    passed: bool
    rows_checked: int
    rows_passed: int
    rows_failed: int
    details: dict[str, Any]


class QualityChecks:

    @staticmethod
    def _missing_column_result(
        check_name: str,
        column: str,
    ) -> CheckResult:
        return CheckResult(
            check_name=check_name,
            passed=False,
            rows_checked=0,
            rows_passed=0,
            rows_failed=0,
            details={
                "column": column,
                "error": f"Column '{column}' does not exist.",
            },
        )

    @staticmethod
    def not_null(dataframe: pd.DataFrame, column: str) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("NOT_NULL", column)

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
                "null_percentage": (
                    round((rows_failed / rows_checked) * 100, 2)
                    if rows_checked else 0
                ),
            },
        )

    @staticmethod
    def unique(dataframe: pd.DataFrame, column: str) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("UNIQUE", column)

        duplicated_mask = dataframe[column].duplicated(keep=False)
        rows_checked = len(dataframe)
        rows_failed = int(duplicated_mask.sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="UNIQUE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={"column": column, "duplicate_rows": rows_failed},
        )

    @staticmethod
    def valid_email(dataframe: pd.DataFrame, column: str) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("VALID_EMAIL", column)

        email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        values = dataframe[column]
        non_null_values = values.dropna()

        valid_mask = (
            non_null_values.astype(str).str.strip().str.match(email_pattern, na=False)
        )

        rows_checked = len(non_null_values)
        rows_failed = int((~valid_mask).sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="VALID_EMAIL",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "invalid_email_count": rows_failed,
                "null_count": int(values.isna().sum()),
                "total_rows": len(dataframe),
            },
        )

    @staticmethod
    def numeric_validity(dataframe: pd.DataFrame, column: str) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("NUMERIC_VALIDITY", column)

        values = dataframe[column]
        non_null_values = values.dropna()
        numeric_values = pd.to_numeric(non_null_values, errors="coerce")
        invalid_mask = numeric_values.isna()

        rows_checked = len(non_null_values)
        rows_failed = int(invalid_mask.sum())
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
                "null_count": int(values.isna().sum()),
                "total_rows": len(dataframe),
            },
        )

    @staticmethod
    def valid_date(dataframe: pd.DataFrame, column: str) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("VALID_DATE", column)

        values = dataframe[column]
        non_null_values = values.dropna()
        converted = pd.to_datetime(non_null_values, errors="coerce", format="mixed")
        invalid_mask = converted.isna()

        rows_checked = len(non_null_values)
        rows_failed = int(invalid_mask.sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="VALID_DATE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={
                "column": column,
                "invalid_date_count": rows_failed,
                "null_count": int(values.isna().sum()),
                "total_rows": len(dataframe),
            },
        )

    @staticmethod
    def range_check(dataframe: pd.DataFrame, column: str, minimum=None, maximum=None) -> CheckResult:
        if column not in dataframe.columns:
            return QualityChecks._missing_column_result("RANGE", column)

        values = dataframe[column]
        non_null_values = values.dropna()
        numeric_values = pd.to_numeric(non_null_values, errors="coerce")
        valid_mask = numeric_values.notna()

        if minimum is not None:
            valid_mask &= numeric_values >= minimum
        if maximum is not None:
            valid_mask &= numeric_values <= maximum

        rows_checked = len(non_null_values)
        rows_passed = int(valid_mask.sum())
        rows_failed = rows_checked - rows_passed
        invalid_numeric_count = int(numeric_values.isna().sum())

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
                "invalid_numeric_count": invalid_numeric_count,
                "null_count": int(values.isna().sum()),
                "total_rows": len(dataframe),
            },
        )

    @staticmethod
    def duplicate_rows(dataframe: pd.DataFrame) -> CheckResult:
        duplicate_mask = dataframe.duplicated(keep=False)
        rows_checked = len(dataframe)
        rows_failed = int(duplicate_mask.sum())
        rows_passed = rows_checked - rows_failed

        return CheckResult(
            check_name="DUPLICATE",
            passed=rows_failed == 0,
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            details={"duplicate_rows": rows_failed},
        )

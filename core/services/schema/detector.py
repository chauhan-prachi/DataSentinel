from __future__ import annotations

import re

import pandas as pd


class SchemaDetector:
    """Detect semantic column types using names and values."""

    EMAIL_PATTERN = re.compile(
        r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
    )

    EMAIL_NAME_KEYWORDS = (
        "email",
        "e_mail",
        "email_address",
        "mail_address",
    )

    DATETIME_NAME_KEYWORDS = (
        "date",
        "time",
        "datetime",
        "timestamp",
        "created_at",
        "updated_at",
        "deleted_at",
        "modified_at",
        "signup_date",
        "birth_date",
        "dob",
        "order_date",
        "start_date",
        "end_date",
    )

    IDENTIFIER_NAME_KEYWORDS = (
        "id",
        "identifier",
        "uuid",
        "key",
        "code",
    )

    def detect(
        self,
        dataframe: pd.DataFrame,
    ) -> list[dict]:
        """Detect the semantic type of every column."""

        results = []

        for column in dataframe.columns:
            series = dataframe[column]

            results.append(
                self._detect_column(
                    column_name=str(column),
                    series=series,
                )
            )

        return results

    def _detect_column(
        self,
        column_name: str,
        series: pd.Series,
    ) -> dict:
        non_null = series.dropna()

        if non_null.empty:
            return {
                "column": column_name,
                "detected_type": "UNKNOWN",
                "confidence": 0.0,
                "reason": (
                    "Column contains no non-null values."
                ),
            }

        if pd.api.types.is_bool_dtype(series):
            return self._result(
                column_name,
                "BOOLEAN",
                1.0,
                "Column contains boolean values.",
            )

        if pd.api.types.is_datetime64_any_dtype(series):
            return self._result(
                column_name,
                "DATETIME",
                1.0,
                "Column is already recognized as datetime.",
            )

        if pd.api.types.is_numeric_dtype(series):
            return self._detect_numeric(
                column_name,
                series,
            )

        if self._name_suggests_email(column_name):
            email_ratio = self._email_valid_ratio(non_null)

            return self._result(
                column_name,
                "EMAIL",
                self._confidence_from_ratio(
                    email_ratio,
                    minimum=0.50,
                ),
                (
                    "Column name suggests an email field; "
                    f"{email_ratio:.0%} of non-null values "
                    "match an email pattern."
                ),
            )

        if self._looks_like_email(non_null):
            email_ratio = self._email_valid_ratio(non_null)

            return self._result(
                column_name,
                "EMAIL",
                min(0.99, email_ratio),
                (
                    "Values match a common email address "
                    "pattern."
                ),
            )

        if self._name_suggests_datetime(column_name):
            date_ratio = self._datetime_valid_ratio(
                non_null
            )

            return self._result(
                column_name,
                "DATETIME",
                self._confidence_from_ratio(
                    date_ratio,
                    minimum=0.50,
                ),
                (
                    "Column name suggests a date/time field; "
                    f"{date_ratio:.0%} of non-null values "
                    "can be parsed as dates."
                ),
            )

        if self._looks_like_datetime(non_null):
            date_ratio = self._datetime_valid_ratio(
                non_null
            )

            return self._result(
                column_name,
                "DATETIME",
                min(0.99, date_ratio),
                (
                    "Values can be consistently parsed "
                    "as dates."
                ),
            )

        if self._looks_like_identifier(
            column_name,
            series,
        ):
            return self._result(
                column_name,
                "IDENTIFIER",
                0.90,
                (
                    "Column name and uniqueness suggest "
                    "an identifier."
                ),
            )

        if self._looks_categorical(series):
            return self._result(
                column_name,
                "CATEGORICAL",
                0.85,
                (
                    "Column contains a relatively small "
                    "number of repeated values."
                ),
            )

        return self._result(
            column_name,
            "STRING",
            0.75,
            "Column contains general textual values.",
        )

    def _detect_numeric(
        self,
        column_name: str,
        series: pd.Series,
    ) -> dict:
        if self._looks_like_identifier(
            column_name,
            series,
        ):
            return self._result(
                column_name,
                "IDENTIFIER",
                0.90,
                (
                    "Numeric column has identifier-like "
                    "naming and high uniqueness."
                ),
            )

        return self._result(
            column_name,
            "NUMERIC",
            0.99,
            "Column contains numeric values.",
        )

    def _name_suggests_email(
        self,
        column_name: str,
    ) -> bool:
        normalized = self._normalize_name(
            column_name
        )

        return any(
            keyword in normalized
            for keyword in self.EMAIL_NAME_KEYWORDS
        )

    def _name_suggests_datetime(
        self,
        column_name: str,
    ) -> bool:
        normalized = self._normalize_name(
            column_name
        )

        return any(
            keyword in normalized
            for keyword in self.DATETIME_NAME_KEYWORDS
        )

    def _normalize_name(
        self,
        column_name: str,
    ) -> str:
        return (
            column_name
            .lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )

    def _looks_like_email(
        self,
        series: pd.Series,
    ) -> bool:
        ratio = self._email_valid_ratio(series)

        return ratio >= 0.90

    def _email_valid_ratio(
        self,
        series: pd.Series,
    ) -> float:
        values = (
            series.astype(str)
            .str.strip()
        )

        if values.empty:
            return 0.0

        matches = values.apply(
            lambda value: bool(
                self.EMAIL_PATTERN.match(value)
            )
        )

        return float(matches.mean())

    def _looks_like_datetime(
        self,
        series: pd.Series,
    ) -> bool:
        ratio = self._datetime_valid_ratio(
            series
        )

        return ratio >= 0.90

    def _datetime_valid_ratio(
        self,
        series: pd.Series,
    ) -> float:
        values = (
            series.dropna()
            .astype(str)
            .str.strip()
        )

        if values.empty:
            return 0.0

        converted = pd.to_datetime(
            values,
            errors="coerce",
            format="mixed",
        )

        return float(
            converted.notna().mean()
        )

    def _looks_like_identifier(
        self,
        column_name: str,
        series: pd.Series,
    ) -> bool:
        normalized_name = (
            column_name
            .lower()
            .strip()
        )

        name_parts = re.split(
            r"[^a-zA-Z0-9]+",
            normalized_name,
        )

        name_suggests_identifier = any(
            part in self.IDENTIFIER_NAME_KEYWORDS
            for part in name_parts
        )

        if not name_suggests_identifier:
            return False

        non_null = series.dropna()

        if non_null.empty:
            return False

        uniqueness_ratio = (
            non_null.nunique()
            / len(non_null)
        )

        highly_unique = uniqueness_ratio >= 0.95

        return highly_unique

    def _looks_categorical(
        self,
        series: pd.Series,
    ) -> bool:
        non_null = series.dropna()

        if non_null.empty:
            return False

        unique_ratio = (
            non_null.nunique()
            / len(non_null)
        )

        return (
            len(non_null) >= 10
            and non_null.nunique() <= 50
            and unique_ratio <= 0.20
        )

    @staticmethod
    def _confidence_from_ratio(
        ratio: float,
        minimum: float,
    ) -> float:
        if ratio < minimum:
            return 0.0

        confidence = 0.70 + (
            (ratio - minimum)
            / (1.0 - minimum)
        ) * 0.29

        return round(
            min(0.99, confidence),
            2,
        )

    @staticmethod
    def _result(
        column: str,
        detected_type: str,
        confidence: float,
        reason: str,
    ) -> dict:
        return {
            "column": column,
            "detected_type": detected_type,
            "confidence": confidence,
            "reason": reason,
        }
from __future__ import annotations

from typing import Any

import pandas as pd


class AnomalyDetector:

    DEFAULT_ROW_COUNT_THRESHOLD = 0.30
    DEFAULT_NULL_RATE_THRESHOLD = 0.20
    DEFAULT_DISTRIBUTION_THRESHOLD = 0.50

    def detect(
        self,
        current_dataframe: pd.DataFrame,
        previous_statistics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        current_statistics = self.build_statistics(
            current_dataframe
        )

        if not previous_statistics:
            return {
                "has_anomalies": False,
                "anomalies": [],
                "summary": {
                    "total": 0,
                    "row_count": 0,
                    "null_rate": 0,
                    "value_distribution": 0,
                },
                "current_statistics": current_statistics,
            }

        anomalies = []

        row_count_anomaly = self._detect_row_count_anomaly(
            current_statistics,
            previous_statistics,
        )

        if row_count_anomaly:
            anomalies.append(row_count_anomaly)

        anomalies.extend(
            self._detect_null_rate_anomalies(
                current_statistics,
                previous_statistics,
            )
        )

        anomalies.extend(
            self._detect_distribution_anomalies(
                current_statistics,
                previous_statistics,
            )
        )

        summary = {
            "total": len(anomalies),
            "row_count": sum(
                1
                for anomaly in anomalies
                if anomaly["type"] == "ROW_COUNT"
            ),
            "null_rate": sum(
                1
                for anomaly in anomalies
                if anomaly["type"] == "NULL_RATE"
            ),
            "value_distribution": sum(
                1
                for anomaly in anomalies
                if anomaly["type"] == "VALUE_DISTRIBUTION"
            ),
        }

        return {
            "has_anomalies": bool(anomalies),
            "anomalies": anomalies,
            "summary": summary,
            "current_statistics": current_statistics,
        }

    def build_statistics(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:

        statistics = {
            "row_count": int(len(dataframe)),
            "columns": {},
        }

        for column in dataframe.columns:
            series = dataframe[column]

            column_statistics = {
                "dtype": str(series.dtype),
                "null_count": int(series.isna().sum()),
                "null_rate": round(
                    float(series.isna().mean()),
                    6,
                ),
            }

            if pd.api.types.is_numeric_dtype(series):
                numeric_series = pd.to_numeric(
                    series,
                    errors="coerce",
                ).dropna()

                column_statistics["type"] = "NUMERIC"

                if not numeric_series.empty:
                    column_statistics.update(
                        {
                            "mean": round(
                                float(numeric_series.mean()),
                                6,
                            ),
                            "std": round(
                                float(numeric_series.std()),
                                6,
                            )
                            if len(numeric_series) > 1
                            else 0.0,
                            "min": float(
                                numeric_series.min()
                            ),
                            "max": float(
                                numeric_series.max()
                            ),
                            "median": float(
                                numeric_series.median()
                            ),
                        }
                    )

            elif pd.api.types.is_bool_dtype(series):
                column_statistics["type"] = "BOOLEAN"

            elif pd.api.types.is_datetime64_any_dtype(series):
                column_statistics["type"] = "DATETIME"

            else:
                column_statistics["type"] = "OTHER"

                value_counts = (
                    series.dropna()
                    .astype(str)
                    .value_counts()
                    .head(20)
                )

                total_non_null = int(
                    series.notna().sum()
                )

                distribution = {}

                if total_non_null > 0:
                    for value, count in value_counts.items():
                        distribution[str(value)] = round(
                            float(count / total_non_null),
                            6,
                        )

                column_statistics["top_values"] = distribution

            statistics["columns"][str(column)] = (
                column_statistics
            )

        return statistics

    def _detect_row_count_anomaly(
        self,
        current_statistics: dict[str, Any],
        previous_statistics: dict[str, Any],
    ) -> dict[str, Any] | None:

        current_count = int(
            current_statistics.get("row_count", 0)
        )

        previous_count = int(
            previous_statistics.get("row_count", 0)
        )

        if previous_count <= 0:
            return None

        relative_change = abs(
            current_count - previous_count
        ) / previous_count

        if relative_change < self.DEFAULT_ROW_COUNT_THRESHOLD:
            return None

        direction = (
            "increase"
            if current_count > previous_count
            else "decrease"
        )

        return {
            "type": "ROW_COUNT",
            "severity": self._severity_from_change(
                relative_change
            ),
            "column": None,
            "metric": "row_count",
            "previous_value": previous_count,
            "current_value": current_count,
            "change_percentage": round(
                relative_change * 100,
                2,
            ),
            "direction": direction,
            "message": (
                f"Row count changed by "
                f"{relative_change * 100:.2f}% "
                f"from {previous_count} to "
                f"{current_count}."
            ),
        }

    def _detect_null_rate_anomalies(
        self,
        current_statistics: dict[str, Any],
        previous_statistics: dict[str, Any],
    ) -> list[dict[str, Any]]:

        anomalies = []

        current_columns = current_statistics.get(
            "columns",
            {},
        )

        previous_columns = previous_statistics.get(
            "columns",
            {},
        )

        common_columns = (
            set(current_columns.keys())
            & set(previous_columns.keys())
        )

        for column in sorted(common_columns):
            current_column = current_columns[column]
            previous_column = previous_columns[column]

            current_null_rate = float(
                current_column.get("null_rate", 0.0)
            )

            previous_null_rate = float(
                previous_column.get("null_rate", 0.0)
            )

            absolute_change = (
                current_null_rate
                - previous_null_rate
            )

            if (
                absolute_change
                < self.DEFAULT_NULL_RATE_THRESHOLD
            ):
                continue

            anomalies.append(
                {
                    "type": "NULL_RATE",
                    "severity": self._severity_from_change(
                        absolute_change
                    ),
                    "column": column,
                    "metric": "null_rate",
                    "previous_value": round(
                        previous_null_rate,
                        6,
                    ),
                    "current_value": round(
                        current_null_rate,
                        6,
                    ),
                    "change_percentage": round(
                        absolute_change * 100,
                        2,
                    ),
                    "direction": "increase",
                    "message": (
                        f"Null rate for '{column}' "
                        f"increased from "
                        f"{previous_null_rate * 100:.2f}% "
                        f"to "
                        f"{current_null_rate * 100:.2f}%."
                    ),
                }
            )

        return anomalies

    def _detect_distribution_anomalies(
        self,
        current_statistics: dict[str, Any],
        previous_statistics: dict[str, Any],
    ) -> list[dict[str, Any]]:

        anomalies = []

        current_columns = current_statistics.get(
            "columns",
            {},
        )

        previous_columns = previous_statistics.get(
            "columns",
            {},
        )

        common_columns = (
            set(current_columns.keys())
            & set(previous_columns.keys())
        )

        for column in sorted(common_columns):
            current_column = current_columns[column]
            previous_column = previous_columns[column]

            if (
                current_column.get("type") != "NUMERIC"
                or previous_column.get("type") != "NUMERIC"
            ):
                continue

            previous_mean = previous_column.get("mean")
            current_mean = current_column.get("mean")

            if (
                previous_mean is None
                or current_mean is None
            ):
                continue

            if previous_mean == 0:
                if current_mean == 0:
                    continue

                relative_change = 1.0
            else:
                relative_change = abs(
                    current_mean - previous_mean
                ) / abs(previous_mean)

            if (
                relative_change
                < self.DEFAULT_DISTRIBUTION_THRESHOLD
            ):
                continue

            direction = (
                "increase"
                if current_mean > previous_mean
                else "decrease"
            )

            anomalies.append(
                {
                    "type": "VALUE_DISTRIBUTION",
                    "severity": self._severity_from_change(
                        relative_change
                    ),
                    "column": column,
                    "metric": "mean",
                    "previous_value": round(
                        float(previous_mean),
                        6,
                    ),
                    "current_value": round(
                        float(current_mean),
                        6,
                    ),
                    "change_percentage": round(
                        relative_change * 100,
                        2,
                    ),
                    "direction": direction,
                    "message": (
                        f"Average value for '{column}' "
                        f"changed from "
                        f"{previous_mean:.2f} to "
                        f"{current_mean:.2f} "
                        f"({relative_change * 100:.2f}% change)."
                    ),
                }
            )

        return anomalies

    @staticmethod
    def _severity_from_change(
        relative_change: float,
    ) -> str:

        percentage = relative_change * 100

        if percentage >= 100:
            return "CRITICAL"

        if percentage >= 50:
            return "HIGH"

        if percentage >= 30:
            return "MEDIUM"

        return "LOW"
from __future__ import annotations

from typing import Any


class SchemaDriftDetector:
    """Compare dataset schemas between pipeline runs."""

    def compare(
        self,
        previous_schema: dict[str, Any] | None,
        current_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        previous_columns = self._normalize_schema(
            previous_schema
        )

        current_columns = self._normalize_schema(
            current_schema
        )

        previous_names = set(previous_columns.keys())
        current_names = set(current_columns.keys())

        added_columns = sorted(
            current_names - previous_names
        )

        removed_columns = sorted(
            previous_names - current_names
        )

        changed_columns = []

        for column in sorted(
            previous_names & current_names
        ):
            previous_type = previous_columns[column]
            current_type = current_columns[column]

            if previous_type != current_type:
                changed_columns.append(
                    {
                        "column": column,
                        "previous_type": previous_type,
                        "current_type": current_type,
                    }
                )

        has_drift = bool(
            added_columns
            or removed_columns
            or changed_columns
        )

        return {
            "has_drift": has_drift,
            "added_columns": added_columns,
            "removed_columns": removed_columns,
            "changed_columns": changed_columns,
            "summary": {
                "added": len(added_columns),
                "removed": len(removed_columns),
                "changed": len(changed_columns),
            },
        }

    @staticmethod
    def _normalize_schema(
        schema: dict[str, Any] | None,
    ) -> dict[str, str]:
        if not schema:
            return {}

        columns = schema.get("columns", [])

        normalized = {}

        for column in columns:
            if not isinstance(column, dict):
                continue

            name = column.get("name")

            if name is None:
                name = column.get("column")

            if name is None:
                continue

            dtype = column.get("dtype")

            if dtype is None:
                dtype = column.get("detected_type")

            if dtype is None:
                dtype = "UNKNOWN"

            normalized[str(name)] = str(dtype)

        return normalized
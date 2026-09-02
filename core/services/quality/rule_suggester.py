class RuleSuggester:
    """Suggest quality checks based on detected schema types."""

    def suggest(self, schema_results: list[dict]) -> list[dict]:
        suggestions = []

        for column in schema_results:
            column_name = column["column"]
            detected_type = column["detected_type"]
            confidence = column["confidence"]

            rules = self._rules_for_type(detected_type)

            for rule in rules:
                suggestions.append(
                    {
                        "column": column_name,
                        "rule": rule,
                        "confidence": confidence,
                        "reason": (
                            f"{rule} is recommended for "
                            f"{detected_type} columns."
                        ),
                    }
                )

        return suggestions

    def _rules_for_type(
        self,
        detected_type: str,
    ) -> list[str]:
        rules_by_type = {
            "IDENTIFIER": [
                "NOT_NULL",
                "UNIQUE",
            ],
            "EMAIL": [
                "NOT_NULL",
                "VALID_EMAIL",
            ],
            "NUMERIC": [
                "NOT_NULL",
                "NUMERIC_VALIDITY",
            ],
            "DATETIME": [
                "NOT_NULL",
                "VALID_DATE",
            ],
            "BOOLEAN": [
                "NOT_NULL",
            ],
            "CATEGORICAL": [
                "NOT_NULL",
            ],
            "STRING": [
                "NOT_NULL",
            ],
            "UNKNOWN": [],
        }

        return rules_by_type.get(
            detected_type,
            [],
        )
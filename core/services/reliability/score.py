from __future__ import annotations

from typing import Any


class ReliabilityScoreService:

    def calculate(
        self,
        pipeline_run,
    ) -> dict[str, Any]:

        if pipeline_run.status == "FAILED":
            return {
                "score": 0.0,
                "grade": "F",
                "status": "UNRELIABLE",
                "breakdown": {
                    "quality": 0.0,
                    "schema": 0.0,
                    "anomalies": 0.0,
                    "pipeline": 0.0,
                },
                "reasons": [
                    "Pipeline run failed."
                ],
            }

        quality_score = self._quality_score(
            pipeline_run.quality_score
        )

        schema_score = self._schema_score(
            pipeline_run.schema_changed
        )

        anomaly_score = self._anomaly_score(
            pipeline_run.anomalies_detected
        )

        pipeline_score = self._pipeline_score(
            pipeline_run.status
        )

        score = round(
            (
                quality_score * 0.50
                + schema_score * 0.20
                + anomaly_score * 0.20
                + pipeline_score * 0.10
            ),
            2,
        )

        grade = self._grade(score)

        reasons = []

        if quality_score < 100:
            reasons.append(
                "One or more data quality checks did not pass."
            )

        if schema_score < 100:
            reasons.append(
                "Schema drift was detected."
            )

        if anomaly_score < 100:
            reasons.append(
                f"{pipeline_run.anomalies_detected} "
                "data anomaly/anomalies were detected."
            )

        if not reasons:
            reasons.append(
                "No reliability issues were detected."
            )

        return {
            "score": score,
            "grade": grade,
            "status": self._status(score),
            "breakdown": {
                "quality": quality_score,
                "schema": schema_score,
                "anomalies": anomaly_score,
                "pipeline": pipeline_score,
            },
            "reasons": reasons,
        }

    @staticmethod
    def _quality_score(
        quality_score,
    ) -> float:

        if quality_score is None:
            return 0.0

        return max(
            0.0,
            min(
                float(quality_score),
                100.0,
            ),
        )

    @staticmethod
    def _schema_score(
        schema_changed: bool,
    ) -> float:

        return 0.0 if schema_changed else 100.0

    @staticmethod
    def _anomaly_score(
        anomaly_count: int,
    ) -> float:

        if anomaly_count <= 0:
            return 100.0

        if anomaly_count == 1:
            return 75.0

        if anomaly_count == 2:
            return 50.0

        if anomaly_count == 3:
            return 25.0

        return 0.0

    @staticmethod
    def _pipeline_score(
        status: str,
    ) -> float:

        return 100.0 if status == "SUCCESS" else 0.0

    @staticmethod
    def _grade(
        score: float,
    ) -> str:

        if score >= 90:
            return "A"

        if score >= 80:
            return "B"

        if score >= 70:
            return "C"

        if score >= 60:
            return "D"

        return "F"

    @staticmethod
    def _status(
        score: float,
    ) -> str:

        if score >= 90:
            return "RELIABLE"

        if score >= 70:
            return "DEGRADED"

        return "UNRELIABLE"
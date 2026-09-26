from __future__ import annotations

from core.models import DataAnomaly, Dataset, PipelineRun


class AnomalyPersistenceService:

    def save_anomalies(
        self,
        dataset: Dataset,
        pipeline_run: PipelineRun,
        anomaly_result: dict,
    ) -> list[DataAnomaly]:

        anomalies = anomaly_result.get("anomalies", [])

        created_anomalies = []

        for anomaly in anomalies:
            created_anomaly = self._create_anomaly(
                dataset=dataset,
                pipeline_run=pipeline_run,
                anomaly=anomaly,
            )

            created_anomalies.append(created_anomaly)

        return created_anomalies

    def _create_anomaly(
        self,
        dataset: Dataset,
        pipeline_run: PipelineRun,
        anomaly: dict,
    ) -> DataAnomaly:

        anomaly_type = anomaly.get("type")

        if anomaly_type not in DataAnomaly.AnomalyType.values:
            raise ValueError(
                f"Unsupported anomaly type: {anomaly_type}"
            )

        severity = anomaly.get(
            "severity",
            DataAnomaly.Severity.MEDIUM,
        )

        if severity not in DataAnomaly.Severity.values:
            severity = DataAnomaly.Severity.MEDIUM

        column_name = anomaly.get("column") or ""

        title = self._build_title(
            anomaly_type=anomaly_type,
            column_name=column_name,
        )

        description = anomaly.get(
            "message",
            "An anomaly was detected in the dataset.",
        )

        expected_value = anomaly.get(
            "previous_value"
        )

        actual_value = anomaly.get(
            "current_value"
        )

        anomaly_score = anomaly.get(
            "change_percentage"
        )

        return DataAnomaly.objects.create(
            dataset=dataset,
            pipeline_run=pipeline_run,
            anomaly_type=anomaly_type,
            column_name=column_name,
            title=title,
            description=description,
            severity=severity,
            expected_value=expected_value,
            actual_value=actual_value,
            anomaly_score=anomaly_score,
            details=anomaly,
        )

    @staticmethod
    def _build_title(
        anomaly_type: str,
        column_name: str,
    ) -> str:

        if anomaly_type == DataAnomaly.AnomalyType.ROW_COUNT:
            return "Row count anomaly detected"

        if anomaly_type == DataAnomaly.AnomalyType.NULL_RATE:
            if column_name:
                return (
                    f"Null rate anomaly detected for "
                    f"{column_name}"
                )

            return "Null rate anomaly detected"

        if (
            anomaly_type
            == DataAnomaly.AnomalyType.VALUE_DISTRIBUTION
        ):
            if column_name:
                return (
                    f"Value distribution anomaly detected "
                    f"for {column_name}"
                )

            return "Value distribution anomaly detected"

        if (
            anomaly_type
            == DataAnomaly.AnomalyType.COLUMN_VALUE
        ):
            if column_name:
                return (
                    f"Column value anomaly detected "
                    f"for {column_name}"
                )

            return "Column value anomaly detected"

        if (
            anomaly_type
            == DataAnomaly.AnomalyType.PIPELINE_DURATION
        ):
            return "Pipeline duration anomaly detected"

        if anomaly_type == DataAnomaly.AnomalyType.FRESHNESS:
            return "Data freshness anomaly detected"

        return "Data anomaly detected"
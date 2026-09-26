from __future__ import annotations

from core.models import Alert


class AlertService:

    def _create_alert(
        self,
        pipeline_run,
        alert_type,
        severity,
        title,
        message,
        metadata=None,
    ):
        existing_alert = Alert.objects.filter(
            pipeline_run=pipeline_run,
            alert_type=alert_type,
        ).first()

        if existing_alert:
            return None

        return Alert.objects.create(
            pipeline=pipeline_run.pipeline,
            pipeline_run=pipeline_run,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            metadata=metadata or {},
        )

    def create_pipeline_failure_alert(
        self,
        pipeline_run,
    ):
        return self._create_alert(
            pipeline_run=pipeline_run,
            alert_type=Alert.AlertType.PIPELINE_FAILURE,
            severity=Alert.Severity.CRITICAL,
            title="Pipeline run failed",
            message=(
                f"Pipeline run #{pipeline_run.id} "
                f"for '{pipeline_run.pipeline.name}' failed."
            ),
            metadata={
                "run_id": pipeline_run.id,
                "error_message": pipeline_run.error_message,
            },
        )

    def create_low_reliability_alert(
        self,
        pipeline_run,
    ):
        if pipeline_run.reliability_score is None:
            return None

        score = float(
            pipeline_run.reliability_score
        )

        if score >= 70:
            return None

        severity = (
            Alert.Severity.CRITICAL
            if score < 50
            else Alert.Severity.HIGH
        )

        return self._create_alert(
            pipeline_run=pipeline_run,
            alert_type=Alert.AlertType.LOW_RELIABILITY,
            severity=severity,
            title="Low pipeline reliability detected",
            message=(
                f"Pipeline run #{pipeline_run.id} "
                f"has a reliability score of {score:.2f}."
            ),
            metadata={
                "reliability_score": score,
                "reliability_grade": (
                    pipeline_run.reliability_grade
                ),
                "reliability_status": (
                    pipeline_run.reliability_status
                ),
            },
        )

    def create_schema_drift_alert(
        self,
        pipeline_run,
    ):
        if not pipeline_run.schema_changed:
            return None

        schema_metadata = (
            pipeline_run.metadata.get(
                "schema_drift",
                {}
            )
            if isinstance(
                pipeline_run.metadata,
                dict
            )
            else {}
        )

        return self._create_alert(
            pipeline_run=pipeline_run,
            alert_type=Alert.AlertType.SCHEMA_DRIFT,
            severity=Alert.Severity.HIGH,
            title="Schema drift detected",
            message=(
                f"Schema changes were detected "
                f"during pipeline run #{pipeline_run.id}."
            ),
            metadata=schema_metadata,
        )

    def create_data_anomaly_alert(
        self,
        pipeline_run,
    ):
        if pipeline_run.anomalies_detected <= 0:
            return None

        anomaly_metadata = (
            pipeline_run.metadata.get(
                "anomaly_detection",
                {}
            )
            if isinstance(
                pipeline_run.metadata,
                dict
            )
            else {}
        )

        anomalies = anomaly_metadata.get(
            "anomalies",
            []
        )

        severity = Alert.Severity.MEDIUM

        for anomaly in anomalies:
            if anomaly.get("severity") == "CRITICAL":
                severity = Alert.Severity.CRITICAL
                break

            if anomaly.get("severity") == "HIGH":
                severity = Alert.Severity.HIGH

        return self._create_alert(
            pipeline_run=pipeline_run,
            alert_type=Alert.AlertType.DATA_ANOMALY,
            severity=severity,
            title="Data anomalies detected",
            message=(
                f"{pipeline_run.anomalies_detected} "
                f"data anomaly/anomalies were detected "
                f"during pipeline run #{pipeline_run.id}."
            ),
            metadata=anomaly_metadata,
        )

    def create_quality_failure_alert(
        self,
        pipeline_run,
    ):
        failed_results = (
            pipeline_run.quality_results
            .filter(
                passed=False
            )
            .select_related(
                "quality_check"
            )
        )

        if not failed_results.exists():
            return None

        failures = []

        highest_severity = Alert.Severity.LOW

        severity_order = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }

        for result in failed_results:
            check = result.quality_check

            failures.append(
                {
                    "check": check.name,
                    "severity": check.severity,
                    "column": check.column_name,
                    "rows_failed": result.rows_failed,
                }
            )

            if (
                severity_order.get(
                    check.severity,
                    1
                )
                > severity_order.get(
                    highest_severity,
                    1
                )
            ):
                highest_severity = check.severity

        return self._create_alert(
            pipeline_run=pipeline_run,
            alert_type=Alert.AlertType.QUALITY_FAILURE,
            severity=highest_severity,
            title="Data quality failures detected",
            message=(
                f"{len(failures)} data quality "
                f"check(s) failed during "
                f"pipeline run #{pipeline_run.id}."
            ),
            metadata={
                "failures": failures,
            },
        )

    def create_alerts_for_run(
        self,
        pipeline_run,
    ):
        alerts = []

        if pipeline_run.status == "FAILED":
            alert = self.create_pipeline_failure_alert(
                pipeline_run
            )

            if alert:
                alerts.append(alert)

            return alerts

        alert = self.create_low_reliability_alert(
            pipeline_run
        )

        if alert:
            alerts.append(alert)

        alert = self.create_schema_drift_alert(
            pipeline_run
        )

        if alert:
            alerts.append(alert)

        alert = self.create_data_anomaly_alert(
            pipeline_run
        )

        if alert:
            alerts.append(alert)

        alert = self.create_quality_failure_alert(
            pipeline_run
        )

        if alert:
            alerts.append(alert)

        return alerts
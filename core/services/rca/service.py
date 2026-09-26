from __future__ import annotations
from typing import Any

class RCAService:
    def analyze(self, pipeline_run) -> dict[str, Any]:
        metadata = (
            pipeline_run.metadata
            if isinstance(pipeline_run.metadata, dict)
            else {}
        )

        schema_drift = metadata.get("schema_drift", {})
        anomaly_detection = metadata.get("anomaly_detection", {})
        anomalies = anomaly_detection.get("anomalies", [])
        quality_failures = self._get_quality_failures(pipeline_run)

        findings = []
        findings.extend(self._analyze_quality_failures(quality_failures))
        findings.extend(self._analyze_schema_drift(schema_drift))
        findings.extend(self._analyze_anomalies(anomalies))

        if pipeline_run.status == "FAILED":
            findings.append({
                "type": "PIPELINE_FAILURE",
                "severity": "CRITICAL",
                "title": "Pipeline execution failed",
                "root_cause": "The pipeline did not complete successfully.",
                "evidence": pipeline_run.error_message or "No pipeline error message was recorded.",
                "impact": "The current pipeline run may not contain complete or reliable results.",
                "recommendation": "Inspect the pipeline error message and upstream data source before rerunning.",
            })

        return self._build_result(pipeline_run, findings)

    def _get_quality_failures(self, pipeline_run) -> list:
        return list(
            pipeline_run.quality_results
            .select_related("quality_check")
            .filter(passed=False)
        )

    def _analyze_quality_failures(self, results: list) -> list[dict[str, Any]]:
        findings = []
        for result in results:
            check = result.quality_check
            column = check.column_name or "dataset"
            findings.append({
                "type": "DATA_QUALITY",
                "severity": check.severity,
                "title": f"Data quality check failed: {check.name}",
                "root_cause": f"The {check.check_type.lower()} validation failed for {column}.",
                "evidence": result.details,
                "impact": f"Invalid or incomplete data in {column} may affect downstream processing.",
                "recommendation": f"Inspect the {column} values in the latest dataset and verify the upstream data source.",
            })
        return findings

    def _analyze_schema_drift(self, schema_drift: dict) -> list[dict[str, Any]]:
        if not schema_drift.get("has_drift", False):
            return []

        added = schema_drift.get("added_columns", [])
        removed = schema_drift.get("removed_columns", [])
        changed = schema_drift.get("changed_columns", [])

        evidence = {
            "added_columns": added,
            "removed_columns": removed,
            "changed_columns": changed,
        }

        return [{
            "type": "SCHEMA_DRIFT",
            "severity": "HIGH",
            "title": "Schema drift detected",
            "root_cause": "The incoming dataset schema differs from the previously observed schema.",
            "evidence": evidence,
            "impact": "Downstream transformations, validation rules, joins, or consumers may be affected by the schema change.",
            "recommendation": "Review the changed, added, and removed columns and verify whether the upstream schema change was expected.",
        }]

    def _analyze_anomalies(self, anomalies: list) -> list[dict[str, Any]]:
        findings = []
        for anomaly in anomalies:
            anomaly_type = anomaly.get("type", "UNKNOWN")
            severity = anomaly.get("severity", "MEDIUM")
            column = anomaly.get("column")
            message = anomaly.get("message", "An unexpected data pattern was detected.")

            findings.append({
                "type": anomaly_type,
                "severity": severity,
                "title": self._anomaly_title(anomaly_type),
                "root_cause": message,
                "evidence": {
                    "column": column,
                    "metric": anomaly.get("metric"),
                    "previous_value": anomaly.get("previous_value"),
                    "current_value": anomaly.get("current_value"),
                    "change_percentage": anomaly.get("change_percentage"),
                    "direction": anomaly.get("direction"),
                },
                "impact": self._anomaly_impact(anomaly_type),
                "recommendation": self._anomaly_recommendation(anomaly_type),
            })
        return findings

    @staticmethod
    def _anomaly_title(anomaly_type: str) -> str:
        titles = {
            "ROW_COUNT": "Unexpected row count change",
            "NULL_RATE": "Unexpected null rate increase",
            "VALUE_DISTRIBUTION": "Unexpected value distribution change",
            "COLUMN_VALUE": "Unexpected column value detected",
            "PIPELINE_DURATION": "Unexpected pipeline duration",
            "FRESHNESS": "Data freshness issue detected",
        }
        return titles.get(anomaly_type, "Data anomaly detected")

    @staticmethod
    def _anomaly_impact(anomaly_type: str) -> str:
        impacts = {
            "ROW_COUNT": "A significant change in record volume may indicate missing, duplicated, or unexpected source data.",
            "NULL_RATE": "Increased missing values may reduce data completeness and affect downstream processing.",
            "VALUE_DISTRIBUTION": "A significant distribution change may indicate an upstream data change or unexpected business behavior.",
            "COLUMN_VALUE": "Unexpected column values may cause validation or downstream processing issues.",
            "PIPELINE_DURATION": "A significant execution-time change may indicate pipeline performance degradation.",
            "FRESHNESS": "Stale data may cause downstream consumers to operate on outdated information.",
        }
        return impacts.get(anomaly_type, "The detected anomaly may affect downstream data reliability.")

    @staticmethod
    def _anomaly_recommendation(anomaly_type: str) -> str:
        recommendations = {
            "ROW_COUNT": "Inspect the latest source batch and compare record counts with the upstream system.",
            "NULL_RATE": "Inspect newly ingested records and verify whether the upstream source changed its missing-value behavior.",
            "VALUE_DISTRIBUTION": "Compare the affected column with recent pipeline runs and investigate upstream transformations or source changes.",
            "COLUMN_VALUE": "Inspect the affected values and validate them against the expected business rules.",
            "PIPELINE_DURATION": "Review recent execution times and investigate changes in data volume or pipeline processing.",
            "FRESHNESS": "Check the upstream source and verify the latest successful data arrival time.",
        }
        return recommendations.get(anomaly_type, "Inspect the affected dataset and compare the current run with previous successful runs.")

    @staticmethod
    def _build_result(pipeline_run, findings: list[dict[str, Any]]) -> dict[str, Any]:
        if not findings:
            return {
                "has_findings": False,
                "finding_count": 0,
                "primary_finding": None,
                "findings": [],
                "summary": "No root cause findings were identified.",
            }

        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        findings = sorted(
            findings,
            key=lambda finding: severity_order.get(finding.get("severity", "LOW"), 0),
            reverse=True,
        )

        return {
            "has_findings": True,
            "finding_count": len(findings),
            "primary_finding": findings[0],
            "findings": findings,
            "summary": f"{len(findings)} root cause finding{'s' if len(findings) != 1 else ''} identified.",
        }

from django.db import transaction

from core.models import (
    Dataset,
    PipelineRun,
    QualityCheck,
    QualityIssue,
    QualityResult,
)


class QualityPersistenceService:

    @transaction.atomic
    def save_results(
        self,
        dataset: Dataset,
        pipeline_run: PipelineRun,
        engine_result: dict,
    ) -> None:
        checks = engine_result.get("checks", [])

        if not checks:
            raise ValueError(
                f"No quality check results were returned for "
                f"dataset '{dataset.name}'."
            )

        for check_result in checks:
            self._save_check_result(
                pipeline_run=pipeline_run,
                dataset=dataset,
                check_result=check_result,
            )

    def _save_check_result(
        self,
        pipeline_run: PipelineRun,
        dataset: Dataset,
        check_result: dict,
    ) -> QualityResult:
        check_name = check_result.get("check_name")

        if not check_name:
            raise ValueError(
                "QualityEngine result is missing 'check_name'."
            )

        details = check_result.get("details") or {}

        column_name = details.get("column", "")

        quality_check = (
            QualityCheck.objects
            .filter(
                dataset=dataset,
                check_type=check_name,
                column_name=column_name,
                is_active=True,
            )
            .order_by("id")
            .first()
        )

        if quality_check is None:
            raise ValueError(
                "No active QualityCheck configuration found for "
                f"{check_name} / {column_name or 'dataset'}."
            )

        rows_checked = max(
            int(check_result.get("rows_checked", 0)),
            0,
        )

        rows_failed = max(
            int(check_result.get("rows_failed", 0)),
            0,
        )

        rows_passed = max(
            int(check_result.get("rows_passed", 0)),
            0,
        )

        rows_failed = min(
            rows_failed,
            rows_checked,
        )

        rows_passed = min(
            rows_passed,
            rows_checked - rows_failed,
        )

        pass_rate = (
            round(
                (rows_passed / rows_checked) * 100,
                2,
            )
            if rows_checked
            else 0
        )

        quality_result = QualityResult.objects.create(
            quality_check=quality_check,
            pipeline_run=pipeline_run,
            passed=bool(
                check_result.get("passed", False)
            ),
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            pass_rate=pass_rate,
            details=details,
        )

        if not quality_result.passed:
            self._create_issue(
                quality_result=quality_result,
                check_result=check_result,
                dataset=dataset,
                rows_failed=rows_failed,
                rows_checked=rows_checked,
            )

        return quality_result

    def _create_issue(
        self,
        quality_result: QualityResult,
        check_result: dict,
        dataset: Dataset,
        rows_failed: int,
        rows_checked: int,
    ) -> QualityIssue:
        check_name = check_result.get(
            "check_name",
            "QUALITY",
        )

        details = check_result.get("details") or {}

        column = details.get(
            "column",
            "dataset",
        )

        severity = self._determine_severity(
            failed_rows=rows_failed,
            total_rows=rows_checked,
        )

        title = (
            f"{check_name} check failed for {column}"
        )

        description = (
            f"Dataset '{dataset.name}' failed the "
            f"{check_name} quality check. "
            f"{rows_failed} row(s) failed the check "
            f"out of {rows_checked} checked."
        )

        ai_analysis = details.get(
            "ai_analysis",
            "",
        )

        ai_recommendation = details.get(
            "ai_recommendation",
            "",
        )

        return QualityIssue.objects.create(
            quality_result=quality_result,
            title=title,
            description=description,
            severity=severity,
            status=QualityIssue.Status.OPEN,
            ai_analysis=ai_analysis,
            ai_recommendation=ai_recommendation,
        )

    @staticmethod
    def _determine_severity(
        failed_rows: int,
        total_rows: int,
    ) -> str:
        if total_rows <= 0:
            return QualityIssue.Severity.LOW

        failure_percentage = (
            failed_rows / total_rows
        ) * 100

        if failure_percentage >= 50:
            return QualityIssue.Severity.CRITICAL

        if failure_percentage >= 20:
            return QualityIssue.Severity.HIGH

        if failure_percentage >= 5:
            return QualityIssue.Severity.MEDIUM

        return QualityIssue.Severity.LOW

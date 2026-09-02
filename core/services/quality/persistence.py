from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import (
    Dataset,
    Pipeline,
    PipelineRun,
    QualityCheck,
    QualityIssue,
    QualityResult,
)


class QualityPersistenceService:
    """
    Persist quality-engine results into the DataSentinel database.
    """

    SYSTEM_USERNAME = "datasentinel"

    @transaction.atomic
    def persist_analysis(
        self,
        dataset_name: str,
        engine_result: dict,
        owner: User,
    ) -> PipelineRun:
        """
        Create the dataset and pipeline records and persist
        the complete quality analysis.
        """

        profile = engine_result["profile"]

        dataset = Dataset.objects.create(
            name=dataset_name,
            description="Dataset analyzed by DataSentinel.",
            owner=owner,
            row_count=profile["row_count"],
            column_count=profile["column_count"],
            schema_snapshot={
                "schema": engine_result.get("schema", []),
                "profile": profile,
            },
        )

        pipeline = Pipeline.objects.create(
            name=f"{dataset_name} Quality Pipeline",
            description="Automatic data-quality analysis pipeline.",
            dataset=dataset,
            status=Pipeline.Status.ACTIVE,
        )

        return self.save_run(
            dataset=dataset,
            pipeline=pipeline,
            engine_result=engine_result,
        )

    @classmethod
    def get_system_user(cls) -> User:
        """
        Return the DataSentinel system user.

        This is temporary while the API is not authenticated.
        Later this can be replaced with request.user.
        """

        user, _ = User.objects.get_or_create(
            username=cls.SYSTEM_USERNAME,
            defaults={
                "email": "system@datasentinel.local",
                "is_active": True,
            },
        )

        return user

    @transaction.atomic
    def save_run(
        self,
        dataset: Dataset,
        pipeline: Pipeline,
        engine_result: dict,
    ) -> PipelineRun:
        """
        Create a successful PipelineRun and persist all
        quality results and issues.
        """

        summary = engine_result["summary"]

        pipeline_run = PipelineRun.objects.create(
            pipeline=pipeline,
            status=PipelineRun.Status.SUCCESS,
            rows_processed=engine_result["profile"]["row_count"],
            quality_score=summary["quality_score"],
            completed_at=timezone.now(),
        )

        self.save_results(
            dataset=dataset,
            pipeline_run=pipeline_run,
            engine_result=engine_result,
        )

        return pipeline_run

    @transaction.atomic
    def save_results(
        self,
        dataset: Dataset,
        pipeline_run: PipelineRun,
        engine_result: dict,
    ) -> None:
        """
        Persist every quality-engine result.

        Existing QualityCheck configurations are reused.
        A pipeline execution must NEVER silently create a
        new QualityCheck configuration.
        """

        for check_result in engine_result["checks"]:
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
        """
        Match an engine result to an existing active QualityCheck,
        then create the corresponding QualityResult.
        """

        check_name = check_result["check_name"]

        details = check_result.get(
            "details",
            {},
        )

        column_name = details.get(
            "column",
            "",
        )

        # ---------------------------------------------------------
        # FIND EXISTING QUALITY CHECK
        # ---------------------------------------------------------

        quality_check = QualityCheck.objects.filter(
            dataset=dataset,
            check_type=check_name,
            column_name=column_name,
            is_active=True,
        ).first()

        if quality_check is None:
            raise ValueError(
                f"No active QualityCheck configuration found for "
                f"{check_name} / {column_name or 'dataset'}."
            )

        # ---------------------------------------------------------
        # CALCULATE RESULT METRICS
        # ---------------------------------------------------------

        rows_checked = check_result["rows_checked"]
        rows_passed = check_result["rows_passed"]
        rows_failed = check_result["rows_failed"]

        pass_rate = (
            round(
                (rows_passed / rows_checked) * 100,
                2,
            )
            if rows_checked
            else 0
        )

        # ---------------------------------------------------------
        # CREATE QUALITY RESULT
        # ---------------------------------------------------------

        quality_result = QualityResult.objects.create(
            quality_check=quality_check,
            pipeline_run=pipeline_run,
            passed=check_result["passed"],
            rows_checked=rows_checked,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            pass_rate=pass_rate,
            details=details,
        )

        # ---------------------------------------------------------
        # CREATE ISSUE FOR FAILED CHECK
        # ---------------------------------------------------------

        if not check_result["passed"]:
            self._create_issue(
                quality_result=quality_result,
                check_result=check_result,
                dataset=dataset,
            )

        return quality_result

    def _create_issue(
        self,
        quality_result: QualityResult,
        check_result: dict,
        dataset: Dataset,
    ) -> QualityIssue:
        """
        Create a QualityIssue for a failed quality check.
        """

        failed_rows = check_result["rows_failed"]
        total_rows = check_result["rows_checked"]
        check_name = check_result["check_name"]

        severity = self._determine_severity(
            failed_rows=failed_rows,
            total_rows=total_rows,
        )

        column = check_result["details"].get(
            "column",
            "dataset",
        )

        title = (
            f"{check_name} check failed for {column}"
        )

        description = (
            f"Dataset '{dataset.name}' failed the "
            f"{check_name} quality check. "
            f"{failed_rows} row(s) failed the check."
        )

        return QualityIssue.objects.create(
            quality_result=quality_result,
            title=title,
            description=description,
            severity=severity,
        )

    @staticmethod
    def _determine_severity(
        failed_rows: int,
        total_rows: int,
    ) -> str:
        """
        Determine issue severity from the percentage of
        failed rows.
        """

        if total_rows == 0:
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


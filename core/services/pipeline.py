import os
from django.db import transaction
from django.utils import timezone

from core.models import Pipeline, PipelineRun
from core.services.anomaly.detector import AnomalyDetector
from core.services.anomaly.persistence import AnomalyPersistenceService
from core.services.ingestion.postgres import PostgreSQLConnector
from core.services.ingestion.universal_loader import UniversalLoader
from core.services.quality.engine import QualityEngine
from core.services.quality.persistence import QualityPersistenceService
from core.services.reliability.score import ReliabilityScoreService
from core.services.rca.service import RCAService
from core.services.schema.drift import SchemaDriftDetector
from core.services.alerts.service import AlertService

class PipelineService:
    def run_pipeline(self, pipeline_id: int):
        with transaction.atomic():
            pipeline = Pipeline.objects.select_for_update().get(id=pipeline_id)

            if pipeline.status != Pipeline.Status.ACTIVE:
                raise ValueError(f"Pipeline '{pipeline.name}' is inactive.")

            if not pipeline.dataset_id:
                raise ValueError(f"Pipeline '{pipeline.name}' has no dataset configured.")

            if not pipeline.dataset.is_active:
                raise ValueError(f"Dataset '{pipeline.dataset.name}' is inactive.")

            if pipeline.runs.filter(status=PipelineRun.Status.RUNNING).exists():
                raise ValueError(f"Pipeline '{pipeline.name}' is already running.")

            pipeline_run = PipelineRun.objects.create(
                pipeline=pipeline,
                status=PipelineRun.Status.RUNNING,
                rows_processed=0,
                anomalies_detected=0,
            )

        dataset = pipeline.dataset.__class__.objects.select_related("data_source").get(id=pipeline.dataset_id)

        try:
            dataframe = self._load_dataset(dataset)
            if dataframe.empty:
                raise ValueError(f"Dataset '{dataset.name}' contains no rows.")

            current_schema = self._build_schema_snapshot(dataframe)

            previous_run = (
                pipeline.runs.filter(status=PipelineRun.Status.SUCCESS)
                .exclude(id=pipeline_run.id)
                .order_by("-completed_at")
                .first()
            )

            previous_schema = None
            previous_statistics = None

            if previous_run and isinstance(previous_run.metadata, dict):
                stored_schema = previous_run.metadata.get("schema_snapshot")
                if isinstance(stored_schema, dict):
                    previous_schema = stored_schema

                stored_statistics = previous_run.metadata.get("anomaly_statistics")
                if isinstance(stored_statistics, dict):
                    previous_statistics = stored_statistics

            if previous_schema:
                drift_detector = SchemaDriftDetector()
                schema_drift = drift_detector.compare(
                    previous_schema=previous_schema,
                    current_schema=current_schema,
                )
            else:
                schema_drift = {
                    "has_drift": False,
                    "added_columns": [],
                    "removed_columns": [],
                    "changed_columns": [],
                    "summary": {"added": 0, "removed": 0, "changed": 0},
                }

            pipeline_run.schema_changed = schema_drift["has_drift"]

            anomaly_detector = AnomalyDetector()
            anomaly_result = anomaly_detector.detect(
                current_dataframe=dataframe,
                previous_statistics=previous_statistics,
            )

            pipeline_run.anomalies_detected = anomaly_result["summary"]["total"]
            pipeline_run.metadata = {
                "schema_snapshot": current_schema,
                "schema_drift": schema_drift,
                "anomaly_statistics": anomaly_result["current_statistics"],
                "anomaly_detection": {
                    "has_anomalies": anomaly_result["has_anomalies"],
                    "anomalies": anomaly_result["anomalies"],
                    "summary": anomaly_result["summary"],
                },
            }

            dataset.row_count = len(dataframe)
            dataset.column_count = len(dataframe.columns)
            dataset.schema_snapshot = current_schema
            dataset.file_size = (
                os.path.getsize(dataset.file_path)
                if dataset.file_path and os.path.isfile(dataset.file_path)
                else dataset.file_size
            )
            dataset.last_processed_at = timezone.now()

            dataset.save(
                update_fields=[
                    "row_count",
                    "column_count",
                    "schema_snapshot",
                    "file_size",
                    "last_processed_at",
                    "updated_at",
                ]
            )

            quality_checks = dataset.quality_checks.filter(is_active=True).order_by("id")
            check_config = []

            for quality_check in quality_checks:
                config = {"check": quality_check.check_type}
                if quality_check.column_name:
                    config["column"] = quality_check.column_name
                if quality_check.configuration:
                    config.update(quality_check.configuration)
                check_config.append(config)

            if not check_config:
                raise ValueError(f"Pipeline '{pipeline.name}' has no active quality checks configured.")

            engine = QualityEngine()
            engine_result = engine.run_dataframe_checks(
                dataframe=dataframe,
                dataset_name=dataset.name,
                check_config=check_config,
            )

            summary = engine_result.get("summary", {})
            profile = engine_result.get("profile", {})

            pipeline_run.rows_processed = profile.get("row_count", len(dataframe))
            pipeline_run.quality_score = summary.get("quality_score")
            pipeline_run.checks_passed = summary.get("passed_checks", 0)
            pipeline_run.checks_failed = summary.get("failed_checks", 0)
            pipeline_run.warnings_count = summary.get("warnings_count", 0)

            persistence = QualityPersistenceService()
            persistence.save_results(dataset=dataset, pipeline_run=pipeline_run, engine_result=engine_result)

            anomaly_persistence = AnomalyPersistenceService()
            anomaly_persistence.save_anomalies(dataset=dataset, pipeline_run=pipeline_run, anomaly_result=anomaly_result)

            pipeline_run.status = PipelineRun.Status.SUCCESS
            pipeline_run.completed_at = timezone.now()

            reliability_service = ReliabilityScoreService()
            reliability_result = reliability_service.calculate(pipeline_run)

            pipeline_run.reliability_score = reliability_result["score"]
            pipeline_run.reliability_grade = reliability_result["grade"]
            pipeline_run.reliability_status = reliability_result["status"]
            pipeline_run.metadata["reliability"] = reliability_result

            pipeline_run.save(
                update_fields=[
                    "rows_processed",
                    "quality_score",
                    "checks_passed",
                    "checks_failed",
                    "warnings_count",
                    "anomalies_detected",
                    "schema_changed",
                    "reliability_score",
                    "reliability_grade",
                    "reliability_status",
                    "metadata",
                    "status",
                    "completed_at",
                ]
            )

            rca_service = RCAService()
            rca_result = rca_service.analyze(pipeline_run)
            pipeline_run.metadata["rca"] = rca_result
            pipeline_run.save(update_fields=["metadata"])

            alert_service = AlertService()
            alerts = alert_service.create_alerts_for_run(pipeline_run)
            pipeline_run.metadata["alerts"] = {
                "count": len(alerts),
                "alert_ids": [alert.id for alert in alerts],
            }
            pipeline_run.save(update_fields=["metadata"])

            return pipeline_run

        except Exception as exc:
            pipeline_run.status = PipelineRun.Status.FAILED
            pipeline_run.error_message = str(exc)
            pipeline_run.quality_score = None
            pipeline_run.completed_at = timezone.now()

            pipeline_run.save(
                update_fields=["status", "error_message", "quality_score", "completed_at"]
            )
            raise


    @staticmethod
    def _build_schema_snapshot(dataframe):
        return {
            "columns": [
                {"name": str(column), "dtype": str(dataframe[column].dtype)}
                for column in dataframe.columns
            ]
        }

    def _load_dataset(self, dataset):
        source_type = dataset.data_source.source_type if dataset.data_source else None
        if source_type == "DATABASE":
            return self._load_database(dataset)
        if dataset.file_path:
            return self._load_file(dataset)
        raise ValueError(f"Dataset '{dataset.name}' does not have a supported data source configured.")

    def _load_file(self, dataset):
        if not dataset.file_path:
            raise ValueError(f"Dataset '{dataset.name}' does not have a file configured.")

        file_path = os.path.abspath(dataset.file_path)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        loader = UniversalLoader()
        file_format = str(dataset.file_format).upper() if dataset.file_format else None
        if file_format == "UNKNOWN":
            file_format = None

        try:
            return loader.read(source=file_path, file_format=file_format)
        except Exception as exc:
            raise ValueError(f"Unable to load dataset '{dataset.name}': {exc}") from exc

    def _load_database(self, dataset):
        if not dataset.table_name:
            raise ValueError(f"Dataset '{dataset.name}' does not have a PostgreSQL table configured.")

        connector = PostgreSQLConnector()
        if not connector.table_exists(dataset.table_name):
            raise ValueError(f"PostgreSQL table '{dataset.table_name}' does not exist.")

        try:
            dataframe = connector.read_table(dataset.table_name)
        except Exception as exc:
            raise ValueError(f"Unable to read PostgreSQL dataset: {exc}") from exc

        return dataframe

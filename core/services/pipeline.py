import os
import pandas as pd

from django.utils import timezone

from core.models import Pipeline, PipelineRun
from core.services.ingestion.postgres import PostgreSQLConnector
from core.services.quality.engine import QualityEngine
from core.services.quality.persistence import QualityPersistenceService


class PipelineService:

    def run_pipeline(self, pipeline_id: int):

        # Load the pipeline and related dataset/source
        pipeline = Pipeline.objects.select_related(
            "dataset",
            "dataset__data_source",
        ).get(id=pipeline_id)

        dataset = pipeline.dataset

        # Prevent duplicate pipeline execution
        if pipeline.runs.filter(status=PipelineRun.Status.RUNNING).exists():
            raise ValueError(f"Pipeline '{pipeline.name}' is already running.")

        # Create a new running record
        pipeline_run = PipelineRun.objects.create(
            pipeline=pipeline,
            status=PipelineRun.Status.RUNNING,
            rows_processed=0,
        )

        try:

            # Load the dataset into a DataFrame
            dataframe = self._load_dataset(dataset)

            # Reject empty datasets
            if dataframe.empty:
                raise ValueError(f"Dataset '{dataset.name}' contains no rows.")

            # Update dataset metadata
            dataset.row_count = len(dataframe)
            dataset.column_count = len(dataframe.columns)

            dataset.schema_snapshot = {
                "columns": [
                    {
                        "name": column,
                        "dtype": str(dataframe[column].dtype),
                    }
                    for column in dataframe.columns
                ]
            }

            dataset.save(
                update_fields=[
                    "row_count",
                    "column_count",
                    "schema_snapshot",
                    "updated_at",
                ]
            )

            # Load active quality checks
            quality_checks = dataset.quality_checks.filter(
                is_active=True
            ).order_by("id")

            check_config = []

            for quality_check in quality_checks:

                config = {
                    "check": quality_check.check_type,
                }

                if quality_check.column_name:
                    config["column"] = quality_check.column_name

                if quality_check.configuration:
                    config.update(quality_check.configuration)

                check_config.append(config)

            if not check_config:
                raise ValueError(
                    f"Pipeline '{pipeline.name}' has no "
                    "active quality checks configured."
                )

            # Run quality engine
            engine = QualityEngine()

            engine_result = engine.run_dataframe_checks(
                dataframe=dataframe,
                dataset_name=dataset.name,
                check_config=check_config,
            )

            # Update pipeline run statistics
            pipeline_run.rows_processed = engine_result["profile"]["row_count"]

            pipeline_run.quality_score = engine_result["summary"]["quality_score"]

            pipeline_run.status = PipelineRun.Status.SUCCESS
            pipeline_run.completed_at = timezone.now()

            pipeline_run.save(
                update_fields=[
                    "rows_processed",
                    "quality_score",
                    "status",
                    "completed_at",
                ]
            )

            # Persist quality results and issues
            persistence = QualityPersistenceService()

            persistence.save_results(
                dataset=dataset,
                pipeline_run=pipeline_run,
                engine_result=engine_result,
            )

            return pipeline_run

        except Exception as exc:

            pipeline_run.status = PipelineRun.Status.FAILED
            pipeline_run.error_message = str(exc)
            pipeline_run.completed_at = timezone.now()

            pipeline_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            raise

    def _load_dataset(self, dataset):

        # Determine the configured dataset source
        source_type = (
            dataset.data_source.source_type
            if dataset.data_source
            else None
        )

        # Handle CSV datasets
        if source_type == "CSV":

            if not dataset.file_path:
                raise ValueError(
                    f"Dataset '{dataset.name}' does not have "
                    "a CSV file configured."
                )

            if not os.path.exists(dataset.file_path):
                raise FileNotFoundError(
                    f"CSV file not found: {dataset.file_path}"
                )

            if not dataset.file_path.lower().endswith(".csv"):
                raise ValueError("Only CSV datasets are supported.")

            try:
                dataframe = pd.read_csv(dataset.file_path)

            except Exception as exc:
                raise ValueError(
                    f"Unable to read CSV dataset: {exc}"
                ) from exc

            return dataframe

        # Handle PostgreSQL/database datasets
        if source_type == "DATABASE":

            if not dataset.table_name:
                raise ValueError(
                    f"Dataset '{dataset.name}' does not have "
                    "a PostgreSQL table configured."
                )

            connector = PostgreSQLConnector()

            if not connector.table_exists(dataset.table_name):
                raise ValueError(
                    f"PostgreSQL table "
                    f"'{dataset.table_name}' does not exist."
                )

            return connector.read_table(dataset.table_name)

        # Reject unsupported dataset sources
        raise ValueError(
            f"Unsupported dataset source type: {source_type}"
        )
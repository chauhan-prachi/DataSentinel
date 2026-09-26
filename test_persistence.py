import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()

from django.contrib.auth.models import User

from core.models import Dataset, DataSource, Pipeline
from core.services.pipeline import PipelineService


user, _ = User.objects.get_or_create(
    username="datasentinel_test",
)

data_source, _ = DataSource.objects.get_or_create(
    name="Local Test CSV",
    defaults={
        "source_type": DataSource.SourceType.CSV,
        "description": "Local CSV used for development testing.",
    },
)

dataset, _ = Dataset.objects.get_or_create(
    name="Customer Test Dataset",
    defaults={
        "description": "Test dataset for DataSentinel quality checks.",
        "owner": user,
        "data_source": data_source,
        "file_path": "data/customers.csv",
    },
)

pipeline, _ = Pipeline.objects.get_or_create(
    name="Customer Quality Pipeline",
    defaults={
        "description": "Runs quality checks on customer data.",
        "dataset": dataset,
    },
)

pipeline.status = Pipeline.Status.ACTIVE
pipeline.save(
    update_fields=["status"]
)

dataset.is_active = True
dataset.save(
    update_fields=["is_active"]
)

pipeline_run = PipelineService().run_pipeline(
    pipeline.id
)

print()
print("Quality run saved successfully.")
print(f"Pipeline Run ID: {pipeline_run.id}")
print(f"Quality Score: {pipeline_run.quality_score}")
print(f"Status: {pipeline_run.status}")
print(f"Rows Processed: {pipeline_run.rows_processed}")
print(f"Checks Passed: {pipeline_run.checks_passed}")
print(f"Checks Failed: {pipeline_run.checks_failed}")
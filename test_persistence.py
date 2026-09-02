import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()
from django.utils import timezone
from core.models import Dataset, DataSource, Pipeline
from core.services.quality.engine import QualityEngine
from core.services.quality.persistence import (
    QualityPersistenceService,
)
from django.contrib.auth.models import User


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

engine = QualityEngine()

check_config = [
    {
        "check": "NOT_NULL",
        "column": "email",
    },
    {
        "check": "UNIQUE",
        "column": "customer_id",
    },
    {
        "check": "VALID_EMAIL",
        "column": "email",
    },
    {
        "check": "RANGE",
        "column": "age",
        "minimum": 0,
        "maximum": 120,
    },
    {
        "check": "DUPLICATE",
    },
]

engine_result = engine.run_csv_checks(
    "data/customers.csv",
    check_config,
)

persistence = QualityPersistenceService()

pipeline_run = persistence.save_run(
    dataset=dataset,
    pipeline=pipeline,
    engine_result=engine_result,
)

print()
print("Quality run saved successfully.")
print(f"Pipeline Run ID: {pipeline_run.id}")
print(f"Quality Score: {pipeline_run.quality_score}")
print(f"Status: {pipeline_run.status}")
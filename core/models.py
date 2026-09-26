from django.db import models
from django.contrib.auth.models import User


class DataSource(models.Model):

    class SourceType(models.TextChoices):
        CSV = "CSV", "CSV"
        JSON = "JSON", "JSON"
        EXCEL = "EXCEL", "Excel"
        PARQUET = "PARQUET", "Parquet"
        TSV = "TSV", "TSV"
        XML = "XML", "XML"
        DATABASE = "DATABASE", "Database"
        API = "API", "API"
        S3 = "S3", "Amazon S3"

    name = models.CharField(max_length=150)

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
    )

    description = models.TextField(blank=True)

    connection_config = models.JSONField(
        default=dict,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Dataset(models.Model):

    class FileFormat(models.TextChoices):
        CSV = "CSV", "CSV"
        JSON = "JSON", "JSON"
        EXCEL = "EXCEL", "Excel"
        PARQUET = "PARQUET", "Parquet"
        TSV = "TSV", "TSV"
        XML = "XML", "XML"
        UNKNOWN = "UNKNOWN", "Unknown"

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="datasets",
    )

    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="datasets",
    )

    table_name = models.CharField(
        max_length=150,
        blank=True,
    )

    file_path = models.CharField(
        max_length=500,
        blank=True,
    )

    file_format = models.CharField(
        max_length=20,
        choices=FileFormat.choices,
        default=FileFormat.UNKNOWN,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
        help_text="File size in bytes.",
    )

    row_count = models.PositiveBigIntegerField(default=0)

    column_count = models.PositiveIntegerField(default=0)

    schema_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    profile_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    freshness_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Expected dataset freshness configuration.",
    )

    last_processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class Pipeline(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="pipelines",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    schedule = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: hourly, daily, or cron expression.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class PipelineRun(models.Model):

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="runs",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING,
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rows_processed = models.PositiveBigIntegerField(
        default=0
    )

    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    reliability_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    reliability_grade = models.CharField(
        max_length=2,
        blank=True,
    )

    reliability_status = models.CharField(
        max_length=20,
        blank=True,
    )

    checks_passed = models.PositiveIntegerField(
        default=0
    )

    checks_failed = models.PositiveIntegerField(
        default=0
    )

    warnings_count = models.PositiveIntegerField(
        default=0
    )

    anomalies_detected = models.PositiveIntegerField(
        default=0
    )

    schema_changed = models.BooleanField(
        default=False
    )

    error_message = models.TextField(
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return (
            f"{self.pipeline.name} - "
            f"{self.started_at:%Y-%m-%d %H:%M}"
        )


class Alert(models.Model):

    class AlertType(models.TextChoices):
        PIPELINE_FAILURE = (
            "PIPELINE_FAILURE",
            "Pipeline Failure",
        )
        LOW_RELIABILITY = (
            "LOW_RELIABILITY",
            "Low Reliability",
        )
        SCHEMA_DRIFT = (
            "SCHEMA_DRIFT",
            "Schema Drift",
        )
        DATA_ANOMALY = (
            "DATA_ANOMALY",
            "Data Anomaly",
        )
        QUALITY_FAILURE = (
            "QUALITY_FAILURE",
            "Quality Failure",
        )

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="alerts",
    )

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
    )

    alert_type = models.CharField(
        max_length=30,
        choices=AlertType.choices,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class QualityCheck(models.Model):

    class CheckType(models.TextChoices):
        NOT_NULL = "NOT_NULL", "Not Null"
        UNIQUE = "UNIQUE", "Unique"
        VALID_EMAIL = "VALID_EMAIL", "Valid Email"
        VALID_DATE = "VALID_DATE", "Valid Date"
        NUMERIC_VALIDITY = "NUMERIC_VALIDITY", "Numeric Validity"
        RANGE = "RANGE", "Range"
        SCHEMA = "SCHEMA", "Schema"
        DUPLICATE = "DUPLICATE", "Duplicate"
        FRESHNESS = "FRESHNESS", "Freshness"
        REGEX = "REGEX", "Regex"
        CUSTOM = "CUSTOM", "Custom"

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="quality_checks",
    )

    name = models.CharField(max_length=150)

    check_type = models.CharField(
        max_length=30,
        choices=CheckType.choices,
    )

    column_name = models.CharField(
        max_length=150,
        blank=True,
    )

    configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    threshold = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional pass threshold as a percentage.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class QualityResult(models.Model):

    quality_check = models.ForeignKey(
        QualityCheck,
        on_delete=models.CASCADE,
        related_name="results",
    )

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name="quality_results",
    )

    passed = models.BooleanField(default=False)

    rows_checked = models.PositiveBigIntegerField(default=0)

    rows_passed = models.PositiveBigIntegerField(default=0)

    rows_failed = models.PositiveBigIntegerField(default=0)

    pass_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]

    def __str__(self):
        return (
            f"{self.quality_check.name} - "
            f"{'PASS' if self.passed else 'FAIL'}"
        )


class QualityIssue(models.Model):

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"

    quality_result = models.ForeignKey(
        QualityResult,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    affected_rows = models.PositiveBigIntegerField(
        default=0,
    )

    ai_analysis = models.TextField(blank=True)

    ai_recommendation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SchemaSnapshot(models.Model):

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="schema_history",
    )

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="schema_snapshots",
    )

    version = models.PositiveIntegerField(default=1)

    schema = models.JSONField(
        default=dict,
        blank=True,
    )

    schema_hash = models.CharField(
        max_length=128,
        blank=True,
    )

    changes_detected = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.dataset.name} - "
            f"Schema v{self.version}"
        )


class DataAnomaly(models.Model):

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    class AnomalyType(models.TextChoices):
        ROW_COUNT = "ROW_COUNT", "Row Count"
        NULL_RATE = "NULL_RATE", "Null Rate"
        VALUE_DISTRIBUTION = (
            "VALUE_DISTRIBUTION",
            "Value Distribution",
        )
        COLUMN_VALUE = "COLUMN_VALUE", "Column Value"
        PIPELINE_DURATION = (
            "PIPELINE_DURATION",
            "Pipeline Duration",
        )
        FRESHNESS = "FRESHNESS", "Freshness"

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="anomalies",
    )

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name="anomalies",
    )

    anomaly_type = models.CharField(
        max_length=30,
        choices=AnomalyType.choices,
    )

    column_name = models.CharField(
        max_length=150,
        blank=True,
    )

    title = models.CharField(max_length=200)

    description = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    expected_value = models.FloatField(
        null=True,
        blank=True,
    )

    actual_value = models.FloatField(
        null=True,
        blank=True,
    )

    anomaly_score = models.FloatField(
        null=True,
        blank=True,
    )

    details = models.JSONField(
        default=dict,
        blank=True,
    )

    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return self.title
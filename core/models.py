from django.db import models
from django.contrib.auth.models import User


class DataSource(models.Model):
    class SourceType(models.TextChoices):
        CSV = "CSV", "CSV"
        JSON = "JSON", "JSON"
        DATABASE = "DATABASE", "Database"
        API = "API", "API"
        S3 = "S3", "Amazon S3"

    name = models.CharField(max_length=150)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
    )
    description = models.TextField(blank=True)
    connection_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Dataset(models.Model):
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

    table_name = models.CharField(max_length=150, blank=True)
    file_path = models.CharField(max_length=500, blank=True)

    row_count = models.PositiveBigIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)

    schema_snapshot = models.JSONField(default=dict, blank=True)

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

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    rows_processed = models.PositiveBigIntegerField(default=0)
    quality_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.pipeline.name} - {self.started_at:%Y-%m-%d %H:%M}"


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

    ai_analysis = models.TextField(blank=True)
    ai_recommendation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
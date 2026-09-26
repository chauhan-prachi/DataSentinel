import os
import json
from pathlib import Path
from django.utils.timezone import now
from django.utils.text import get_valid_filename
from uuid import uuid4
import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.services.ingestion.universal_loader import UniversalLoader
from core.forms import QualityCheckForm
from core.models import (
    DataSource,
    Dataset,
    Pipeline,
    PipelineRun,
    QualityCheck,
    QualityIssue,
    QualityResult,
)
from core.services.pipeline import PipelineService
from core.services.quality.engine import QualityEngine
from core.models import Alert

def _authenticated_user(request):
    if not request.user.is_authenticated:
        return None

    return request.user


def _dataset_queryset(request):
    user = _authenticated_user(request)

    if user is None:
        return Dataset.objects.none()

    return (
        Dataset.objects
        .select_related(
            "data_source",
            "owner",
        )
        .filter(
            owner=user,
            is_active=True,
        )
        .annotate(
            pipeline_count=Count(
                "pipelines",
                distinct=True,
            ),
            quality_check_count=Count(
                "quality_checks",
                filter=Q(
                    quality_checks__is_active=True
                ),
                distinct=True,
            ),
        )
        .order_by("-updated_at")
    )


def _pipeline_queryset(request):
    user = _authenticated_user(request)

    if user is None:
        return Pipeline.objects.none()

    return (
        Pipeline.objects
        .select_related("dataset")
        .filter(
            dataset__owner=user,
            dataset__is_active=True,
        )
        .annotate(
            run_count=Count(
                "runs",
                distinct=True,
            ),
            average_quality=Avg(
                "runs__quality_score",
            ),
            last_run_at=Max(
                "runs__started_at",
            ),
        )
        .order_by("name")
    )


def _run_queryset(request):
    user = _authenticated_user(request)

    if user is None:
        return PipelineRun.objects.none()

    return (
        PipelineRun.objects
        .select_related(
            "pipeline",
            "pipeline__dataset",
        )
        .filter(
            pipeline__dataset__owner=user,
            pipeline__dataset__is_active=True,
        )
        .order_by("-started_at")
    )


def _issue_queryset(request):
    user = _authenticated_user(request)

    if user is None:
        return QualityIssue.objects.none()

    return (
        QualityIssue.objects
        .select_related(
            "quality_result",
            "quality_result__quality_check",
            "quality_result__pipeline_run",
            "quality_result__pipeline_run__pipeline",
            "quality_result__pipeline_run__pipeline__dataset",
        )
        .filter(
            quality_result__pipeline_run__pipeline__dataset__owner=user,
            quality_result__pipeline_run__pipeline__dataset__is_active=True,
        )
        .order_by("-created_at")
    )

def _build_schema_snapshot(dataframe):
    columns = []

    for column in dataframe.columns:
        series = dataframe[column]

        null_count = int(
            series.isna().sum()
        )

        null_percentage = round(
            float(series.isna().mean() * 100),
            2,
        )

        unique_count = _safe_unique_count(
            series
        )

        columns.append(
            {
                "name": str(column),
                "dtype": str(series.dtype),
                "null_count": null_count,
                "null_percentage": null_percentage,
                "unique_count": unique_count,
            }
        )

    return {
        "columns": columns,
    }


def _safe_unique_count(series):
    for value in series:
        if isinstance(
            value,
            (dict, list, tuple, set),
        ):
            values = []

            for item in series.dropna():
                try:
                    values.append(
                        repr(item)
                    )
                except Exception:
                    values.append(
                        str(type(item))
                    )

            return int(
                len(set(values))
            )

    try:
        return int(
            series.nunique(dropna=True)
        )
    except TypeError:
        values = []

        for item in series.dropna():
            try:
                values.append(
                    repr(item)
                )
            except Exception:
                values.append(
                    str(type(item))
                )

        return int(
            len(set(values))
        )


def _create_default_quality_checks(
    dataset,
    dataframe,
):
    engine = QualityEngine()

    analysis = engine.run_dataframe_checks(
        dataframe=dataframe,
        dataset_name=dataset.name,
        check_config=None,
    )

    suggestions = analysis.get(
        "suggestions",
        [],
    )

    supported_types = {
        QualityCheck.CheckType.NOT_NULL,
        QualityCheck.CheckType.UNIQUE,
        QualityCheck.CheckType.VALID_EMAIL,
        QualityCheck.CheckType.VALID_DATE,
        QualityCheck.CheckType.NUMERIC_VALIDITY,
        QualityCheck.CheckType.RANGE,
        QualityCheck.CheckType.DUPLICATE,
    }

    created_checks = []

    for suggestion in suggestions:
        check_type = suggestion.get("rule")

        if check_type not in supported_types:
            continue

        column_name = str(
            suggestion.get("column") or ""
        )

        quality_check = (
            QualityCheck.objects
            .filter(
                dataset=dataset,
                check_type=check_type,
                column_name=column_name,
            )
            .order_by("id")
            .first()
        )

        if quality_check:
            if not quality_check.is_active:
                quality_check.is_active = True
                quality_check.save(
                    update_fields=[
                        "is_active",
                        "updated_at",
                    ]
                )

            created_checks.append(
                quality_check
            )
            continue

        configuration = {}

        for key, value in suggestion.items():
            if key not in {
                "rule",
                "column",
            }:
                configuration[key] = value

        column_label = (
            column_name
            or "dataset"
        )

        quality_check = QualityCheck.objects.create(
            dataset=dataset,
            name=(
                f"{check_type.replace('_', ' ').title()} "
                f"- {column_label}"
            ),
            check_type=check_type,
            column_name=column_name,
            configuration=configuration,
            is_active=True,
        )

        created_checks.append(
            quality_check
        )

    if created_checks:
        return created_checks

    for column in dataframe.columns:
        column_name = str(column)

        quality_check = (
            QualityCheck.objects
            .filter(
                dataset=dataset,
                check_type=QualityCheck.CheckType.NOT_NULL,
                column_name=column_name,
            )
            .order_by("id")
            .first()
        )

        if quality_check is None:
            quality_check = QualityCheck.objects.create(
                dataset=dataset,
                name=f"Not Null - {column_name}",
                check_type=QualityCheck.CheckType.NOT_NULL,
                column_name=column_name,
                configuration={},
                is_active=True,
            )
        elif not quality_check.is_active:
            quality_check.is_active = True
            quality_check.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

        created_checks.append(
            quality_check
        )

    duplicate_check = (
        QualityCheck.objects
        .filter(
            dataset=dataset,
            check_type=QualityCheck.CheckType.DUPLICATE,
            column_name="",
        )
        .order_by("id")
        .first()
    )

    if duplicate_check is None:
        duplicate_check = QualityCheck.objects.create(
            dataset=dataset,
            name="Duplicate Rows - dataset",
            check_type=QualityCheck.CheckType.DUPLICATE,
            column_name="",
            configuration={},
            is_active=True,
        )
    elif not duplicate_check.is_active:
        duplicate_check.is_active = True
        duplicate_check.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    created_checks.append(
        duplicate_check
    )

    return created_checks


def _create_pipeline(dataset):
    pipeline = (
        Pipeline.objects
        .filter(dataset=dataset)
        .order_by("id")
        .first()
    )

    if pipeline:
        if pipeline.status != Pipeline.Status.ACTIVE:
            pipeline.status = Pipeline.Status.ACTIVE
            pipeline.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return pipeline

    return Pipeline.objects.create(
        name=f"{dataset.name} Quality Pipeline",
        description=(
            "Automatic data-quality monitoring pipeline."
        ),
        dataset=dataset,
        status=Pipeline.Status.ACTIVE,
        schedule="",
    )


def _create_dataset_from_upload(request):
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        raise ValueError("Please select a dataset file.")

    original_name = uploaded_file.name or ""
    if "." not in original_name:
        raise ValueError("Unsupported dataset format. Please upload CSV, JSON, Excel, Parquet, TSV, or XML.")

    extension = Path(original_name).suffix.lower()
    supported_formats = UniversalLoader.SUPPORTED_FORMATS

    if extension not in supported_formats:
        raise ValueError(
            f"Unsupported dataset format '{extension}'. "
            "Supported formats are CSV, JSON, Excel, Parquet, TSV, and XML."
        )

    file_format = supported_formats[extension]
    name = (request.POST.get("name", "").strip() or Path(original_name).stem)
    description = request.POST.get("description", "").strip()

    upload_directory = Path(settings.MEDIA_ROOT) / "datasets"
    upload_directory.mkdir(parents=True, exist_ok=True)

    safe_filename = get_valid_filename(original_name)
    if not safe_filename:
        raise ValueError("The uploaded file has an invalid filename.")

    file_path = upload_directory / safe_filename
    if file_path.exists():
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        file_path = upload_directory / f"{Path(safe_filename).stem}_{timestamp}{Path(safe_filename).suffix}"

    try:
        with file_path.open("wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        loader = UniversalLoader()
        dataframe = loader.read(source=str(file_path), file_format=file_format)

        if dataframe.empty:
            raise ValueError("The uploaded dataset contains no rows.")
        if len(dataframe.columns) == 0:
            raise ValueError("The uploaded dataset contains no columns.")

        source_type_map = {
            "CSV": DataSource.SourceType.CSV,
            "JSON": DataSource.SourceType.JSON,
            "EXCEL": DataSource.SourceType.EXCEL,
            "PARQUET": DataSource.SourceType.PARQUET,
            "TSV": DataSource.SourceType.TSV,
            "XML": DataSource.SourceType.XML,
        }
        source_type = source_type_map[file_format]
        file_size = file_path.stat().st_size

        with transaction.atomic():
            data_source = DataSource.objects.create(
                name=f"{name} Source",
                source_type=source_type,
            )
            dataset = Dataset.objects.create(
                name=name,
                description=description,
                owner=request.user,
                data_source=data_source,
                file_path=str(file_path),
                file_format=file_format,
                file_size=file_size,
                row_count=len(dataframe),
                column_count=len(dataframe.columns),
                is_active=True,
                last_processed_at=timezone.now(),
                schema_snapshot=_build_schema_snapshot(dataframe),
            )
            pipeline = _create_pipeline(dataset)
            _create_default_quality_checks(dataset, dataframe)

        return dataset, pipeline

    except ValueError:
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as exc:
        if file_path.exists():
            file_path.unlink()
        raise ValueError(f"Unable to create dataset from uploaded file: {exc}") from exc


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard_page")

    demo_metrics = {
        "datasets": 12,
        "pipelines": 8,
        "pipeline_runs": 247,
        "quality_score": 94.6,
        "open_issues": 3,
    }

    quality_trend_data = [
        {"date": "Mon", "score": 82},
        {"date": "Tue", "score": 88},
        {"date": "Wed", "score": 85},
        {"date": "Thu", "score": 92},
        {"date": "Fri", "score": 94},
        {"date": "Sat", "score": 91},
        {"date": "Sun", "score": 95},
    ]

    pipeline_health = [
        {
            "name": "Customer Data Pipeline",
            "status": "HEALTHY",
            "quality_score": 98.2,
        },
        {
            "name": "Sales Analytics Pipeline",
            "status": "HEALTHY",
            "quality_score": 96.4,
        },
        {
            "name": "Product Inventory Pipeline",
            "status": "WARNING",
            "quality_score": 78.5,
        },
        {
            "name": "Marketing Events Pipeline",
            "status": "CRITICAL",
            "quality_score": 42.3,
        },
    ]

    return render(
        request,
        "landing.html",
        {
            "demo_metrics": demo_metrics,
            "quality_trend_data": quality_trend_data,
            "pipeline_health": pipeline_health,
        },
    )


@login_required
def user_dashboard(request):
    datasets = _dataset_queryset(request)
    pipelines = _pipeline_queryset(request)
    runs = _run_queryset(request)
    issues_queryset = _issue_queryset(request)

    total_datasets = datasets.count()
    total_pipelines = pipelines.count()
    total_runs = runs.count()

    successful_runs = runs.filter(
        status=PipelineRun.Status.SUCCESS
    ).count()

    failed_runs = runs.filter(
        status=PipelineRun.Status.FAILED
    ).count()

    running_runs = runs.filter(
        status=PipelineRun.Status.RUNNING
    ).count()

    open_issues = issues_queryset.filter(
        status=QualityIssue.Status.OPEN
    ).count()

    acknowledged_issues = issues_queryset.filter(
        status=QualityIssue.Status.ACKNOWLEDGED
    ).count()

    resolved_issues = issues_queryset.filter(
        status=QualityIssue.Status.RESOLVED
    ).count()

    average_quality = (
        runs
        .filter(
            quality_score__isnull=False
        )
        .aggregate(
            value=Avg("quality_score")
        )["value"]
    )

    if average_quality is not None:
        average_quality = round(
            float(average_quality),
            1,
        )

    total_checks = QualityResult.objects.filter(
        pipeline_run__pipeline__dataset__owner=request.user,
        pipeline_run__pipeline__dataset__is_active=True,
    ).count()

    passed_checks = QualityResult.objects.filter(
        pipeline_run__pipeline__dataset__owner=request.user,
        pipeline_run__pipeline__dataset__is_active=True,
        passed=True,
    ).count()

    failed_checks = QualityResult.objects.filter(
        pipeline_run__pipeline__dataset__owner=request.user,
        pipeline_run__pipeline__dataset__is_active=True,
        passed=False,
    ).count()

    issue_severity = {
        "critical": issues_queryset.filter(
            severity=QualityIssue.Severity.CRITICAL
        ).count(),
        "high": issues_queryset.filter(
            severity=QualityIssue.Severity.HIGH
        ).count(),
        "medium": issues_queryset.filter(
            severity=QualityIssue.Severity.MEDIUM
        ).count(),
        "low": issues_queryset.filter(
            severity=QualityIssue.Severity.LOW
        ).count(),
    }

    latest_run = runs.first()

    recent_runs = list(runs[:5])

    quality_trend_data = [
        {
            "id": run.id,
            "quality_score": (
                float(run.quality_score)
                if run.quality_score is not None
                else None
            ),
            "date": run.started_at.strftime(
                "%b %d"
            ),
        }
        for run in recent_runs
    ]

    recent_issues = list(
        issues_queryset[:5]
    )

    pipeline_health = []

    for pipeline in pipelines[:5]:
        latest_pipeline_run = (
            pipeline.runs
            .order_by("-started_at")
            .first()
        )

        if latest_pipeline_run is None:
            health_status = "NO_RUN"

        elif (
            latest_pipeline_run.status
            == PipelineRun.Status.RUNNING
        ):
            health_status = "RUNNING"

        elif (
            latest_pipeline_run.status
            == PipelineRun.Status.FAILED
        ):
            health_status = "FAILED"

        elif (
            latest_pipeline_run.quality_score is not None
            and float(
                latest_pipeline_run.quality_score
            ) < 50
        ):
            health_status = "CRITICAL"

        elif (
            latest_pipeline_run.quality_score is not None
            and float(
                latest_pipeline_run.quality_score
            ) < 80
        ):
            health_status = "WARNING"

        else:
            health_status = "HEALTHY"

        pipeline_health.append(
            {
                "pipeline": pipeline,
                "latest_run": latest_pipeline_run,
                "health_status": health_status,
            }
        )

    if total_datasets == 0:
        dashboard_state = "new"

    elif total_pipelines == 0:
        dashboard_state = "dataset_added"

    elif total_runs == 0:
        dashboard_state = "pipeline_created"

    else:
        dashboard_state = "active"

    if dashboard_state == "new":
        getting_started_step = 1

    elif dashboard_state == "dataset_added":
        getting_started_step = 2

    elif dashboard_state == "pipeline_created":
        getting_started_step = 3

    else:
        getting_started_step = 4

    quality_percentage = 0

    if total_checks:
        quality_percentage = round(
            (passed_checks / total_checks) * 100,
            1,
        )

    success_rate = 0

    if total_runs:
        success_rate = round(
            (successful_runs / total_runs) * 100,
            1,
        )

    return render(
        request,
        "dashboard.html",
        {
            "dashboard_state": dashboard_state,
            "getting_started_step": getting_started_step,

            "total_datasets": total_datasets,
            "total_pipelines": total_pipelines,
            "total_runs": total_runs,

            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "running_runs": running_runs,
            "success_rate": success_rate,

            "average_quality": average_quality,
            "quality_percentage": quality_percentage,

            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,

            "open_issues": open_issues,
            "acknowledged_issues": acknowledged_issues,
            "resolved_issues": resolved_issues,
            "issue_severity": issue_severity,

            "latest_run": latest_run,
            "recent_runs": recent_runs,
            "quality_trend_data": quality_trend_data,
            "recent_issues": recent_issues,

            "datasets": datasets[:5],
            "pipelines": pipelines[:5],
            "pipeline_health": pipeline_health,
        },
    )


@login_required
def datasets_page(request):
    if request.method == "POST":
        try:
            dataset, pipeline = _create_dataset_from_upload(
                request
            )

            check_count = (
                dataset.quality_checks
                .filter(is_active=True)
                .count()
            )

            messages.success(
                request,
                (
                    f'Dataset "{dataset.name}" '
                    f"uploaded successfully with "
                    f"{check_count} quality checks "
                    f'and pipeline "{pipeline.name}".'
                ),
            )

            return redirect(
                "dataset_detail_page",
                dataset_id=dataset.id,
            )

        except ValueError as exc:
            messages.error(
                request,
                str(exc),
            )

            return redirect(
                "datasets_page"
            )

        except Exception as exc:
            messages.error(
                request,
                f"Dataset setup failed: {exc}",
            )

            return redirect(
                "datasets_page"
            )

    datasets = _dataset_queryset(
        request
    )

    total_datasets = datasets.count()

    total_pipelines = (
        Pipeline.objects
        .filter(
            dataset__owner=request.user,
            dataset__is_active=True,
        )
        .count()
    )

    total_checks = (
        QualityCheck.objects
        .filter(
            dataset__owner=request.user,
            dataset__is_active=True,
            is_active=True,
        )
        .count()
    )

    average_quality = (
        PipelineRun.objects
        .filter(
            pipeline__dataset__owner=request.user,
            pipeline__dataset__is_active=True,
            quality_score__isnull=False,
        )
        .aggregate(
            value=Avg("quality_score")
        )["value"]
    )

    if average_quality is not None:
        average_quality = round(
            float(average_quality),
            1,
        )

    return render(
        request,
        "datasets.html",
        {
            "datasets": datasets,
            "total_datasets": total_datasets,
            "total_pipelines": total_pipelines,
            "total_checks": total_checks,
            "average_quality": average_quality,
        },
    )

@login_required
def runs_page(request):
    runs = _run_queryset(request)

    return render(
        request,
        "runs.html",
        {
            "runs": runs,
        },
    )
@login_required
def pipelines_page(request):
    pipelines = _pipeline_queryset(request)
    datasets = _dataset_queryset(request)

    return render(
        request,
        "pipelines.html",
        {
            "pipelines": pipelines,
            "datasets": datasets,
        },
    )


@require_POST
@login_required
def create_pipeline(request):
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    dataset_id = request.POST.get("dataset_id", "").strip()
    schedule = request.POST.get("schedule", "").strip()

    if not name:
        messages.error(request, "Pipeline name is required.")
        return redirect("pipelines_page")

    if len(name) > 150:
        messages.error(
            request,
            "Pipeline name must be 150 characters or fewer.",
        )
        return redirect("pipelines_page")

    if not dataset_id:
        messages.error(request, "Please select a dataset.")
        return redirect("pipelines_page")

    try:
        dataset = Dataset.objects.get(
            id=dataset_id,
            owner=request.user,
            is_active=True,
        )
    except Dataset.DoesNotExist:
        messages.error(
            request,
            "The selected dataset is not available.",
        )
        return redirect("pipelines_page")

    pipeline = Pipeline.objects.create(
        name=name,
        description=description,
        dataset=dataset,
        status=Pipeline.Status.ACTIVE,
        schedule=schedule,
    )

    messages.success(
        request,
        f'Pipeline "{pipeline.name}" was created successfully.',
    )

    return redirect(
        "pipeline_detail_page",
        pipeline_id=pipeline.id,
    )

@login_required
def issues_page(request):
    severity = (
        request.GET.get(
            "severity",
            "",
        )
        .strip()
        .upper()
    )

    status = (
        request.GET.get(
            "status",
            "",
        )
        .strip()
        .upper()
    )

    issues_queryset = _issue_queryset(
        request
    )

    if severity:
        issues_queryset = issues_queryset.filter(
            severity=severity
        )

    if status:
        issues_queryset = issues_queryset.filter(
            status=status
        )

    return render(
        request,
        "issues.html",
        {
            "issues": issues_queryset,
            "selected_severity": severity,
            "selected_status": status,
        },
    )


@require_GET
def health_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "DataSentinel",
        }
    )


@require_POST
@login_required
def analyze_dataset(request):
    uploaded_file = request.FILES.get(
        "file"
    )

    if uploaded_file is None:
        return JsonResponse(
            {
                "error": "No CSV file was uploaded."
            },
            status=400,
        )

    if not uploaded_file.name.lower().endswith(
        ".csv"
    ):
        return JsonResponse(
            {
                "error": "Only CSV files are supported."
            },
            status=400,
        )

    try:
        dataframe = pd.read_csv(
            uploaded_file
        )

        if dataframe.empty:
            return JsonResponse(
                {
                    "error": (
                        "The uploaded CSV file "
                        "contains no rows."
                    )
                },
                status=400,
            )

        if len(dataframe.columns) == 0:
            return JsonResponse(
                {
                    "error": (
                        "The uploaded CSV file "
                        "contains no columns."
                    )
                },
                status=400,
            )

        engine = QualityEngine()

        result = engine.run_dataframe_checks(
            dataframe=dataframe,
            dataset_name=uploaded_file.name,
            check_config=None,
        )

        return JsonResponse(
            result,
            status=200,
        )

    except Exception as exc:
        return JsonResponse(
            {
                "error": "Dataset analysis failed.",
                "details": str(exc),
            },
            status=500,
        )


@require_POST
@login_required
def run_pipeline(
    request,
    pipeline_id,
):
    pipeline = get_object_or_404(
        Pipeline.objects.select_related(
            "dataset"
        ),
        id=pipeline_id,
        dataset__owner=request.user,
        dataset__is_active=True,
    )

    try:
        pipeline_run = (
            PipelineService()
            .run_pipeline(
                pipeline.id
            )
        )

        return JsonResponse(
            {
                "message": (
                    "Pipeline executed successfully."
                ),
                "run": {
                    "id": pipeline_run.id,
                    "pipeline_id": (
                        pipeline_run.pipeline.id

                    ),
                    "pipeline": (
                        pipeline_run.pipeline.name
                    ),
                    "dataset": (
                        pipeline_run.pipeline.dataset.name
                    ),
                    "status": pipeline_run.status,
                    "rows_processed": (
                        pipeline_run.rows_processed
                    ),
                    "quality_score": (
                        float(
                            pipeline_run.quality_score
                        )
                        if pipeline_run.quality_score is not None
                        else None
                    ),
                    "reliability_score": (
                        float(
                            pipeline_run.reliability_score
                        )
                        if pipeline_run.reliability_score is not None
                        else None
                    ),
                    "reliability_grade": (
                        pipeline_run.reliability_grade
                    ),
                    "reliability_status": (
                        pipeline_run.reliability_status
                    ),
                    "started_at": (
                        pipeline_run.started_at
                    ),
                    "completed_at": (
                        pipeline_run.completed_at
                    ),
                },
            },
            status=200,
        )

    except ValueError as exc:
        return JsonResponse(
            {
                "error": str(exc)
            },
            status=400,
        )

    except Exception as exc:
        return JsonResponse(
            {
                "error": (
                    "Pipeline execution failed."
                ),
                "details": str(exc),
            },
            status=500,
        )

@require_GET
@login_required
def pipeline_runs(
    request
):
    runs = _run_queryset(
        request
    )

    data = [
        {
            "id": run.id,
            "pipeline": run.pipeline.name,
            "dataset": run.pipeline.dataset.name,
            "status": run.status,
            "rows_processed": (
                run.rows_processed
            ),
            "quality_score": (
                float(
                    run.quality_score
                )
                if run.quality_score is not None
                else None
            ),
            "reliability_score": (
                float(
                    run.reliability_score
                )
                if run.reliability_score is not None
                else None
            ),
            "reliability_grade": (
                run.reliability_grade
            ),
            "reliability_status": (
                run.reliability_status
            ),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }
        for run in runs
    ]

    return JsonResponse(
        {
            "count": len(data),
            "runs": data,
        }
    )
@require_GET
@login_required
def pipeline_run_detail(request, run_id):
    try:
        run = (
            PipelineRun.objects
            .select_related("pipeline", "pipeline__dataset")
            .get(
                id=run_id,
                pipeline__dataset__owner=request.user,
                pipeline__dataset__is_active=True,
            )
        )
    except PipelineRun.DoesNotExist:
        return JsonResponse(
            {"error": "Pipeline run not found."},
            status=404,
        )

    results = (
        run.quality_results
        .select_related("quality_check")
        .prefetch_related("issues")
        .order_by("id")
    )

    checks = []
    for result in results:
        checks.append(
            {
                "id": result.id,
                "check_name": result.quality_check.name,
                "check_type": result.quality_check.check_type,
                "column": result.quality_check.column_name,
                "passed": result.passed,
                "rows_checked": result.rows_checked,
                "rows_passed": result.rows_passed,
                "rows_failed": result.rows_failed,
                "pass_rate": (
                    float(result.pass_rate)
                    if result.pass_rate is not None
                    else 0.0
                ),
                "details": result.details,
                "executed_at": result.executed_at,
                "issues": [
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "description": issue.description,
                        "severity": issue.severity,
                        "status": issue.status,
                        "ai_analysis": issue.ai_analysis,
                        "ai_recommendation": issue.ai_recommendation,
                        "created_at": issue.created_at,
                        "resolved_at": issue.resolved_at,
                    }
                    for issue in result.issues.all()
                ],
            }
        )

    passed_checks = sum(1 for check in checks if check["passed"])
    failed_checks = len(checks) - passed_checks

    reliability_metadata = (
        run.metadata.get("reliability", {})
        if isinstance(run.metadata, dict)
        else {}
    )

    rca_metadata = (
        run.metadata.get("rca", {})
        if isinstance(run.metadata, dict)
        else {}
    )

    return JsonResponse(
        {
            "id": run.id,
            "pipeline": {
                "id": run.pipeline.id,
                "name": run.pipeline.name,
            },
            "dataset": {
                "id": run.pipeline.dataset.id,
                "name": run.pipeline.dataset.name,
            },
            "status": run.status,
            "rows_processed": run.rows_processed,
            "quality_score": (
                float(run.quality_score)
                if run.quality_score is not None
                else None
            ),
            "reliability": {
                "score": (
                    float(run.reliability_score)
                    if run.reliability_score is not None
                    else None
                ),
                "grade": run.reliability_grade,
                "status": run.reliability_status,
                "breakdown": reliability_metadata.get("breakdown", {}),
                "reasons": reliability_metadata.get("reasons", []),
            },
            "rca": rca_metadata,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "error_message": run.error_message,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
            },
        }
    )



@require_GET
@login_required
def pipelines(request):
    pipelines_queryset = _pipeline_queryset(
        request
    )

    pipelines_data = []

    for pipeline in pipelines_queryset:
        latest_run = (
            pipeline.runs
            .order_by("-started_at")
            .first()
        )

        pipelines_data.append(
            {
                "id": pipeline.id,
                "name": pipeline.name,
                "description": pipeline.description,
                "status": pipeline.status,
                "dataset": {
                    "id": pipeline.dataset.id,
                    "name": pipeline.dataset.name,
                },
                "run_count": pipeline.run_count,
                "quality_score": (
                    round(
                        float(
                            pipeline.average_quality
                        ),
                        2,
                    )
                    if pipeline.average_quality is not None
                    else None
                ),
                "last_run_at": (
                    latest_run.started_at
                    if latest_run
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "count": len(pipelines_data),
            "pipelines": pipelines_data,
        }
    )


@login_required
def pipeline_runs_page(request):
    runs = _run_queryset(request)

    return render(
        request,
        "pipeline_runs.html",
        {
            "runs": runs,
        },
    )


@login_required
def pipeline_run_detail_page(
    request,
    run_id,
):
    pipeline_run = get_object_or_404(
        PipelineRun.objects.select_related(
            "pipeline",
            "pipeline__dataset",
        ),
        id=run_id,
        pipeline__dataset__owner=request.user,
        pipeline__dataset__is_active=True,
    )

    results = (
        pipeline_run.quality_results
        .select_related("quality_check")
        .prefetch_related("issues")
        .order_by("id")
    )

    passed_checks = results.filter(
        passed=True
    ).count()

    failed_checks = results.filter(
        passed=False
    ).count()

    total_checks = results.count()

    return render(
        request,
        "pipeline_run_detail.html",
        {
            "pipeline_run": pipeline_run,
            "results": results,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_checks": total_checks,
            "quality_score": (
                pipeline_run.quality_score
            ),
        },
    )


@require_POST
@login_required
def update_issue(
    request,
    issue_id,
):
    issue = get_object_or_404(
        QualityIssue.objects.select_related(
            "quality_result__pipeline_run__pipeline__dataset"
        ),
        id=issue_id,
        quality_result__pipeline_run__pipeline__dataset__owner=request.user,
        quality_result__pipeline_run__pipeline__dataset__is_active=True,
    )

    if issue.status == QualityIssue.Status.RESOLVED:
        messages.info(
            request,
            "This issue is already resolved.",
        )

        return redirect(
            "issues_page"
        )

    issue.status = QualityIssue.Status.RESOLVED
    issue.resolved_at = timezone.now()

    issue.save(
        update_fields=[
            "status",
            "resolved_at",
        ]
    )

    messages.success(
        request,
        "Issue resolved successfully.",
    )

    return redirect(
        "issues_page"
    )


@require_GET
@login_required
def dashboard(request):
    runs = _run_queryset(request)

    total_runs = runs.count()

    successful_runs = runs.filter(
        status=PipelineRun.Status.SUCCESS
    ).count()

    failed_runs = runs.filter(
        status=PipelineRun.Status.FAILED
    ).count()

    average_quality_score = (
        runs.filter(
            quality_score__isnull=False
        )
        .aggregate(
            value=Avg("quality_score")
        )["value"]
    )

    if average_quality_score is not None:
        average_quality_score = round(
            float(average_quality_score),
            2,
        )

    results_queryset = QualityResult.objects.filter(
        pipeline_run__pipeline__dataset__owner=request.user,
        pipeline_run__pipeline__dataset__is_active=True,
    )

    total_checks = results_queryset.count()

    passed_checks = results_queryset.filter(
        passed=True
    ).count()

    failed_checks = results_queryset.filter(
        passed=False
    ).count()

    open_issues_queryset = QualityIssue.objects.filter(
        quality_result__pipeline_run__pipeline__dataset__owner=request.user,
        quality_result__pipeline_run__pipeline__dataset__is_active=True,
        status=QualityIssue.Status.OPEN,
    )

    open_issues = open_issues_queryset.count()

    issue_severity = {
        "CRITICAL": open_issues_queryset.filter(
            severity=QualityIssue.Severity.CRITICAL
        ).count(),
        "HIGH": open_issues_queryset.filter(
            severity=QualityIssue.Severity.HIGH
        ).count(),
        "MEDIUM": open_issues_queryset.filter(
            severity=QualityIssue.Severity.MEDIUM
        ).count(),
        "LOW": open_issues_queryset.filter(
            severity=QualityIssue.Severity.LOW
        ).count(),
    }

    latest_run = None

    if runs.exists():
        run = runs.first()

        latest_run = {
            "id": run.id,
            "pipeline": run.pipeline.name,
            "dataset": run.pipeline.dataset.name,
            "status": run.status,
            "rows_processed": (
                run.rows_processed
            ),
            "quality_score": (
                float(run.quality_score)
                if run.quality_score is not None
                else None
            ),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

    recent_runs = [
        {
            "id": run.id,
            "pipeline": run.pipeline.name,
            "dataset": run.pipeline.dataset.name,
            "status": run.status,
            "rows_processed": (
                run.rows_processed
            ),
            "quality_score": (
                float(run.quality_score)
                if run.quality_score is not None
                else None
            ),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }
        for run in runs[:10]
    ]

    return JsonResponse(
        {
            "service": "DataSentinel",
            "overview": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "average_quality_score": (
                    average_quality_score
                ),
            },
            "quality": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks,
                "open_issues": open_issues,
                "issue_severity": issue_severity,
            },
            "latest_run": latest_run,
            "recent_runs": recent_runs,
        }
    )


@require_GET
@login_required
def issues(request):
    issues_queryset = _issue_queryset(
        request
    )

    issues_data = []

    for issue in issues_queryset:
        quality_result = issue.quality_result
        run = quality_result.pipeline_run
        pipeline = run.pipeline
        dataset = pipeline.dataset
        quality_check = quality_result.quality_check

        issues_data.append(
            {
                "id": issue.id,
                "run_id": run.id,
                "pipeline": {
                    "id": pipeline.id,
                    "name": pipeline.name,
                },
                "dataset": {
                    "id": dataset.id,
                    "name": dataset.name,
                },
                "check": {
                    "id": quality_result.id,
                    "name": quality_check.name,
                    "type": quality_check.check_type,
                    "column": (
                        quality_check.column_name
                    ),
                },
                "title": issue.title,
                "description": issue.description,
                "severity": issue.severity,
                "status": issue.status,
                "ai_analysis": issue.ai_analysis,
                "ai_recommendation": (
                    issue.ai_recommendation
                ),
                "created_at": issue.created_at,
                "resolved_at": issue.resolved_at,
            }
        )

    return JsonResponse(
        {
            "count": len(issues_data),
            "issues": issues_data,
        }
    )


@require_GET
@login_required
def issue_detail(
    request,
    issue_id,
):
    try:
        issue = _issue_queryset(
            request
        ).get(
            id=issue_id
        )

    except QualityIssue.DoesNotExist:
        return JsonResponse(
            {
                "error": "Issue not found."
            },
            status=404,
        )

    quality_result = issue.quality_result
    run = quality_result.pipeline_run
    quality_check = quality_result.quality_check

    return JsonResponse(
        {
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "severity": issue.severity,
            "status": issue.status,
            "ai_analysis": issue.ai_analysis,
            "ai_recommendation": (
                issue.ai_recommendation
            ),
            "created_at": issue.created_at,
            "resolved_at": issue.resolved_at,
            "run": {
                "id": run.id,
                "status": run.status,
                "quality_score": (
                    float(run.quality_score)
                    if run.quality_score is not None
                    else None
                ),
            },
            "check": {
                "id": quality_result.id,
                "name": quality_check.name,
                "type": quality_check.check_type,
                "column": (
                    quality_check.column_name
                ),
                "passed": quality_result.passed,
                "rows_checked": (
                    quality_result.rows_checked
                ),
                "rows_passed": (
                    quality_result.rows_passed
                ),
                "rows_failed": (
                    quality_result.rows_failed
                ),
                "pass_rate": float(
                    quality_result.pass_rate
                ),
                "details": quality_result.details,
            },
        }
    )


@login_required
def pipeline_detail_page(request, pipeline_id):
    pipeline = get_object_or_404(
        Pipeline.objects.select_related("dataset"),
        id=pipeline_id,
        dataset__owner=request.user,
        dataset__is_active=True,
    )

    runs = (
        PipelineRun.objects
        .filter(pipeline=pipeline)
        .order_by("-started_at")
    )

    latest_run = runs.first()

    latest_results = (
        latest_run.quality_results
        .select_related("quality_check")
        .prefetch_related("issues")
        .order_by("id")
        if latest_run
        else QualityResult.objects.none()
    )

    quality_checks = (
        pipeline.dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    total_runs = runs.count()

    average_quality = (
        runs
        .filter(quality_score__isnull=False)
        .aggregate(value=Avg("quality_score"))["value"]
    )

    if average_quality is not None:
        average_quality = round(
            float(average_quality),
            2,
        )

    passed_checks = (
        latest_results.filter(passed=True).count()
        if latest_run
        else 0
    )

    failed_checks = (
        latest_results.filter(passed=False).count()
        if latest_run
        else 0
    )

    return render(
        request,
        "pipeline_detail.html",
        {
            "pipeline": pipeline,
            "runs": runs,
            "latest_run": latest_run,
            "latest_results": latest_results,
            "quality_checks": quality_checks,
            "total_runs": total_runs,
            "average_quality": average_quality,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        },
    )

@require_GET
@login_required
def pipeline_detail(
    request,
    pipeline_id,
):
    try:
        pipeline = (
            Pipeline.objects
            .select_related(
                "dataset",
                "dataset__data_source",
            )
            .get(
                id=pipeline_id,
                dataset__owner=request.user,
                dataset__is_active=True,
            )
        )
    except Pipeline.DoesNotExist:
        return JsonResponse(
            {
                "error": "Pipeline not found."
            },
            status=404,
        )

    runs = (
        PipelineRun.objects
        .filter(
            pipeline=pipeline
        )
        .order_by("-started_at")
    )

    quality_checks = (
        pipeline.dataset.quality_checks
        .filter(
            is_active=True
        )
        .order_by("id")
    )

    return JsonResponse(
        {
            "id": pipeline.id,
            "name": pipeline.name,
            "description": pipeline.description,
            "status": pipeline.status,
            "schedule": pipeline.schedule,
            "dataset": {
                "id": pipeline.dataset.id,
                "name": pipeline.dataset.name,
                "row_count": (
                    pipeline.dataset.row_count
                ),
                "column_count": (
                    pipeline.dataset.column_count
                ),
            },
            "run_count": runs.count(),
            "quality_checks": [
                {
                    "id": check.id,
                    "name": check.name,
                    "check_type": (
                        check.check_type
                    ),
                    "column_name": (
                        check.column_name
                    ),
                    "configuration": (
                        check.configuration
                    ),
                    "is_active": (
                        check.is_active
                    ),
                }
                for check in quality_checks
            ],
            "runs": [
                {
                    "id": run.id,
                    "status": run.status,
                    "rows_processed": (
                        run.rows_processed
                    ),
                    "quality_score": (
                        float(
                            run.quality_score
                        )
                        if run.quality_score is not None
                        else None
                    ),
                    "reliability_score": (
                        float(
                            run.reliability_score
                        )
                        if run.reliability_score is not None
                        else None
                    ),
                    "reliability_grade": (
                        run.reliability_grade
                    ),
                    "reliability_status": (
                        run.reliability_status
                    ),
                    "started_at": run.started_at,
                    "completed_at": (
                        run.completed_at
                    ),
                }
                for run in runs[:10]
            ],
        }
    )
@require_GET
@login_required
def datasets(request):
    queryset = _dataset_queryset(request)

    datasets_data = [
        {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "source_type": (
                dataset.data_source.source_type
                if dataset.data_source
                else None
            ),
            "file_format": dataset.file_format,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "is_active": dataset.is_active,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "pipeline_count": dataset.pipeline_count,
            "quality_check_count": dataset.quality_check_count,
        }
        for dataset in queryset
    ]

    return JsonResponse(
        {
            "count": len(datasets_data),
            "datasets": datasets_data,
        }
    )

@require_GET
@login_required
def dataset_detail(
    request,
    dataset_id,
):
    try:
        dataset = (
            Dataset.objects
            .select_related(
                "data_source",
                "owner",
            )
            .get(
                id=dataset_id,
                owner=request.user,
                is_active=True,
            )
        )

    except Dataset.DoesNotExist:
        return JsonResponse(
            {
                "error": "Dataset not found."
            },
            status=404,
        )

    quality_checks = (
        dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    pipelines = (
        dataset.pipelines
        .order_by("-updated_at")
    )

    return JsonResponse(
        {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "schema_snapshot": (
                dataset.schema_snapshot
            ),
            "is_active": dataset.is_active,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "data_source": (
                {
                    "id": dataset.data_source.id,
                    "name": dataset.data_source.name,
                    "type": (
                        dataset.data_source.source_type
                    ),
                    "is_active": (
                        dataset.data_source.is_active
                    ),
                }
                if dataset.data_source
                else None
            ),
            "quality_checks": [
                {
                    "id": check.id,
                    "name": check.name,
                    "check_type": (
                        check.check_type
                    ),
                    "column_name": (
                        check.column_name
                    ),
                    "configuration": (
                        check.configuration
                    ),
                    "is_active": (
                        check.is_active
                    ),
                }
                for check in quality_checks
            ],
            "pipelines": [
                {
                    "id": pipeline.id,
                    "name": pipeline.name,
                    "description": (
                        pipeline.description
                    ),
                    "status": pipeline.status,
                    "schedule": (
                        pipeline.schedule
                    ),
                    "updated_at": (
                        pipeline.updated_at
                    ),
                }
                for pipeline in pipelines
            ],
            "pipeline_count": pipelines.count(),
            "quality_check_count": (
                quality_checks.count()
            ),
        }
    )


@login_required
def datasets_page_redirect(request):
    return redirect(
        "datasets_page"
    )


@login_required
def dataset_detail_page(
    request,
    dataset_id,
):
    dataset = get_object_or_404(
        Dataset.objects.select_related(
            "data_source",
            "owner",
        ),
        id=dataset_id,
        owner=request.user,
        is_active=True,
    )

    quality_checks = (
        dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    pipelines = (
        dataset.pipelines
        .order_by("-updated_at")
    )

    schema_columns = []

    if dataset.schema_snapshot:
        schema_columns = (
            dataset.schema_snapshot.get(
                "columns",
                [],
            )
        )

    return render(
        request,
        "dataset_detail.html",
        {
            "dataset": dataset,
            "quality_checks": quality_checks,
            "pipelines": pipelines,
            "schema_columns": schema_columns,
        },
    )


@login_required
def quality_checks_page(
    request,
    dataset_id,
):
    dataset = get_object_or_404(
        Dataset,
        id=dataset_id,
        owner=request.user,
        is_active=True,
    )

    quality_checks = (
        dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    form = QualityCheckForm(
        dataset=dataset
    )

    return render(
        request,
        "quality_checks.html",
        {
            "dataset": dataset,
            "quality_checks": quality_checks,
            "form": form,
        },
    )


@require_POST
@login_required
def create_quality_check(
    request,
    dataset_id,
):
    dataset = get_object_or_404(
        Dataset,
        id=dataset_id,
        owner=request.user,
        is_active=True,
    )

    form = QualityCheckForm(
        request.POST,
        dataset=dataset,
    )

    if form.is_valid():
        quality_check = form.save(
            commit=False
        )

        quality_check.dataset = dataset
        quality_check.is_active = True
        quality_check.save()

        messages.success(
            request,
            "Quality check added successfully.",
        )

        return redirect(
            "quality_checks_page",
            dataset_id=dataset.id,
        )

    quality_checks = (
        dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    return render(
        request,
        "quality_checks.html",
        {
            "dataset": dataset,
            "quality_checks": quality_checks,
            "form": form,
        },
        status=400,
    )


@require_POST
@login_required
def run_quality_checks(
    request,
    pipeline_id,
):
    pipeline = get_object_or_404(
        Pipeline.objects.select_related(
            "dataset"
        ),
        id=pipeline_id,
        dataset__owner=request.user,
        dataset__is_active=True,
        status=Pipeline.Status.ACTIVE,
    )

    if not pipeline.dataset.quality_checks.filter(
        is_active=True
    ).exists():
        messages.error(
            request,
            (
                "No active quality checks are "
                "configured for this dataset."
            ),
        )

        return redirect(
            "pipeline_detail_page",
            pipeline_id=pipeline.id,
        )

    try:
        pipeline_run = (
            PipelineService()
            .run_pipeline(
                pipeline.id
            )
        )

        messages.success(
            request,
            (
                "Quality checks completed. "
                f"Score: {pipeline_run.quality_score}%"
            ),
        )

        return redirect(
            "run_detail",
            run_id=pipeline_run.id,
        )

    except ValueError as exc:
        messages.error(
            request,
            f"Quality check execution failed: {exc}",
        )

        return redirect(
            "pipeline_detail_page",
            pipeline_id=pipeline.id,
        )

    except Exception as exc:
        messages.error(
            request,
            (
                "Quality check execution failed: "
                f"{exc}"
            ),
        )

        return redirect(
            "pipeline_detail_page",
            pipeline_id=pipeline.id,
        )


@login_required
def run_detail(
    request,
    run_id,
):
    run = get_object_or_404(
        PipelineRun.objects.select_related(
            "pipeline",
            "pipeline__dataset",
        ),
        id=run_id,
        pipeline__dataset__owner=request.user,
        pipeline__dataset__is_active=True,
    )

    results = (
        QualityResult.objects
        .filter(pipeline_run=run)
        .select_related("quality_check")
        .prefetch_related("issues")
        .order_by("id")
    )

    passed_checks = results.filter(
        passed=True
    ).count()

    failed_checks = results.filter(
        passed=False
    ).count()

    total_checks = results.count()

    return render(
        request,
        "run_detail.html",
        {
            "run": run,
            "results": results,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_checks": total_checks,
            "quality_score": (
                run.quality_score
            ),
        },
    )

@login_required
def alerts(request):
    alerts = Alert.objects.filter(
        pipeline__dataset__owner=request.user
    ).select_related(
        "pipeline",
        "pipeline_run",
    )

    data = []

    for alert in alerts:
        data.append(
            {
                "id": alert.id,
                "pipeline": {
                    "id": alert.pipeline.id,
                    "name": alert.pipeline.name,
                },
                "pipeline_run": (
                    {
                        "id": alert.pipeline_run.id,
                        "status": alert.pipeline_run.status,
                    }
                    if alert.pipeline_run
                    else None
                ),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "status": alert.status,
                "title": alert.title,
                "message": alert.message,
                "metadata": alert.metadata,
                "created_at": alert.created_at,
                "acknowledged_at": alert.acknowledged_at,
                "resolved_at": alert.resolved_at,
            }
        )

    return JsonResponse(
        {
            "count": len(data),
            "alerts": data,
        }
    )
@login_required
def update_alert(request, alert_id):
    if request.method != "PATCH":
        return JsonResponse(
            {
                "error": "Only PATCH requests are allowed."
            },
            status=405,
        )

    alert = (
        Alert.objects
        .select_related(
            "pipeline",
            "pipeline_run",
        )
        .filter(
            id=alert_id,
            pipeline__dataset__owner=request.user,
        )
        .first()
    )

    if alert is None:
        return JsonResponse(
            {
                "error": "Alert not found."
            },
            status=404,
        )

    try:
        data = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {
                "error": "Invalid JSON request body."
            },
            status=400,
        )

    new_status = data.get("status")

    allowed_statuses = {
        Alert.Status.OPEN,
        Alert.Status.ACKNOWLEDGED,
        Alert.Status.RESOLVED,
    }

    if new_status not in allowed_statuses:
        return JsonResponse(
            {
                "error": (
                    "Invalid status. "
                    "Use OPEN, ACKNOWLEDGED, "
                    "or RESOLVED."
                )
            },
            status=400,
        )

    current_status = alert.status

    if current_status == Alert.Status.RESOLVED:
        if new_status != Alert.Status.RESOLVED:
            return JsonResponse(
                {
                    "error": (
                        "A resolved alert cannot be "
                        "moved back to another status."
                    )
                },
                status=400,
            )

    if (
        current_status == Alert.Status.OPEN
        and new_status == Alert.Status.OPEN
    ):
        return JsonResponse(
            {
                "message": "Alert is already open.",
                "alert": {
                    "id": alert.id,
                    "status": alert.status,
                },
            }
        )

    if (
        current_status == Alert.Status.ACKNOWLEDGED
        and new_status == Alert.Status.OPEN
    ):
        return JsonResponse(
            {
                "error": (
                    "An acknowledged alert cannot "
                    "be moved back to OPEN."
                )
            },
            status=400,
        )

    now = timezone.now()

    if new_status == Alert.Status.ACKNOWLEDGED:
        alert.status = Alert.Status.ACKNOWLEDGED

        if alert.acknowledged_at is None:
            alert.acknowledged_at = now

    elif new_status == Alert.Status.RESOLVED:
        alert.status = Alert.Status.RESOLVED

        if alert.acknowledged_at is None:
            alert.acknowledged_at = now

        if alert.resolved_at is None:
            alert.resolved_at = now

    alert.save(
        update_fields=[
            "status",
            "acknowledged_at",
            "resolved_at",
        ]
    )

    return JsonResponse(
        {
            "message": "Alert updated successfully.",
            "alert": {
                "id": alert.id,
                "pipeline": {
                    "id": alert.pipeline.id,
                    "name": alert.pipeline.name,
                },
                "pipeline_run": (
                    {
                        "id": alert.pipeline_run.id,
                        "status": alert.pipeline_run.status,
                    }
                    if alert.pipeline_run
                    else None
                ),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "status": alert.status,
                "title": alert.title,
                "message": alert.message,
                "metadata": alert.metadata,
                "created_at": alert.created_at,
                "acknowledged_at": alert.acknowledged_at,
                "resolved_at": alert.resolved_at,
            },
        }
    )
@login_required
def alerts_page(request):
    alerts_queryset = (
        Alert.objects
        .filter(
            pipeline__dataset__owner=request.user,
        )
        .select_related(
            "pipeline",
            "pipeline_run",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "alerts.html",
        {
            "alerts": alerts_queryset,
        },
    )
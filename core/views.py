import json
import os

from decimal import Decimal

import pandas as pd

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import (get_object_or_404,redirect,render,)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.forms import QualityCheckForm

from core.models import (Dataset,DataSource,Pipeline,PipelineRun,QualityCheck,QualityIssue,QualityResult,)
from core.services.pipeline import PipelineService
from core.services.quality.engine import QualityEngine
from core.services.quality.persistence import (
    QualityPersistenceService,
)



def dashboard_page(request):
    return render(request, "dashboard.html")

def datasets_page(request):
    return render(request, "datasets.html")


def runs_page(request):
    return render(request, "runs.html")


def pipelines_page(request):
    return render(request, "pipelines.html")


def issues_page(request):
    return render(request, "issues.html")

def health_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "DataSentinel",
        }
    )


@csrf_exempt
def analyze_dataset(request):
    

    if request.method != "POST":
        return JsonResponse(
            {
                "error": "Only POST requests are allowed."
            },
            status=405,
        )

    uploaded_file = request.FILES.get("file")

    if uploaded_file is None:
        return JsonResponse(
            {
                "error": "No CSV file was uploaded."
            },
            status=400,
        )

    if not uploaded_file.name.lower().endswith(".csv"):
        return JsonResponse(
            {
                "error": "Only CSV files are supported."
            },
            status=400,
        )

    try:
        import pandas as pd

        dataframe = pd.read_csv(uploaded_file)

        engine = QualityEngine()

        result = engine.run_dataframe_checks(
            dataframe=dataframe,
            dataset_name=uploaded_file.name,
            check_config=None,
        )

        from core.models import Dataset

        dataset = Dataset.objects.filter(
            name=uploaded_file.name
        ).first()

        if dataset is not None:

            pipeline = Pipeline.objects.filter(
                dataset=dataset
            ).first()

            if pipeline is not None:

                persistence = QualityPersistenceService()

                pipeline_run = persistence.save_run(
                    dataset=dataset,
                    pipeline=pipeline,
                    engine_result=result,
                )

                result["persistence"] = {
                    "pipeline_run_id": pipeline_run.id,
                    "dataset_id": dataset.id,
                    "pipeline_id": pipeline.id,
                }

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

@csrf_exempt
def run_pipeline(request, pipeline_id):
    if request.method != "POST":
        return JsonResponse(
            {
                "error": "Only POST requests are allowed."
            },
            status=405,
        )

    try:
        service = PipelineService()

        pipeline_run = service.run_pipeline(pipeline_id)

        return JsonResponse(
            {
                "message": "Pipeline executed successfully.",
                "run": {
                    "id": pipeline_run.id,
                    "pipeline_id": pipeline_run.pipeline.id,
                    "pipeline": pipeline_run.pipeline.name,
                    "dataset": pipeline_run.pipeline.dataset.name,
                    "status": pipeline_run.status,
                    "rows_processed": pipeline_run.rows_processed,
                    "quality_score": (
                        float(pipeline_run.quality_score)
                        if pipeline_run.quality_score is not None
                        else None
                    ),
                    "started_at": pipeline_run.started_at,
                    "completed_at": pipeline_run.completed_at,
                }
            },
            status=200,
        )

    except Pipeline.DoesNotExist:
        return JsonResponse(
            {
                "error": "Pipeline not found."
            },
            status=404,
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
                "error": "Pipeline execution failed.",
                "details": str(exc),
            },
            status=500,
        )


def pipeline_runs(request):
    """
    Return historical quality-analysis runs.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    runs = (
        PipelineRun.objects
        .select_related(
            "pipeline",
            "pipeline__dataset",
        )
        .order_by("-started_at")
    )

    data = []

    for run in runs:
        data.append(
            {
                "id": run.id,
                "pipeline": run.pipeline.name,
                "dataset": run.pipeline.dataset.name,
                "status": run.status,
                "rows_processed": run.rows_processed,
                "quality_score": (
                    float(run.quality_score)
                    if run.quality_score is not None
                    else None
                ),
                "started_at": run.started_at,
                "completed_at": run.completed_at,
            }
        )

    return JsonResponse(
        {
            "count": len(data),
            "runs": data,
        }
    )


@csrf_exempt
def pipeline_run_detail(request, run_id):
    """
    Return detailed results for one pipeline run as JSON.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    try:
        run = (
            PipelineRun.objects
            .select_related(
                "pipeline",
                "pipeline__dataset",
            )
            .get(id=run_id)
        )

    except PipelineRun.DoesNotExist:
        return JsonResponse(
            {
                "error": "Pipeline run not found."
            },
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
                    }
                    for issue in result.issues.all()
                ],
            }
        )

    passed_checks = sum(
        1
        for check in checks
        if check["passed"]
    )

    failed_checks = sum(
        1
        for check in checks
        if not check["passed"]
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


@csrf_exempt
def pipelines(request):
    """
    Return all DataSentinel pipelines as JSON.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    pipelines_data = []

    pipelines_queryset = (
        Pipeline.objects
        .select_related("dataset")
        .order_by("name")
    )

    for pipeline in pipelines_queryset:

        runs = pipeline.runs.all()

        run_count = runs.count()

        latest_run = runs.first()

        quality_scores = [
            float(run.quality_score)
            for run in runs
            if run.quality_score is not None
        ]

        average_quality = (
            round(
                sum(quality_scores) / len(quality_scores),
                2,
            )
            if quality_scores
            else None
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
                "run_count": run_count,
                "quality_score": average_quality,
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


def pipeline_runs_page(request):
    """
    Render the pipeline runs management page.
    """

    return render(
        request,
        "pipeline_runs.html",
    )


def pipeline_run_detail_page(request, run_id):
    """
    Render the detailed pipeline run page.
    """

    pipeline_run = get_object_or_404(
        PipelineRun.objects.select_related(
            "pipeline",
            "pipeline__dataset",
        ),
        id=run_id,
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
            "quality_score": pipeline_run.quality_score,
        },
    )
@csrf_exempt
def update_issue(request, issue_id):
    """
    Update the status of a data-quality issue.
    """

    if request.method != "PATCH":
        return JsonResponse(
            {
                "error": "Only PATCH requests are allowed."
            },
            status=405,
        )

    from core.models import QualityIssue

    try:
        issue = QualityIssue.objects.get(id=issue_id)
    except QualityIssue.DoesNotExist:
        return JsonResponse(
            {
                "error": "Issue not found."
            },
            status=404,
        )

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid JSON."
            },
            status=400,
        )

    new_status = body.get("status")

    allowed_statuses = [
        "OPEN",
        "ACKNOWLEDGED",
        "RESOLVED",
    ]

    if new_status not in allowed_statuses:
        return JsonResponse(
            {
                "error": "Invalid status.",
                "allowed_statuses": allowed_statuses,
            },
            status=400,
        )

    issue.status = new_status
    issue.save(update_fields=["status"])

    return JsonResponse(
        {
            "message": "Issue updated successfully.",
            "issue": {
                "id": issue.id,
                "title": issue.title,
                "severity": issue.severity,
                "status": issue.status,
            },
        }
    )


def dashboard(request):
    """
    Return dashboard overview and analytics.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    runs = (
        PipelineRun.objects
        .select_related(
            "pipeline",
            "pipeline__dataset",
        )
        .prefetch_related(
            "quality_results__issues"
        )
        .order_by("-started_at")
    )

    total_runs = runs.count()

    successful_runs = runs.filter(
        status="SUCCESS"
    ).count()

    failed_runs = runs.filter(
        status="FAILED"
    ).count()

    quality_scores = [
        float(score)
        for score in runs.values_list(
            "quality_score",
            flat=True,
        )
        if score is not None
    ]

    average_quality_score = (
        round(
            sum(quality_scores) / len(quality_scores),
            2,
        )
        if quality_scores
        else None
    )

    total_checks = 0
    passed_checks = 0
    failed_checks = 0
    open_issues = 0

    issue_severity = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    for run in runs:
        for result in run.quality_results.all():

            total_checks += 1

            if result.passed:
                passed_checks += 1
            else:
                failed_checks += 1

            for issue in result.issues.all():

                if issue.status == "OPEN":
                    open_issues += 1

                    severity = str(
                        issue.severity
                    ).upper()

                    if severity in issue_severity:
                        issue_severity[severity] += 1

    latest_run = None

    if runs.exists():
        run = runs.first()

        latest_run = {
            "id": run.id,
            "pipeline": run.pipeline.name,
            "dataset": run.pipeline.dataset.name,
            "status": run.status,
            "rows_processed": run.rows_processed,
            "quality_score": (
                float(run.quality_score)
                if run.quality_score is not None
                else None
            ),
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

    recent_runs = []

    for run in runs[:10]:

        recent_runs.append(
            {
                "id": run.id,
                "pipeline": run.pipeline.name,
                "dataset": run.pipeline.dataset.name,
                "status": run.status,
                "rows_processed": run.rows_processed,
                "quality_score": (
                    float(run.quality_score)
                    if run.quality_score is not None
                    else None
                ),
                "started_at": run.started_at,
                "completed_at": run.completed_at,
            }
        )

    return JsonResponse(
        {
            "service": "DataSentinel",

            "overview": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "average_quality_score": average_quality_score,
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

 
def issues(request):
    """
    Return all data-quality issues.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    issues_data = []

    runs = (
        PipelineRun.objects
        .select_related(
            "pipeline",
            "pipeline__dataset",
        )
        .prefetch_related(
            "quality_results__issues",
            "quality_results__quality_check",
        )
        .order_by("-started_at")
    )

    for run in runs:

        for quality_result in run.quality_results.all():

            for issue in quality_result.issues.all():

                issues_data.append(
                    {
                        "id": issue.id,

                        "run_id": run.id,

                        "pipeline": {
                            "id": run.pipeline.id,
                            "name": run.pipeline.name,
                        },

                        "dataset": {
                            "id": run.pipeline.dataset.id,
                            "name": run.pipeline.dataset.name,
                        },

                        "check": {
                            "id": quality_result.id,
                            "name": (
                                quality_result
                                .quality_check
                                .name
                            ),
                            "type": (
                                quality_result
                                .quality_check
                                .check_type
                            ),
                            "column": (
                                quality_result
                                .quality_check
                                .column_name
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
                    }
                )

    return JsonResponse(
        {
            "count": len(issues_data),
            "issues": issues_data,
        }
    )


def issue_detail(request, issue_id):
    """
    Return detailed information for one issue.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    from core.models import QualityIssue

    try:
        issue = (
            QualityIssue.objects
            .select_related(
                "quality_result",
                "quality_result__pipeline_run",
                "quality_result__quality_check",
            )
            .get(id=issue_id)
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
            "ai_recommendation": issue.ai_recommendation,
            "created_at": issue.created_at,

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
                "column": quality_check.column_name,
                "passed": quality_result.passed,
                "rows_checked": quality_result.rows_checked,
                "rows_passed": quality_result.rows_passed,
                "rows_failed": quality_result.rows_failed,
                "pass_rate": float(
                    quality_result.pass_rate
                ),
                "details": quality_result.details,
            },
        }
    )



@csrf_exempt
def update_issue(request, issue_id):
    """
    Update the status of a data-quality issue.
    """

    if request.method != "PATCH":
        return JsonResponse(
            {
                "error": "Only PATCH requests are allowed."
            },
            status=405,
        )

    try:
        issue = QualityIssue.objects.get(id=issue_id)

    except QualityIssue.DoesNotExist:
        return JsonResponse(
            {
                "error": "Issue not found."
            },
            status=404,
        )

    try:
        data = json.loads(request.body or "{}")

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid JSON request body."
            },
            status=400,
        )

    status_value = data.get("status")

    if not status_value:
        return JsonResponse(
            {
                "error": "Status is required."
            },
            status=400,
        )

    allowed_statuses = [
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
    ]

    if status_value not in allowed_statuses:
        return JsonResponse(
            {
                "error": "Invalid status.",
                "allowed_statuses": allowed_statuses,
            },
            status=400,
        )

    issue.status = status_value
    issue.save(update_fields=["status"])

    return JsonResponse(
        {
            "success": True,
            "message": "Issue status updated successfully.",
            "issue": {
                "id": issue.id,
                "title": issue.title,
                "severity": issue.severity,
                "status": issue.status,
            },
        }
    )
def pipeline_detail_page(request, pipeline_id):
    pipeline = get_object_or_404(
        Pipeline.objects.select_related("dataset"),
        id=pipeline_id,
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
        else []
    )

    total_runs = runs.count()

    quality_scores = [
        float(run.quality_score)
        for run in runs
        if run.quality_score is not None
    ]

    average_quality = (
        round(sum(quality_scores) / len(quality_scores), 2)
        if quality_scores
        else None
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
            "total_runs": total_runs,
            "average_quality": average_quality,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        },
    )

def pipeline_detail(request, pipeline_id):
    """
    Return details for a single pipeline.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    try:
        pipeline = (
            Pipeline.objects
            .select_related(
                "dataset",
                "dataset__data_source",
            )
            .get(id=pipeline_id)
        )

        runs = (
            PipelineRun.objects
            .filter(pipeline=pipeline)
            .order_by("-started_at")
        )

        quality_checks = (
            pipeline.dataset.quality_checks
            .filter(is_active=True)
            .order_by("id")
        )

        return JsonResponse(
            {
                "id": pipeline.id,
                "name": pipeline.name,
                "description": pipeline.description,
                "status": pipeline.status,

                "dataset": {
                    "id": pipeline.dataset.id,
                    "name": pipeline.dataset.name,
                    "row_count": pipeline.dataset.row_count,
                    "column_count": pipeline.dataset.column_count,
                },

                "run_count": runs.count(),

                "quality_checks": [
                    {
                        "id": check.id,
                        "name": check.name,
                        "check_type": check.check_type,
                        "column_name": check.column_name,
                        "configuration": check.configuration,
                        "is_active": check.is_active,
                    }
                    for check in quality_checks
                ],

                "runs": [
                    {
                        "id": run.id,
                        "status": run.status,
                        "rows_processed": run.rows_processed,
                        "quality_score": (
                            float(run.quality_score)
                            if run.quality_score is not None
                            else None
                        ),
                        "started_at": run.started_at,
                        "completed_at": run.completed_at,
                    }
                    for run in runs[:10]
                ],
            }
        )

    except Pipeline.DoesNotExist:
        return JsonResponse(
            {
                "error": "Pipeline not found."
            },
            status=404,
        )
def datasets_page(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        uploaded_file = request.FILES.get("file")

        if not name:
            messages.error(request, "Dataset name is required.")
            return redirect("datasets_page")

        if not uploaded_file:
            messages.error(request, "CSV file is required.")
            return redirect("datasets_page")

        if not uploaded_file.name.lower().endswith(".csv"):
            messages.error(request, "Only CSV files are supported.")
            return redirect("datasets_page")

        try:
            dataframe = pd.read_csv(uploaded_file)
        except Exception as exc:
            messages.error(
                request,
                f"Unable to read CSV file: {exc}",
            )
            return redirect("datasets_page")

        if dataframe.empty:
            messages.error(
                request,
                "The uploaded CSV file contains no rows.",
            )
            return redirect("datasets_page")

        if len(dataframe.columns) == 0:
            messages.error(
                request,
                "The uploaded CSV file contains no columns.",
            )
            return redirect("datasets_page")

        if request.user.is_authenticated:
            owner = request.user
        else:
            owner, _ = User.objects.get_or_create(
                username="datasentinel",
                defaults={
                    "email": "system@datasentinel.local",
                    "is_active": True,
                },
            )

        data_source = DataSource.objects.create(
            name=f"{name} CSV Source",
            source_type=DataSource.SourceType.CSV,
            description=f"CSV source for dataset '{name}'.",
            connection_config={
                "filename": uploaded_file.name,
            },
        )

        upload_directory = os.path.join(
            settings.MEDIA_ROOT,
            "datasets",
        )

        os.makedirs(upload_directory, exist_ok=True)

        safe_name = (
            name.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        safe_filename = f"{owner.id}_{safe_name}.csv"

        file_path = os.path.join(
            upload_directory,
            safe_filename,
        )

        with open(file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        schema_snapshot = {
            "columns": [
                {
                    "name": column,
                    "dtype": str(dataframe[column].dtype),
                    "null_count": int(
                        dataframe[column].isna().sum()
                    ),
                    "null_percentage": round(
                        float(
                            dataframe[column].isna().mean() * 100
                        ),
                        2,
                    ),
                    "unique_count": int(
                        dataframe[column].nunique(
                            dropna=True
                        )
                    ),
                }
                for column in dataframe.columns
            ]
        }

        Dataset.objects.create(
            name=name,
            description=description,
            owner=owner,
            data_source=data_source,
            file_path=file_path,
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            schema_snapshot=schema_snapshot,
        )

        messages.success(
            request,
            f'Dataset "{name}" uploaded successfully.',
        )

        return redirect("datasets_page")

    datasets = (
        Dataset.objects
        .select_related("data_source", "owner")
        .filter(is_active=True)
        .order_by("-updated_at")
    )

    total_datasets = datasets.count()

    total_pipelines = Pipeline.objects.filter(
        dataset__is_active=True
    ).count()

    total_checks = QualityCheck.objects.filter(
        dataset__is_active=True,
        is_active=True,
    ).count()

    quality_scores = list(
        PipelineRun.objects.filter(
            pipeline__dataset__is_active=True,
            quality_score__isnull=False,
        ).values_list(
            "quality_score",
            flat=True,
        )
    )

    average_quality = None

    if quality_scores:
        average_quality = round(
            sum(float(score) for score in quality_scores)
            / len(quality_scores),
            1,
        )

    for dataset in datasets:
        dataset.pipeline_count = dataset.pipelines.count()

        dataset.quality_check_count = (
            dataset.quality_checks
            .filter(is_active=True)
            .count()
        )

    context = {
        "datasets": datasets,
        "total_datasets": total_datasets,
        "total_pipelines": total_pipelines,
        "total_checks": total_checks,
        "average_quality": average_quality,
    }

    return render(
        request,
        "datasets.html",
        context,
    )
@csrf_exempt
def datasets(request):
    """
    List datasets or create a new CSV dataset.
    """

    # GET - LIST DATASETS
    

    if request.method == "GET":

        datasets_data = []

        queryset = (
            Dataset.objects
            .select_related("data_source", "owner")
            .filter(is_active=True)
            .order_by("-updated_at")
        )

        for dataset in queryset:

            datasets_data.append(
                {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": dataset.description,

                    "source_type": (
                        dataset.data_source.source_type
                        if dataset.data_source
                        else None
                    ),

                    "row_count": dataset.row_count,
                    "column_count": dataset.column_count,
                    "is_active": dataset.is_active,

                    "created_at": dataset.created_at,
                    "updated_at": dataset.updated_at,

                    "pipeline_count": dataset.pipelines.count(),

                    "quality_check_count": (
                        dataset.quality_checks
                        .filter(is_active=True)
                        .count()
                    ),
                }
            )

        return JsonResponse(
            {
                "count": len(datasets_data),
                "datasets": datasets_data,
            }
        )

    
    # ONLY GET AND POST ARE ALLOWED

    if request.method != "POST":

        return JsonResponse(
            {
                "error": "Only GET and POST requests are allowed."
            },
            status=405,
        )

    # GET FORM DATA
    

    name = request.POST.get("name", "").strip()

    description = request.POST.get(
        "description",
        ""
    ).strip()

    uploaded_file = request.FILES.get("file")

    # VALIDATION

    if not name:

        return JsonResponse(
            {
                "error": "Dataset name is required."
            },
            status=400,
        )

    if not uploaded_file:

        return JsonResponse(
            {
                "error": "CSV file is required."
            },
            status=400,
        )

    if not uploaded_file.name.lower().endswith(".csv"):

        return JsonResponse(
            {
                "error": "Only CSV files are supported."
            },
            status=400,
        )

    # 
    # READ CSV

    try:

        dataframe = pd.read_csv(uploaded_file)

    except Exception as exc:

        return JsonResponse(
            {
                "error": f"Unable to read CSV file: {exc}"
            },
            status=400,
        )

    if dataframe.empty:

        return JsonResponse(
            {
                "error": "The uploaded CSV file contains no rows."
            },
            status=400,
        )

    if len(dataframe.columns) == 0:

        return JsonResponse(
            {
                "error": "The uploaded CSV file contains no columns."
            },
            status=400,
        )

    # DETERMINE OWNER

    if request.user.is_authenticated:

        owner = request.user

    else:

        owner, _ = User.objects.get_or_create(
            username="datasentinel",
            defaults={
                "email": "system@datasentinel.local",
                "is_active": True,
            },
        )

    # CREATE DATA SOURCE

    data_source = DataSource.objects.create(
        name=f"{name} CSV Source",

        source_type=DataSource.SourceType.CSV,

        description=f"CSV source for dataset '{name}'.",

        connection_config={
            "filename": uploaded_file.name,
        },
    )

    # SAVE CSV FILE

    upload_directory = os.path.join(
        settings.MEDIA_ROOT,
        "datasets",
    )

    os.makedirs(
        upload_directory,
        exist_ok=True,
    )

    safe_filename = (
        f"{owner.id}_{name}"
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        + ".csv"
    )

    file_path = os.path.join(
        upload_directory,
        safe_filename,
    )

    with open(file_path, "wb+") as destination:

        for chunk in uploaded_file.chunks():

            destination.write(chunk)

    # DETECT SCHEMA

    schema_snapshot = {
        "columns": [

            {
                "name": column,

                "dtype": str(
                    dataframe[column].dtype
                ),

                "null_count": int(
                    dataframe[column].isna().sum()
                ),

                "null_percentage": round(
                    float(
                        dataframe[column]
                        .isna()
                        .mean()
                        * 100
                    ),
                    2,
                ),

                "unique_count": int(
                    dataframe[column].nunique(
                        dropna=True
                    )
                ),
            }

            for column in dataframe.columns
        ]
    }

    # CREATE DATASET

    dataset = Dataset.objects.create(

        name=name,

        # IMPORTANT:
        # This was "desscription" in your code.
        description=description,

        owner=owner,

        data_source=data_source,

        file_path=file_path,

        row_count=len(dataframe),

        column_count=len(dataframe.columns),

        schema_snapshot=schema_snapshot,
    )

    # RESPONSE

    return JsonResponse(
        {
            "message": "Dataset uploaded successfully.",

            "dataset": {

                "id": dataset.id,

                "name": dataset.name,

                "description": dataset.description,

                "source_type": data_source.source_type,

                "row_count": dataset.row_count,

                "column_count": dataset.column_count,

                "created_at": dataset.created_at,
            },
        },
        status=201,
    )


# DATASET DETAIL API

def dataset_detail(request, dataset_id):
    """
    Return detailed information about one dataset as JSON.
    """

    if request.method != "GET":

        return JsonResponse(
            {
                "error": "Only GET requests are allowed."
            },
            status=405,
        )

    try:

        dataset = (
            Dataset.objects
            .select_related(
                "data_source",
                "owner",
            )
            .get(
                id=dataset_id,
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

    # QUALITY CHECKS

    quality_checks = (
        dataset.quality_checks
        .filter(is_active=True)
        .order_by("id")
    )

    # PIPELINES

    pipelines = (
        dataset.pipelines
        .order_by("-updated_at")
    )

    
    # RESPONSE

    return JsonResponse(
        {
            "id": dataset.id,

            "name": dataset.name,

            "description": dataset.description,

            # Do not expose this to users in a production UI.
            "file_path": dataset.file_path,

            "row_count": dataset.row_count,

            "column_count": dataset.column_count,

            "schema_snapshot": dataset.schema_snapshot,

            "is_active": dataset.is_active,

            "created_at": dataset.created_at,

            "updated_at": dataset.updated_at,

            "data_source": (

                {
                    "id": dataset.data_source.id,

                    "name": dataset.data_source.name,

                    "type": dataset.data_source.source_type,

                    "is_active": dataset.data_source.is_active,
                }

                if dataset.data_source

                else None
            ),

            "quality_checks": [

                {
                    "id": check.id,

                    "name": check.name,

                    "check_type": check.check_type,

                    "column_name": check.column_name,

                    "configuration": check.configuration,

                    "is_active": check.is_active,
                }

                for check in quality_checks
            ],

            "pipelines": [

                {
                    "id": pipeline.id,

                    "name": pipeline.name,

                    "description": pipeline.description,

                    "status": pipeline.status,

                    "schedule": pipeline.schedule,

                    "updated_at": pipeline.updated_at,
                }

                for pipeline in pipelines
            ],

            "pipeline_count": pipelines.count(),

            "quality_check_count": quality_checks.count(),
        }
    )


# DATASET DETAIL PAGE
def dataset_detail_page(request, dataset_id):
    dataset = get_object_or_404(
        Dataset.objects.select_related(
            "data_source",
            "owner",
        ),
        id=dataset_id,
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
        schema_columns = dataset.schema_snapshot.get("columns", [])

    context = {
        "dataset": dataset,
        "quality_checks": quality_checks,
        "pipelines": pipelines,
        "schema_columns": schema_columns,
    }

    return render(
        request,
        "dataset_detail.html",
        context,
    )

# QUALITY CHECKS PAGE

def quality_checks_page(request, dataset_id):

    dataset = get_object_or_404(
        Dataset,
        id=dataset_id,
    )

    quality_checks = (
        dataset.quality_checks.all()
    )

    form = QualityCheckForm(
        dataset=dataset,
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


# CREATE QUALITY CHECK

def create_quality_check(request, dataset_id):

    dataset = get_object_or_404(
        Dataset,
        id=dataset_id,
    )

    if request.method != "POST":

        return redirect(
            "quality_checks_page",
            dataset_id=dataset.id,
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
        dataset.quality_checks.all()
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
def run_quality_checks(request, pipeline_id):
    pipeline = get_object_or_404(
        Pipeline.objects.select_related("dataset"),
        id=pipeline_id,
        status=Pipeline.Status.ACTIVE,
    )

    dataset = pipeline.dataset

    checks = (
        QualityCheck.objects
        .filter(
            dataset=dataset,
            is_active=True,
        )
        .order_by("id")
    )

    if not checks.exists():
        messages.error(
            request,
            "No active quality checks are configured for this dataset.",
        )

        return redirect(
            "pipeline_detail_page",
            pipeline_id=pipeline.id,
        )

    check_config = [
        {
            "check": check.check_type,
            "column": check.column_name,
            **(check.configuration or {}),
        }
        for check in checks
    ]

    try:
        engine = QualityEngine()

        engine_result = engine.run_csv_checks(
            file_path=dataset.file_path,
            check_config=check_config,
        )

        persistence = QualityPersistenceService()

        pipeline_run = persistence.save_run(
            dataset=dataset,
            pipeline=pipeline,
            engine_result=engine_result,
        )

        messages.success(
            request,
            f"Quality checks completed. "
            f"Score: {pipeline_run.quality_score}%",
        )

        # IMPORTANT:
        # Redirect using the PipelineRun ID
        return redirect(
            "pipeline_run_detail_page",
            run_id=pipeline_run.id,
        )

    except Exception as exc:
        messages.error(
            request,
            f"Quality check execution failed: {exc}",
        )

        return redirect(
            "pipeline_detail_page",
            pipeline_id=pipeline.id,
        )

def pipeline_run_detail_page(request, run_id):
    pipeline_run = get_object_or_404(
        PipelineRun.objects.select_related(
            "pipeline",
            "dataset",
        ),
        id=run_id,
    )

    return render(
        request,
        "pipeline_run_detail.html",
        {
            "pipeline_run": pipeline_run,
            "run_id": pipeline_run.id,
        },
    )
def run_detail(request, run_id):
    run = get_object_or_404(
        PipelineRun.objects.select_related(
            "pipeline",
            "pipeline__dataset",
        ),
        id=run_id,
    )

    results = (
        QualityResult.objects
        .filter(pipeline_run=run)
        .select_related("quality_check")
        .prefetch_related("issues")
        .order_by("id")
    )

    passed_checks = results.filter(passed=True).count()
    failed_checks = results.filter(passed=False).count()

    return render(
        request,
        "run_detail.html",
        {
            "run": run,
            "results": results,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        },
    )
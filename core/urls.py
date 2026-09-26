from django.shortcuts import redirect
from django.urls import path

from core import views


def home(request):

    if request.user.is_authenticated:
        return redirect("dashboard_page")

    return redirect("landing_page")


urlpatterns = [

    path(
        "",
        home,
        name="home",
    ),

    path(
        "dashboard/",
        views.user_dashboard,
        name="dashboard_page",
    ),

    path(
        "datasets/",
        views.datasets_page,
        name="datasets_page",
    ),

    path(
        "datasets/<int:dataset_id>/",
        views.dataset_detail_page,
        name="dataset_detail_page",
    ),

    path(
        "datasets/<int:dataset_id>/quality-checks/",
        views.quality_checks_page,
        name="quality_checks_page",
    ),

    path(
        "datasets/<int:dataset_id>/quality-checks/add/",
        views.create_quality_check,
        name="create_quality_check",
    ),

    path(
        "pipelines/",
        views.pipelines_page,
        name="pipelines_page",
    ),

    path(
        "pipelines/create/",
        views.create_pipeline,
        name="create_pipeline",
    ),

    path(
        "pipelines/<int:pipeline_id>/",
        views.pipeline_detail_page,
        name="pipeline_detail_page",
    ),

    path(
        "pipelines/<int:pipeline_id>/run/",
        views.run_quality_checks,
        name="run_quality_checks",
    ),

    path(
        "runs/",
        views.runs_page,
        name="runs_page",
    ),

    path(
        "runs/<int:run_id>/",
        views.run_detail,
        name="run_detail",
    ),

    path(
        "issues/",
        views.issues_page,
        name="issues_page",
    ),

    path(
        "alerts/",
        views.alerts_page,
        name="alerts_page",
    ),

    path(
        "api/issues/<int:issue_id>/status/",
        views.update_issue,
        name="update_issue",
    ),

    path(
        "api/health/",
        views.health_check,
        name="health_check",
    ),

    path(
        "api/analyze/",
        views.analyze_dataset,
        name="analyze_dataset",
    ),

    path(
        "api/dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "api/datasets/",
        views.datasets,
        name="datasets",
    ),

    path(
        "api/datasets/<int:dataset_id>/",
        views.dataset_detail,
        name="dataset_detail",
    ),

    path(
        "api/pipelines/",
        views.pipelines,
        name="pipelines",
    ),

    path(
        "api/pipelines/<int:pipeline_id>/",
        views.pipeline_detail,
        name="pipeline_detail",
    ),

    path(
        "api/pipelines/<int:pipeline_id>/run/",
        views.run_pipeline,
        name="run_pipeline",
    ),

    path(
        "api/runs/",
        views.pipeline_runs,
        name="pipeline_runs",
    ),

    path(
        "api/runs/<int:run_id>/",
        views.pipeline_run_detail,
        name="pipeline_run_detail",
    ),

    path(
        "api/issues/",
        views.issues,
        name="issues",
    ),

    path(
        "api/issues/<int:issue_id>/",
        views.issue_detail,
        name="issue_detail",
    ),

    path(
        "api/alerts/",
        views.alerts,
        name="alerts",
    ),

    path(
        "api/alerts/<int:alert_id>/",
        views.update_alert,
        name="update_alert",
    ),
]
let qualityTrendChart = null;

let checkResultsChart = null;


async function loadDashboardData() {

    try {

        const response = await fetch("/api/dashboard/");

        if (!response.ok) {
            throw new Error("Unable to load dashboard data.");
        }

        const data = await response.json();

        renderQualityTrendChart(
            data.reliability.history
        );

        renderCheckResultsChart(
            data.quality.passed_checks,
            data.quality.failed_checks
        );

        renderActiveIncidents(
            data.alerts.active
        );

    } catch (error) {

        console.error(
            "Dashboard data loading failed:",
            error
        );

    }

}


function renderQualityTrendChart(runs) {

    const canvas = document.getElementById(
        "qualityTrendChart"
    );

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (!Array.isArray(runs) || !runs.length) {
        return;
    }

    const validRuns = runs.filter(function(run) {

        return run.quality_score !== null;

    });

    if (!validRuns.length) {
        return;
    }

    if (qualityTrendChart) {
        qualityTrendChart.destroy();
    }

    qualityTrendChart = new Chart(canvas, {

        type: "line",

        data: {

            labels: validRuns.map(function(run) {

                return run.date;

            }),

            datasets: [
                {
                    label: "Quality Score",

                    data: validRuns.map(function(run) {

                        return run.quality_score;

                    }),

                    tension: 0.35,

                    fill: false,

                    borderWidth: 3,

                    pointRadius: 4,

                    pointHoverRadius: 6
                }
            ]
        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            interaction: {
                intersect: false,

                mode: "index"
            },

            scales: {

                x: {

                    grid: {
                        display: false
                    }

                },

                y: {

                    beginAtZero: true,

                    max: 100,

                    ticks: {

                        callback: function(value) {

                            return value + "%";

                        }

                    }

                }

            },

            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    callbacks: {

                        label: function(context) {

                            return (
                                "Quality: " +
                                context.parsed.y +
                                "%"
                            );

                        }

                    }

                }

            }

        }

    });

}


function renderCheckResultsChart(passed, failed) {

    const canvas = document.getElementById(
        "checkResultsChart"
    );

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (checkResultsChart) {
        checkResultsChart.destroy();
    }

    checkResultsChart = new Chart(canvas, {

        type: "doughnut",

        data: {

            labels: [
                "Passed",
                "Failed"
            ],

            datasets: [
                {
                    data: [
                        passed,
                        failed
                    ],

                    borderWidth: 0
                }
            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            cutout: "68%",

            plugins: {

                legend: {
                    position: "bottom"
                }

            }

        }

    });

}


function renderActiveIncidents(alerts) {

    const container = document.getElementById(
        "dashboardIncidents"
    );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!Array.isArray(alerts) || !alerts.length) {

        container.innerHTML = `
            <div class="incident-empty">

                <div class="incident-empty-icon">
                    ✓
                </div>

                <strong>
                    No active incidents
                </strong>

                <span>
                    Your data platform has no unresolved alerts.
                </span>

            </div>
        `;

        return;
    }

    alerts.forEach(function(alert) {

        const incident = document.createElement(
            "div"
        );

        incident.className = "dashboard-incident";

        const severity =
            String(alert.severity || "LOW")
                .toLowerCase();

        const pipelineName =
            alert.pipeline
                ? alert.pipeline.name
                : "Unknown pipeline";

        const runId =
            alert.pipeline_run
                ? "#" + alert.pipeline_run.id
                : "—";

        incident.innerHTML = `

            <div class="incident-severity ${severity}">
                ${escapeHtml(alert.severity)}
            </div>

            <div class="incident-content">

                <strong>
                    ${escapeHtml(alert.title)}
                </strong>

                <p>
                    ${escapeHtml(alert.message)}
                </p>

                <div class="incident-meta">

                    <span>
                        ${escapeHtml(pipelineName)}
                    </span>

                    <span>
                        Run ${runId}
                    </span>

                    <span>
                        ${formatIncidentDate(
                            alert.created_at
                        )}
                    </span>

                </div>

            </div>

            <a
                href="/alerts/"
                class="incident-link"
            >
                Investigate →
            </a>

        `;

        container.appendChild(incident);

    });

}


function escapeHtml(value) {

    const div = document.createElement(
        "div"
    );

    div.textContent = value ?? "";

    return div.innerHTML;

}


function formatIncidentDate(value) {

    if (!value) {
        return "—";
    }

    return new Date(value).toLocaleString();

}


document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadDashboardData();

        const refreshButton =
            document.getElementById(
                "refreshDashboard"
            );

        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                function() {

                    window.location.reload();

                }
            );

        }

    }
);
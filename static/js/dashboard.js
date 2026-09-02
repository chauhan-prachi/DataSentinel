let qualityTrendChart = null;
let checkResultsChart = null;

async function loadDashboard() {
    const loadingState = document.getElementById("loadingState");
    const dashboardContent = document.getElementById("dashboardContent");
    const errorState = document.getElementById("errorState");
    const refreshButton = document.getElementById("refreshButton");

    try {
        if (refreshButton) {
            refreshButton.disabled = true;
            refreshButton.classList.add("loading");
        }

        if (loadingState) {
            loadingState.classList.remove("hidden");
        }

        if (errorState) {
            errorState.classList.add("hidden");
        }

        const response = await fetch("/api/dashboard/", {
            method: "GET",
            headers: {
                "Accept": "application/json"
            },
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`Dashboard API returned ${response.status}`);
        }

        const data = await response.json();

        updateMetrics(data);
        updateLatestRun(data.latest_run);
        updateQualityOverview(data.quality);
        updateRecentRuns(data.recent_runs || []);
        updateAnalytics(data);

        if (dashboardContent) {
            dashboardContent.classList.remove("hidden");
        }

        if (loadingState) {
            loadingState.classList.add("hidden");
        }

    } catch (error) {
        console.error("Dashboard error:", error);

        if (loadingState) {
            loadingState.classList.add("hidden");
        }

        if (dashboardContent) {
            dashboardContent.classList.add("hidden");
        }

        if (errorState) {
            errorState.classList.remove("hidden");
        }

        const errorMessage = document.getElementById("errorMessage");

        if (errorMessage) {
            errorMessage.textContent =
                "Unable to connect to the DataSentinel API. Please check that the Django server is running.";
        }

    } finally {
        if (refreshButton) {
            refreshButton.disabled = false;
            refreshButton.classList.remove("loading");
        }
    }
}


function updateMetrics(data) {
    const overview = data.overview || {};

    setText("totalRuns", overview.total_runs ?? 0);
    setText("successfulRuns", overview.successful_runs ?? 0);
    setText("averageQuality", formatScore(overview.average_quality_score));
    setText("openIssues", data.quality?.open_issues ?? 0);

    const totalRuns = Number(overview.total_runs || 0);
    const successfulRuns = Number(overview.successful_runs || 0);

    const successRate =
        totalRuns > 0
            ? ((successfulRuns / totalRuns) * 100).toFixed(1)
            : "0.0";

    setText("successRate", `${successRate}%`);
}


function updateLatestRun(run) {
    if (!run) {
        return;
    }

    setText("latestPipeline", run.pipeline || "Unknown");
    setText("latestDataset", run.dataset || "Unknown");
    setText("latestRows", run.rows_processed ?? 0);
    setText("latestQuality", `${formatScore(run.quality_score)}%`);
    setText("latestStarted", formatDate(run.started_at));

    const statusElement = document.getElementById("latestStatus");

    if (statusElement) {
        statusElement.textContent = run.status || "UNKNOWN";

        statusElement.className = "status-badge";

        const status = String(run.status || "").toUpperCase();

        if (status === "SUCCESS") {
            statusElement.classList.add("success");
        } else if (status === "FAILED") {
            statusElement.classList.add("failed");
        } else {
            statusElement.classList.add("running");
        }
    }
}


function updateQualityOverview(quality) {
    if (!quality) {
        return;
    }

    setText("qualityPercentage", calculateQualityPercentage(quality));
    setText("passedChecks", quality.passed_checks ?? 0);
    setText("failedChecks", quality.failed_checks ?? 0);
    setText("qualityIssues", quality.open_issues ?? 0);
}


function calculateQualityPercentage(quality) {
    const passed = Number(quality.passed_checks || 0);
    const failed = Number(quality.failed_checks || 0);
    const total = passed + failed;

    if (total === 0) {
        return "0.0%";
    }

    return `${((passed / total) * 100).toFixed(1)}%`;
}


function updateRecentRuns(runs) {
    const table = document.getElementById("recentRunsTable");

    if (!table) {
        return;
    }

    if (!runs || runs.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    No pipeline runs found.
                </td>
            </tr>
        `;
        return;
    }

    table.innerHTML = runs.slice(0, 10).map(run => {

        const status = String(run.status || "").toUpperCase();

        let statusClass = "running";

        if (status === "SUCCESS") {
            statusClass = "success";
        } else if (status === "FAILED") {
            statusClass = "failed";
        }

        const score = Number(run.quality_score || 0);

        let scoreClass = "poor";

        if (score >= 80) {
            scoreClass = "good";
        } else if (score >= 50) {
            scoreClass = "warning";
        }

        return `
            <tr>
                <td>
                    <strong>#${run.id}</strong>
                </td>

                <td>
                    <strong>${escapeHtml(run.pipeline)}</strong>
                </td>

                <td>
                    ${escapeHtml(run.dataset)}
                </td>

                <td>
                    <span class="status ${statusClass}">
                        ${escapeHtml(status)}
                    </span>
                </td>

                <td>
                    ${Number(run.rows_processed || 0).toLocaleString()}
                </td>

                <td>
                    <strong class="score ${scoreClass}">
                        ${formatScore(score)}%
                    </strong>
                </td>

                <td>
                    ${formatDate(run.started_at)}
                </td>
            </tr>
        `;

    }).join("");
}


function updateAnalytics(data) {
    const overview = data.overview || {};
    const quality = data.quality || {};
    const runs = data.recent_runs || [];

    const totalRuns = Number(overview.total_runs || 0);
    const successfulRuns = Number(overview.successful_runs || 0);
    const failedRuns = Number(overview.failed_runs || 0);

    const passedChecks = Number(quality.passed_checks || 0);
    const failedChecks = Number(quality.failed_checks || 0);
    const openIssues = Number(quality.open_issues || 0);

    setText("analyticsPassedChecks", passedChecks);
    setText("analyticsFailedChecks", failedChecks);

    setText("healthSuccessful", successfulRuns);
    setText("healthFailed", failedRuns);
    setText("healthTotal", totalRuns);

    setText("analyticsIssueCount", openIssues);
    setText("analyticsOpenIssues", openIssues);

    const successPercentage =
        totalRuns > 0
            ? (successfulRuns / totalRuns) * 100
            : 0;

    const failedPercentage =
        totalRuns > 0
            ? (failedRuns / totalRuns) * 100
            : 0;

    setWidth("successHealthBar", successPercentage);
    setWidth("failedHealthBar", failedPercentage);

    updateIssueSeverity(quality);

    renderQualityTrendChart(runs);
    renderCheckResultsChart(passedChecks, failedChecks);
}


function updateIssueSeverity(quality) {
    const severity = quality.issue_severity || {};

    setText("criticalIssues", severity.CRITICAL ?? 0);
    setText("highIssues", severity.HIGH ?? 0);
    setText("mediumIssues", severity.MEDIUM ?? 0);
    setText("lowIssues", severity.LOW ?? 0);
}


function renderQualityTrendChart(runs) {
    const canvas = document.getElementById("qualityTrendChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const orderedRuns = [...runs].reverse();

    const labels = orderedRuns.map(run => `#${run.id}`);

    const scores = orderedRuns.map(run =>
        Number(run.quality_score || 0)
    );

    if (qualityTrendChart) {
        qualityTrendChart.destroy();
    }

    qualityTrendChart = new Chart(canvas, {
        type: "line",

        data: {
            labels: labels,

            datasets: [
                {
                    label: "Quality Score",
                    data: scores,
                    borderWidth: 3,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 7
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

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: context =>
                            ` Quality Score: ${context.parsed.y}%`
                    }
                }
            },

            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,

                    ticks: {
                        callback: value => `${value}%`
                    }
                },

                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}


function renderCheckResultsChart(passed, failed) {
    const canvas = document.getElementById("checkResultsChart");

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

            cutout: "72%",

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: context => {
                            const value = context.parsed;
                            return ` ${context.label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}


function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


function setWidth(id, percentage) {
    const element = document.getElementById(id);

    if (element) {
        element.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
    }
}


function formatScore(value) {
    const number = Number(value);

    if (Number.isNaN(number)) {
        return "0.00";
    }

    return number.toFixed(2);
}


function formatDate(dateString) {
    if (!dateString) {
        return "Unknown";
    }

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }

    return date.toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}


function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();

    setInterval(loadDashboard, 30000);
});


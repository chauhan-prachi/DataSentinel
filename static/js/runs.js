document.addEventListener("DOMContentLoaded", function () {

    loadRuns();

    const refreshButton = document.getElementById("refreshRuns");
    const retryButton = document.getElementById("retryRuns");

    if (refreshButton) {
        refreshButton.addEventListener("click", loadRuns);
    }

    if (retryButton) {
        retryButton.addEventListener("click", loadRuns);
    }
});


async function loadRuns() {

    const loading = document.getElementById("runsLoading");
    const panel = document.getElementById("runsPanel");
    const error = document.getElementById("runsError");

    showElement(loading);
    hideElement(panel);
    hideElement(error);

    try {

        const response = await fetch("/api/runs/", {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(
                "Request failed: " + response.status
            );
        }

        const data = await response.json();

        const runs = Array.isArray(data.runs)
            ? data.runs
            : [];

        updateSummary(runs);
        renderRuns(runs);

        hideElement(loading);
        showElement(panel);

    } catch (errorObject) {

        console.error(
            "Runs loading error:",
            errorObject
        );

        hideElement(loading);
        hideElement(panel);
        showElement(error);
    }
}


function updateSummary(runs) {

    const totalElement =
        document.getElementById("totalRuns");

    const successfulElement =
        document.getElementById("successfulRuns");

    const failedElement =
        document.getElementById("failedRuns");

    const averageElement =
        document.getElementById("averageQuality");


    const total = runs.length;

    const successful = runs.filter(function (run) {
        return run.status === "SUCCESS";
    }).length;

    const failed = runs.filter(function (run) {
        return run.status === "FAILED";
    }).length;


    const scores = runs
        .map(function (run) {
            return Number(run.quality_score);
        })
        .filter(function (score) {
            return Number.isFinite(score);
        });


    let average = null;

    if (scores.length > 0) {

        const totalScore = scores.reduce(
            function (sum, score) {
                return sum + score;
            },
            0
        );

        average = totalScore / scores.length;
    }


    if (totalElement) {
        totalElement.textContent = total;
    }

    if (successfulElement) {
        successfulElement.textContent = successful;
    }

    if (failedElement) {
        failedElement.textContent = failed;
    }

    if (averageElement) {

        averageElement.textContent =
            average !== null
                ? average.toFixed(1) + "%"
                : "—";
    }
}


function renderRuns(runs) {

    const tbody =
        document.getElementById("runsTable");

    if (!tbody) {
        return;
    }

    tbody.innerHTML = "";


    if (runs.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="8"
                    class="run-empty"
                >
                    No pipeline runs found.
                </td>
            </tr>
        `;

        return;
    }


    runs.forEach(function (run) {

        const row =
            document.createElement("tr");

        row.setAttribute(
            "data-run-id",
            run.id
        );


        const qualityScore =
            run.quality_score !== null &&
            run.quality_score !== undefined
                ? Number(run.quality_score)
                : null;


        const qualityHtml =
            qualityScore !== null &&
            Number.isFinite(qualityScore)
                ? `
                    <span class="run-quality ${getQualityClass(qualityScore)}">
                        ${qualityScore.toFixed(2)}%
                    </span>
                `
                : `
                    <span class="quality-na">
                        —
                    </span>
                `;


        row.innerHTML = `

            <td>
                <button
                    class="run-id-button"
                    type="button"
                    aria-label="View run #${run.id}"
                >
                    #${run.id}
                </button>
            </td>

            <td>
                <div class="run-name">
                    ${escapeHtml(run.pipeline)}
                </div>
            </td>

            <td>
                <div class="dataset-name">
                    ${escapeHtml(run.dataset)}
                </div>
            </td>

            <td>
                <span class="run-status ${getStatusClass(run.status)}">
                    ${escapeHtml(run.status)}
                </span>
            </td>

            <td>
                ${Number(run.rows_processed || 0).toLocaleString("en-IN")}
            </td>

            <td>
                ${qualityHtml}
            </td>

            <td>
                ${formatDate(run.started_at)}
            </td>

            <td>
                ${formatDate(run.completed_at)}
            </td>

        `;


        row.addEventListener(
            "click",
            function (event) {

                if (
                    event.target.closest(
                        ".run-id-button"
                    )
                ) {
                    window.location.href =
                        "/runs/" + run.id + "/";
                    return;
                }

                window.location.href =
                    "/runs/" + run.id + "/";
            }
        );


        tbody.appendChild(row);
    });
}


function getStatusClass(status) {

    switch (status) {

        case "SUCCESS":
            return "success";

        case "FAILED":
            return "failed";

        case "RUNNING":
            return "pending";

        default:
            return "pending";
    }
}


function getQualityClass(score) {

    if (score >= 80) {
        return "quality-good";
    }

    if (score >= 60) {
        return "quality-medium";
    }

    return "quality-low";
}


function formatDate(dateString) {

    if (!dateString) {
        return "—";
    }

    const date =
        new Date(dateString);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return escapeHtml(dateString);
    }

    return date.toLocaleString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "numeric",
            minute: "2-digit"
        }
    );
}


function showElement(element) {

    if (element) {
        element.classList.remove("hidden");
    }
}


function hideElement(element) {

    if (element) {
        element.classList.add("hidden");
    }
}


function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
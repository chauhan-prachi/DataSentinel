document.addEventListener("DOMContentLoaded", () => {
    loadRuns();

    const refreshButton = document.getElementById("refreshRuns");

    if (refreshButton) {
        refreshButton.addEventListener("click", loadRuns);
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
        const response = await fetch("/api/runs/");

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();

        renderRuns(data.runs || []);

        hideElement(loading);
        showElement(panel);

    } catch (err) {
        console.error("Runs loading error:", err);

        hideElement(loading);
        showElement(error);
    }
}


function renderRuns(runs) {
    const tbody = document.getElementById("runsTable");

    if (!tbody) {
        return;
    }

    tbody.innerHTML = "";

    if (runs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="run-empty">
                    No pipeline runs found.
                </td>
            </tr>
        `;

        return;
    }

    runs.forEach((run) => {
        const row = document.createElement("tr");

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
                ${run.rows_processed ?? 0}
            </td>

            <td>
                ${
                    run.quality_score !== null &&
                    run.quality_score !== undefined
                        ? `
                            <span class="run-quality ${getQualityClass(
                                Number(run.quality_score)
                            )}">
                                ${Number(run.quality_score).toFixed(2)}%
                            </span>
                        `
                        : `
                            <span class="quality-na">—</span>
                        `
                }
            </td>

            <td>
                ${formatDate(run.started_at)}
            </td>

            <td>
                ${formatDate(run.completed_at)}
            </td>
        `;

        row.addEventListener("click", () => {
            window.location.href = `/runs/${run.id}/`;
        });

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

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return escapeHtml(dateString);
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
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
document.addEventListener("DOMContentLoaded", () => {
    const page = document.getElementById("pipelinePage");

    if (!page) {
        console.error("pipelinePage element not found.");
        return;
    }

    const pipelineId = page.dataset.pipelineId;

    if (!pipelineId) {
        console.error("Pipeline ID is missing.");
        return;
    }

    loadPipeline(pipelineId);

    const refreshButton = document.getElementById("refreshPipeline");

    if (refreshButton) {
        refreshButton.addEventListener("click", () => {
            loadPipeline(pipelineId);
        });
    }

    const retryButton = document.getElementById("retryPipeline");

    if (retryButton) {
        retryButton.addEventListener("click", () => {
            loadPipeline(pipelineId);
        });
    }

    const runButton = document.getElementById("runPipelineButton");

    if (runButton) {
        runButton.addEventListener("click", () => {
            runPipeline(pipelineId);
        });
    }
});


async function loadPipeline(pipelineId) {
    const loading = document.getElementById("pipelineLoading");
    const content = document.getElementById("pipelineContent");
    const error = document.getElementById("pipelineError");

    showElement(loading);
    hideElement(content);
    hideElement(error);

    try {
        const response = await fetch(`/api/pipelines/${encodeURIComponent(pipelineId)}/`);
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const pipeline = await response.json();

        renderPipeline(pipeline);

        hideElement(loading);
        showElement(content);

    } catch (err) {
        console.error("Pipeline loading error:", err);

        hideElement(loading);
        showElement(error);

        const message = document.getElementById("pipelineErrorMessage");

        if (message) {
            message.textContent =
                err.message || "Unable to load pipeline.";
        }
    }
}


function renderPipeline(pipeline) {
    const name = document.getElementById("pipelineName");

    if (name) {
        name.textContent = pipeline.name || "--";
    }

    const description = document.getElementById("pipelineDescription");

    if (description) {
        description.textContent =
            pipeline.description ||
            "Data quality monitoring pipeline";
    }

    const dataset = document.getElementById("pipelineDataset");

    if (dataset) {
        dataset.textContent =
            pipeline.dataset?.name ||
            pipeline.dataset_name ||
            "--";
    }

    const runs = document.getElementById("pipelineRuns");

    if (runs) {
        runs.textContent = pipeline.run_count ?? 0;
    }

    const qualityScore = document.getElementById("pipelineQualityScore");

    if (qualityScore) {
        if (
            pipeline.quality_score !== null &&
            pipeline.quality_score !== undefined
        ) {
            qualityScore.textContent =
                `${Number(pipeline.quality_score).toFixed(2)}%`;
        } else {
            qualityScore.textContent = "--";
        }
    }

    const lastRun = document.getElementById("pipelineLastRun");

    if (lastRun) {
        lastRun.textContent = getLastRunDate(pipeline);
    }

    renderQualityChecks(
        pipeline.quality_checks || []
    );

    renderRuns(
        pipeline.runs || []
    );

    const status = document.getElementById("pipelineStatus");

    if (status) {
        const pipelineStatus =
            pipeline.status || "ACTIVE";

        status.textContent = pipelineStatus;

        status.className =
            `status-badge ${getStatusClass(pipelineStatus)}`;
    }
}


function renderQualityChecks(checks) {
    const container =
        document.getElementById("qualityChecksContainer");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!checks.length) {
        container.innerHTML = `
            <div class="empty-state">
                No quality checks configured.
            </div>
        `;

        return;
    }

    checks.forEach((check) => {
        const item =
            document.createElement("div");

        item.className = "check-item";

        const checkType =
            escapeHtml(check.check_type || "Quality Check");

        const columnName =
            check.column_name
                ? escapeHtml(check.column_name)
                : "Dataset-level check";

        const checkStatus =
            check.is_active
                ? "ACTIVE"
                : "INACTIVE";

        item.innerHTML = `
            <div class="check-info">

                <div class="check-icon">
                    ✓
                </div>

                <div>

                    <div class="check-type">
                        ${checkType}
                    </div>

                    <div class="check-column">
                        ${columnName}
                    </div>

                </div>

            </div>

            <div class="check-status">
                ${checkStatus}
            </div>
        `;

        container.appendChild(item);
    });
}


function renderRuns(runs) {
    const container =
        document.getElementById("pipelineRunsContainer");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!runs.length) {
        container.innerHTML = `
            <div class="empty-state">
                No pipeline runs found.
            </div>
        `;

        return;
    }

    const table =
        document.createElement("table");

    table.className = "runs-table";

    table.innerHTML = `
        <thead>
            <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Rows Processed</th>
                <th>Quality Score</th>
                <th>Started</th>
                <th>Completed</th>
            </tr>
        </thead>

        <tbody></tbody>
    `;

    const tbody =
        table.querySelector("tbody");

    runs.forEach((run) => {
        const row =
            document.createElement("tr");

        const status =
            run.status || "PENDING";

        const qualityScore =
            run.quality_score !== null &&
            run.quality_score !== undefined
                ? `${Number(run.quality_score).toFixed(2)}%`
                : "--";

        row.innerHTML = `
            <td>
                <strong>#${escapeHtml(run.id)}</strong>
            </td>

            <td>
                <span class="status-badge ${getStatusClass(status)}">
                    ${escapeHtml(status)}
                </span>
            </td>

            <td>
                ${run.rows_processed ?? 0}
            </td>

            <td>
                ${qualityScore}
            </td>

            <td>
                ${formatDate(run.started_at)}
            </td>

            <td>
                ${formatDate(run.completed_at)}
            </td>
        `;

        tbody.appendChild(row);
    });

    container.appendChild(table);
}


async function runPipeline(pipelineId) {
    const confirmed = confirm(
        "Are you sure you want to run this pipeline?"
    );

    if (!confirmed) {
        return;
    }

    const runButton =
        document.getElementById("runPipelineButton");

    if (runButton) {
        runButton.disabled = true;
        runButton.textContent = "Running...";
    }

    try {
        const response = await fetch(
            `/pipelines/${pipelineId}/run/`,
            {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "Content-Type": "application/json"
                }
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch (jsonError) {
            console.warn("Response was not JSON.");
        }

        if (!response.ok) {
            throw new Error(
                data.error ||
                data.message ||
                "Pipeline execution failed."
            );
        }

        alert(
            data.message ||
            "Pipeline executed successfully."
        );

        await loadPipeline(pipelineId);

    } catch (error) {
        console.error(
            "Pipeline execution error:",
            error
        );

        alert(
            error.message ||
            "Unable to execute pipeline."
        );

    } finally {
        if (runButton) {
            runButton.disabled = false;
            runButton.textContent = "Run Pipeline";
        }
    }
}


function getLastRunDate(pipeline) {
    if (
        pipeline.runs &&
        pipeline.runs.length > 0
    ) {
        return formatDate(
            pipeline.runs[0].started_at
        );
    }

    return "--";
}


function getStatusClass(status) {
    const normalizedStatus =
        String(status || "")
            .toUpperCase();

    if (
        normalizedStatus === "SUCCESS" ||
        normalizedStatus === "ACTIVE"
    ) {
        return "success";
    }

    if (
        normalizedStatus === "FAILED" ||
        normalizedStatus === "INACTIVE"
    ) {
        return "failed";
    }

    return "pending";
}


function formatDate(dateString) {
    if (!dateString) {
        return "--";
    }

    const date =
        new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return dateString;
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


function getCsrfToken() {
    const name = "csrftoken=";

    const cookies =
        document.cookie.split(";");

    for (let cookie of cookies) {
        cookie = cookie.trim();

        if (cookie.startsWith(name)) {
            return decodeURIComponent(
                cookie.substring(name.length)
            );
        }
    }

    return "";
}
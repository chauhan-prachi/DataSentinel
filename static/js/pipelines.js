document.addEventListener("DOMContentLoaded", () => {
    loadPipelines();

    const refreshButton = document.getElementById("refreshPipelines");

    if (refreshButton) {
        refreshButton.addEventListener("click", loadPipelines);
    }
});


async function loadPipelines() {
    const loading = document.getElementById("pipelinesLoading");
    const container = document.getElementById("pipelinesContainer");
    const error = document.getElementById("pipelinesError");

    showElement(loading);
    hideElement(container);
    hideElement(error);

    try {
        const response = await fetch("/api/pipelines/");

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();

        renderPipelines(data.pipelines || []);

        hideElement(loading);
        showElement(container);

    } catch (error) {
        console.error("Pipelines loading error:", error);

        hideElement(loading);
        showElement(error);
    }
}


function renderPipelines(pipelines) {
    const container = document.getElementById("pipelinesContainer");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (pipelines.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                No pipelines found.
            </div>
        `;

        return;
    }

    pipelines.forEach(pipeline => {
        const card = document.createElement("div");

        card.className = "pipeline-card";

        card.innerHTML = `
            <div class="pipeline-card-header">

                <div>
                    <span class="pipeline-icon">
                        ◈
                    </span>

                    <div>
                        <h3>
                            ${escapeHtml(pipeline.name)}
                        </h3>

                        <p>
                            ${escapeHtml(
                                pipeline.description ||
                                "Data quality monitoring pipeline"
                            )}
                        </p>
                    </div>
                </div>

                <span class="status-badge ${getStatusClass(pipeline.status)}">
                    ${escapeHtml(pipeline.status || "ACTIVE")}
                </span>

            </div>


            <div class="pipeline-meta">

                <div class="pipeline-meta-item">
                    <span>Dataset</span>

                    <strong>
                        ${escapeHtml(
                            pipeline.dataset?.name ||
                            pipeline.dataset_name ||
                            "--"
                        )}
                    </strong>
                </div>


                <div class="pipeline-meta-item">
                    <span>Runs</span>

                    <strong>
                        ${pipeline.run_count ?? 0}
                    </strong>
                </div>


                <div class="pipeline-meta-item">
                    <span>Last Run</span>

                    <strong>
                        ${formatDate(
                            pipeline.last_run_at
                        )}
                    </strong>
                </div>


                <div class="pipeline-meta-item">
                    <span>Quality Score</span>

                    <strong>
                        ${
                            pipeline.quality_score !== null &&
                            pipeline.quality_score !== undefined
                                ? `${Number(
                                    pipeline.quality_score
                                ).toFixed(2)}%`
                                : "--"
                        }
                    </strong>
                </div>

            </div>


            <div class="pipeline-card-footer">

                <button
                    class="secondary-btn"
                    onclick="viewPipeline(${pipeline.id})"
                >
                    View Details
                </button>


                <button
                    class="primary-btn"
                    onclick="runPipeline(${pipeline.id})"
                >
                    Run Pipeline
                </button>

            </div>
        `;

        container.appendChild(card);
    });
}


async function viewPipeline(pipelineId) {
    window.location.href = `/pipelines/${pipelineId}/`;
}


async function runPipeline(pipelineId) {
    const confirmed = confirm(
        "Are you sure you want to run this pipeline?"
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            `/api/pipelines/${pipelineId}/run/`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                }
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Pipeline execution failed."
            );
        }

        alert("Pipeline executed successfully.");

        await loadPipelines();

    } catch (error) {
        console.error("Pipeline execution error:", error);

        alert(
            error.message ||
            "Unable to execute pipeline."
        );
    }
}


function getStatusClass(status) {
    const normalizedStatus = String(
        status || ""
    ).toUpperCase();

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

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return dateString;
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
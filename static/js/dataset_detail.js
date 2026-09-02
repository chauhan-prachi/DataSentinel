document.addEventListener("DOMContentLoaded", () => {
    const datasetId = window.DATASET_ID;

    if (!datasetId) {
        return;
    }

    loadDataset(datasetId);

    const refreshButton = document.getElementById("refreshDataset");

    if (refreshButton) {
        refreshButton.addEventListener("click", () => loadDataset(datasetId));
    }

    const retryButton = document.getElementById("retryDataset");

    if (retryButton) {
        retryButton.addEventListener("click", () => loadDataset(datasetId));
    }
});

async function loadDataset(datasetId) {
    const loading = document.getElementById("datasetLoading");
    const content = document.getElementById("datasetContent");
    const error = document.getElementById("datasetError");

    showElement(loading);
    hideElement(content);
    hideElement(error);

    try {
        const response = await fetch(`/api/datasets/${encodeURIComponent(datasetId)}/`);

        let data = {};

        try {
            data = await response.json();
        } catch (jsonError) {
            data = {};
        }

        if (!response.ok) {
            throw new Error(
                data.error || `Request failed: ${response.status}`
            );
        }

        renderDataset(data);

        hideElement(loading);
        showElement(content);
    } catch (err) {
        console.error("Dataset loading error:", err);

        hideElement(loading);
        showElement(error);

        const message = document.getElementById("datasetErrorMessage");

        if (message) {
            message.textContent =
                err.message || "Unable to load dataset.";
        }
    }
}

function renderDataset(dataset) {
    const name = document.getElementById("datasetName");
    const description = document.getElementById("datasetDescription");
    const rows = document.getElementById("datasetRows");
    const columns = document.getElementById("datasetColumns");
    const checks = document.getElementById("datasetChecks");
    const pipelines = document.getElementById("datasetPipelines");

    if (name) {
        name.textContent = dataset.name || "Dataset";
    }

    if (description) {
        description.textContent =
            dataset.description || "No description provided.";
    }

    if (rows) {
        rows.textContent = formatNumber(dataset.row_count);
    }

    if (columns) {
        columns.textContent = formatNumber(dataset.column_count);
    }

    if (checks) {
        checks.textContent = formatNumber(dataset.quality_check_count);
    }

    if (pipelines) {
        pipelines.textContent = formatNumber(dataset.pipeline_count);
    }

    renderDataSource(dataset.data_source);
    renderSchema(dataset.schema_snapshot);
    renderQualityChecks(dataset.quality_checks || []);
    renderPipelines(dataset.pipelines || []);
}

function renderDataSource(source) {
    const container = document.getElementById("dataSourceContainer");

    if (!container) {
        return;
    }

    if (!source) {
        container.innerHTML = `
            <div class="empty-state">
                No data source configured.
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="source-details">
            <strong>
                ${escapeHtml(source.name || "Unnamed source")}
            </strong>

            <span>
                Type:
                ${escapeHtml(source.type || "--")}
            </span>

            <span>
                Status:
                ${source.is_active ? "ACTIVE" : "INACTIVE"}
            </span>
        </div>
    `;
}

function renderSchema(schemaSnapshot) {
    const container = document.getElementById("schemaContainer");

    if (!container) {
        return;
    }

    const columns = schemaSnapshot?.columns || [];

    if (!columns.length) {
        container.innerHTML = `
            <div class="empty-state">
                No schema information available.
            </div>
        `;
        return;
    }

    const table = document.createElement("table");
    table.className = "data-table";

    table.innerHTML = `
        <thead>
            <tr>
                <th>Column</th>
                <th>Data Type</th>
                <th>Nulls</th>
                <th>Null %</th>
                <th>Unique Values</th>
            </tr>
        </thead>
        <tbody></tbody>
    `;

    const tbody = table.querySelector("tbody");

    columns.forEach(column => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>
                <strong>
                    ${escapeHtml(column.name || "--")}
                </strong>
            </td>

            <td>
                ${escapeHtml(column.dtype || "--")}
            </td>

            <td>
                ${formatNumber(column.null_count)}
            </td>

            <td>
                ${column.null_percentage ?? 0}%
            </td>

            <td>
                ${formatNumber(column.unique_count)}
            </td>
        `;

        tbody.appendChild(row);
    });

    container.innerHTML = "";
    container.appendChild(table);
}

function renderQualityChecks(checks) {
    const container = document.getElementById("qualityChecksContainer");

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

    checks.forEach(check => {
        const item = document.createElement("div");
        item.className = "quality-check-item";

        item.innerHTML = `
            <div>
                <strong>
                    ${escapeHtml(check.name || "Unnamed check")}
                </strong>

                <div>
                    ${escapeHtml(check.check_type || "--")}
                </div>

                <small>
                    ${
                        check.column_name
                            ? escapeHtml(check.column_name)
                            : "Dataset-level check"
                    }
                </small>
            </div>

            <span class="status-badge success">
                ACTIVE
            </span>
        `;

        container.appendChild(item);
    });
}

function renderPipelines(pipelines) {
    const container = document.getElementById("pipelinesContainer");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!pipelines.length) {
        container.innerHTML = `
            <div class="empty-state">
                No pipelines are using this dataset yet.
            </div>
        `;
        return;
    }

    pipelines.forEach(pipeline => {
        const item = document.createElement("div");
        item.className = "pipeline-item";

        const pipelineStatus = pipeline.status || "PENDING";

        item.innerHTML = `
            <div>
                <strong>
                    ${escapeHtml(pipeline.name || "Unnamed pipeline")}
                </strong>

                <p>
                    ${escapeHtml(
                        pipeline.description || "No description."
                    )}
                </p>
            </div>

            <div>
                <span class="status-badge ${getStatusClass(pipelineStatus)}">
                    ${escapeHtml(pipelineStatus)}
                </span>

                <button
                    class="secondary-btn"
                    type="button"
                    data-pipeline-id="${encodeURIComponent(pipeline.id)}"
                >
                    View
                </button>
            </div>
        `;

        const viewButton = item.querySelector("[data-pipeline-id]");

        if (viewButton) {
            viewButton.addEventListener("click", () => {
                window.location.href =
                    `/pipelines/${encodeURIComponent(pipeline.id)}/`;
            });
        }

        container.appendChild(item);
    });
}

function getStatusClass(status) {
    const normalized = String(status || "").toUpperCase();

    if (
        normalized === "ACTIVE" ||
        normalized === "SUCCESS" ||
        normalized === "COMPLETED"
    ) {
        return "success";
    }

    if (
        normalized === "FAILED" ||
        normalized === "INACTIVE" ||
        normalized === "ERROR"
    ) {
        return "failed";
    }

    return "pending";
}

function formatNumber(value) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "0";
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
        return "0";
    }

    return number.toLocaleString("en-IN");
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
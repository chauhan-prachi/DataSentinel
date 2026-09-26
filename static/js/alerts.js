document.addEventListener("DOMContentLoaded", () => {

    const container = document.getElementById("alertsContainer");
    const loading = document.getElementById("alertsLoading");
    const empty = document.getElementById("alertsEmpty");
    const error = document.getElementById("alertsError");

    const search = document.getElementById("alertSearch");
    const severityFilter = document.getElementById("alertSeverityFilter");
    const statusFilter = document.getElementById("alertStatusFilter");
    const typeFilter = document.getElementById("alertTypeFilter");

    const modal = document.getElementById("alertDetailModal");
    const closeModal = document.getElementById("closeAlertDetail");
    const overlay = document.getElementById("alertDetailOverlay");

    const acknowledgeButton = document.getElementById(
        "acknowledgeAlertButton"
    );

    const resolveButton = document.getElementById(
        "resolveAlertButton"
    );

    const toast = document.getElementById("alertToast");
    const toastMessage = document.getElementById("alertToastMessage");

    let alerts = [];
    let selectedAlert = null;


    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value ?? "";
        return div.innerHTML;
    }


    function formatDate(value) {
        if (!value) {
            return "—";
        }

        return new Date(value).toLocaleString();
    }


    function typeLabel(type) {
        return type
            .replaceAll("_", " ")
            .toLowerCase()
            .replace(/\b\w/g, char => char.toUpperCase());
    }


    function showToast(message) {
        toastMessage.textContent = message;
        toast.classList.remove("hidden");

        setTimeout(() => {
            toast.classList.add("hidden");
        }, 2500);
    }


    function updateSummary(items) {
        document.getElementById("totalAlerts").textContent =
            items.length;

        document.getElementById("openAlerts").textContent =
            items.filter(
                alert => alert.status === "OPEN"
            ).length;

        document.getElementById("acknowledgedAlerts").textContent =
            items.filter(
                alert => alert.status === "ACKNOWLEDGED"
            ).length;

        document.getElementById("criticalAlerts").textContent =
            items.filter(
                alert => alert.severity === "CRITICAL"
            ).length;
    }


    function filteredAlerts() {
        const query = search.value.trim().toLowerCase();

        return alerts.filter(alert => {

            const matchesSearch =
                !query ||
                alert.title.toLowerCase().includes(query) ||
                alert.message.toLowerCase().includes(query) ||
                alert.pipeline.name.toLowerCase().includes(query);

            const matchesSeverity =
                !severityFilter.value ||
                alert.severity === severityFilter.value;

            const matchesStatus =
                !statusFilter.value ||
                alert.status === statusFilter.value;

            const matchesType =
                !typeFilter.value ||
                alert.alert_type === typeFilter.value;

            return (
                matchesSearch &&
                matchesSeverity &&
                matchesStatus &&
                matchesType
            );
        });
    }


    function renderAlerts() {
        const items = filteredAlerts();

        container.innerHTML = "";

        if (!items.length) {
            container.classList.add("hidden");
            empty.classList.remove("hidden");
            return;
        }

        empty.classList.add("hidden");
        container.classList.remove("hidden");

        items.forEach(alert => {

            const card = document.createElement("article");

            card.className = "alert-card";

            card.innerHTML = `
                <div class="alert-card-header">
                    <div>
                        <span class="alert-severity-badge ${alert.severity.toLowerCase()}">
                            ${escapeHtml(alert.severity)}
                        </span>

                        <span class="alert-status-badge ${alert.status.toLowerCase()}">
                            ${escapeHtml(alert.status)}
                        </span>
                    </div>

                    <span class="detail-label">
                        ${escapeHtml(typeLabel(alert.alert_type))}
                    </span>
                </div>

                <h3 class="alert-card-title">
                    ${escapeHtml(alert.title)}
                </h3>

                <p class="alert-card-message">
                    ${escapeHtml(alert.message)}
                </p>

                <div class="alert-card-footer">

                    <div class="alert-card-meta">

                        <span>
                            Pipeline: ${escapeHtml(alert.pipeline.name)}
                        </span>

                        <span>
                            Run: ${
                                alert.pipeline_run
                                    ? `#${alert.pipeline_run.id}`
                                    : "—"
                            }
                        </span>

                        <span>
                            ${formatDate(alert.created_at)}
                        </span>

                    </div>

                    <div class="alert-card-actions">

                        ${
                            alert.status === "OPEN"
                                ? `
                                    <button
                                        type="button"
                                        class="acknowledge"
                                        data-action="acknowledge"
                                        data-id="${alert.id}"
                                    >
                                        Acknowledge
                                    </button>
                                `
                                : ""
                        }

                        ${
                            alert.status !== "RESOLVED"
                                ? `
                                    <button
                                        type="button"
                                        class="resolve"
                                        data-action="resolve"
                                        data-id="${alert.id}"
                                    >
                                        Resolve
                                    </button>
                                `
                                : ""
                        }

                    </div>

                </div>
            `;

            card.addEventListener("click", event => {

                if (event.target.closest("button")) {
                    return;
                }

                openDetails(alert);
            });

            container.appendChild(card);
        });
    }


    function openDetails(alert) {

        selectedAlert = alert;

        document.getElementById("detailAlertType").textContent =
            typeLabel(alert.alert_type);

        document.getElementById("alertDetailTitle").textContent =
            alert.title;


        const severityElement =
            document.getElementById("detailAlertSeverity");

        severityElement.textContent = alert.severity;

        severityElement.className =
            `alert-severity-badge ${alert.severity.toLowerCase()}`;


        const statusElement =
            document.getElementById("detailAlertStatus");

        statusElement.textContent = alert.status;

        statusElement.className =
            `alert-status-badge ${alert.status.toLowerCase()}`;


        document.getElementById("detailAlertMessage").textContent =
            alert.message;

        document.getElementById("detailAlertPipeline").textContent =
            alert.pipeline.name;

        document.getElementById("detailAlertRun").textContent =
            alert.pipeline_run
                ? `#${alert.pipeline_run.id}`
                : "—";

        document.getElementById("detailAlertRunStatus").textContent =
            alert.pipeline_run
                ? alert.pipeline_run.status
                : "—";

        document.getElementById("detailAlertTypeValue").textContent =
            typeLabel(alert.alert_type);

        document.getElementById("detailAlertCreated").textContent =
            formatDate(alert.created_at);

        document.getElementById("detailAlertAcknowledged").textContent =
            formatDate(alert.acknowledged_at);

        document.getElementById("detailAlertResolved").textContent =
            formatDate(alert.resolved_at);

        document.getElementById("detailAlertMetadata").textContent =
            JSON.stringify(alert.metadata || {}, null, 2);


        acknowledgeButton.classList.toggle(
            "hidden",
            alert.status !== "OPEN"
        );

        resolveButton.classList.toggle(
            "hidden",
            alert.status === "RESOLVED"
        );

        modal.classList.remove("hidden");
    }


    function closeDetails() {
        modal.classList.add("hidden");
        selectedAlert = null;
    }


    async function updateAlert(id, status) {

        try {

            const csrfToken = document.querySelector(
                "[name=csrfmiddlewaretoken]"
            ).value;


            const response = await fetch(
                `/api/alerts/${id}/`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },

                    body: JSON.stringify({
                        status: status
                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {
                throw new Error(
                    data.error || "Unable to update alert."
                );
            }


            closeDetails();


            showToast(
                status === "RESOLVED"
                    ? "Alert resolved."
                    : "Alert acknowledged."
            );


            await loadAlerts();

        } catch (err) {

            showToast(err.message);
        }
    }


    async function changeStatus(id, status) {
        await updateAlert(id, status);
    }


    async function loadAlerts() {

        loading.classList.remove("hidden");

        error.classList.add("hidden");
        empty.classList.add("hidden");
        container.classList.add("hidden");


        try {

            const response = await fetch("/api/alerts/");


            if (!response.ok) {
                throw new Error("Unable to load alerts.");
            }


            const data = await response.json();

            alerts = data.alerts || [];


            updateSummary(alerts);

            renderAlerts();

        } catch (err) {

            error.classList.remove("hidden");

        } finally {

            loading.classList.add("hidden");
        }
    }


    search.addEventListener(
        "input",
        renderAlerts
    );


    severityFilter.addEventListener(
        "change",
        renderAlerts
    );


    statusFilter.addEventListener(
        "change",
        renderAlerts
    );


    typeFilter.addEventListener(
        "change",
        renderAlerts
    );


    document.getElementById("refreshAlerts")
        .addEventListener(
            "click",
            loadAlerts
        );


    document.getElementById("retryAlertsButton")
        .addEventListener(
            "click",
            loadAlerts
        );


    container.addEventListener("click", event => {

        const button = event.target.closest("button");

        if (!button) {
            return;
        }

        const id = Number(button.dataset.id);
        const action = button.dataset.action;


        changeStatus(
            id,
            action === "resolve"
                ? "RESOLVED"
                : "ACKNOWLEDGED"
        );
    });


    acknowledgeButton.addEventListener(
        "click",
        () => {

            if (selectedAlert) {

                changeStatus(
                    selectedAlert.id,
                    "ACKNOWLEDGED"
                );
            }
        }
    );


    resolveButton.addEventListener(
        "click",
        () => {

            if (selectedAlert) {

                changeStatus(
                    selectedAlert.id,
                    "RESOLVED"
                );
            }
        }
    );


    closeModal.addEventListener(
        "click",
        closeDetails
    );


    overlay.addEventListener(
        "click",
        closeDetails
    );


    document.addEventListener(
        "keydown",
        event => {

            if (event.key === "Escape") {
                closeDetails();
            }
        }
    );


    loadAlerts();

});
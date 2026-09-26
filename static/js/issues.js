document.addEventListener("DOMContentLoaded", function () {
    const issuesContainer = document.getElementById("issuesContainer");
    const issuesLoading = document.getElementById("issuesLoading");
    const issuesError = document.getElementById("issuesError");
    const refreshButton = document.getElementById("refreshIssues");
    const retryButton = document.getElementById("retryIssuesButton");

    const severityFilter = document.getElementById("severityFilter");
    const statusFilter = document.getElementById("statusFilter");

    const detailModal = document.getElementById("issueDetailModal");
    const detailOverlay = document.getElementById("issueDetailOverlay");
    const closeDetailButton = document.getElementById("closeIssueDetail");

    const detailLoading = document.getElementById("issueDetailLoading");
    const detailError = document.getElementById("issueDetailError");
    const detailContent = document.getElementById("issueDetailContent");

    let allIssues = [];

    function show(element) {
        if (element) {
            element.classList.remove("hidden");
        }
    }

    function hide(element) {
        if (element) {
            element.classList.add("hidden");
        }
    }

    function getCSRFToken() {
        const metaToken = document.querySelector(
            'meta[name="csrf-token"]'
        );

        if (metaToken && metaToken.content) {
            return metaToken.content;
        }

        const cookie = document.cookie
            .split("; ")
            .find(function (row) {
                return row.startsWith("csrftoken=");
            });

        return cookie
            ? decodeURIComponent(cookie.split("=")[1])
            : "";
    }

    async function loadIssues() {
        hide(issuesError);
        hide(issuesContainer);
        show(issuesLoading);

        try {
            const response = await fetch("/api/issues/", {
                method: "GET",
                headers: {
                    Accept: "application/json"
                },
                credentials: "same-origin"
            });

            if (!response.ok) {
                throw new Error(
                    "Failed to load issues: " + response.status
                );
            }

            const data = await response.json();

            allIssues = Array.isArray(data.issues)
                ? data.issues
                : [];

            renderIssues(allIssues);

            hide(issuesLoading);
            show(issuesContainer);

        } catch (error) {
            console.error("Error loading issues:", error);

            hide(issuesLoading);
            hide(issuesContainer);
            show(issuesError);
        }
    }

    function renderIssues(issues) {
        if (!issuesContainer) {
            return;
        }

        const selectedSeverity = severityFilter
            ? severityFilter.value
            : "";

        const selectedStatus = statusFilter
            ? statusFilter.value
            : "";

        const filteredIssues = issues.filter(function (issue) {
            const severityMatches =
                !selectedSeverity ||
                String(issue.severity || "").toUpperCase() ===
                    String(selectedSeverity).toUpperCase();

            const statusMatches =
                !selectedStatus ||
                String(issue.status || "").toUpperCase() ===
                    String(selectedStatus).toUpperCase();

            return severityMatches && statusMatches;
        });

        if (filteredIssues.length === 0) {
            issuesContainer.innerHTML = `
                <div class="issue-empty">
                    <div class="issue-empty-icon">✓</div>
                    <h3>No issues found</h3>
                    <p>There are no data quality issues matching your filters.</p>
                </div>
            `;
            return;
        }

        let html = `
            <div class="issues-table-wrapper">
                <div class="issues-table-container">
                    <table class="issues-table">
                        <thead>
                            <tr>
                                <th>Issue</th>
                                <th>Pipeline</th>
                                <th>Dataset</th>
                                <th>Severity</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        filteredIssues.forEach(function (issue) {
            const status = String(
                issue.status || ""
            ).toUpperCase();

            const resolved = status === "RESOLVED";

            html += `
                <tr>
                    <td>
                        <div class="issue-title">
                            ${escapeHtml(
                                issue.title || "Untitled Issue"
                            )}
                        </div>
                        <div class="issue-description">
                            ${escapeHtml(
                                issue.description ||
                                "No description available."
                            )}
                        </div>
                    </td>

                    <td>
                        <span class="issue-pipeline">
                            ${escapeHtml(
                                issue.pipeline?.name || "—"
                            )}
                        </span>
                    </td>

                    <td>
                        <span class="issue-dataset">
                            ${escapeHtml(
                                issue.dataset?.name || "—"
                            )}
                        </span>
                    </td>

                    <td>
                        <span class="severity-badge ${getSeverityClass(
                            issue.severity
                        )}">
                            <span class="status-dot"></span>
                            ${formatLabel(issue.severity)}
                        </span>
                    </td>

                    <td>
                        <span class="issue-status ${getStatusClass(
                            issue.status
                        )}">
                            <span class="status-icon">
                                ${resolved ? "✓" : "!"}
                            </span>
                            ${formatLabel(issue.status)}
                        </span>
                    </td>

                    <td>
                        <div class="issue-actions">

                            <button
                                type="button"
                                class="issue-action-btn view-issue-button"
                                data-issue-id="${issue.id}"
                            >
                                <span>View Details</span>
                                <span class="button-arrow">→</span>
                            </button>

                            ${
                                resolved
                                    ? `
                                        <button
                                            type="button"
                                            class="issue-action-btn resolve-btn resolved"
                                            disabled
                                        >
                                            <span>✓</span>
                                            <span>Resolved</span>
                                        </button>
                                    `
                                    : `
                                        <button
                                            type="button"
                                            class="issue-action-btn resolve-btn resolve-issue-button"
                                            data-issue-id="${issue.id}"
                                        >
                                            <span>Resolve</span>
                                        </button>
                                    `
                            }

                        </div>
                    </td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        issuesContainer.innerHTML = html;
    }

    if (issuesContainer) {
        issuesContainer.addEventListener("click", function (event) {
            const viewButton = event.target.closest(
                ".view-issue-button"
            );

            const resolveButton = event.target.closest(
                ".resolve-issue-button"
            );

            if (viewButton) {
                event.preventDefault();

                const issueId =
                    viewButton.getAttribute("data-issue-id");

                if (!issueId) {
                    console.error(
                        "View Details button has no issue ID."
                    );
                    return;
                }

                openIssueDetail(issueId);
                return;
            }

            if (resolveButton) {
                event.preventDefault();

                if (resolveButton.disabled) {
                    return;
                }

                const issueId =
                    resolveButton.getAttribute("data-issue-id");

                if (!issueId) {
                    console.error(
                        "Resolve button has no issue ID."
                    );
                    return;
                }

                resolveIssue(issueId, resolveButton);
            }
        });
    }

    async function openIssueDetail(issueId) {
        if (!detailModal) {
            console.error(
                "Issue detail modal was not found."
            );
            return;
        }

        detailModal.classList.remove("hidden");
        document.body.classList.add("modal-open");

        hide(detailError);
        hide(detailContent);
        show(detailLoading);

        try {
            const response = await fetch(
                "/api/issues/" + issueId + "/",
                {
                    method: "GET",
                    headers: {
                        Accept: "application/json"
                    },
                    credentials: "same-origin"
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Failed to load issue: " +
                    response.status
                );
            }

            const data = await response.json();
            const issue = data.issue || data;

            populateIssueDetail(issue);

            hide(detailLoading);
            show(detailContent);

        } catch (error) {
            console.error(
                "Error loading issue details:",
                error
            );

            hide(detailLoading);
            show(detailError);
        }
    }

    async function resolveIssue(issueId, button) {
    if (button) {
        button.disabled = true;
        button.textContent = "Resolving...";
    }

    try {
        const csrfToken = getCSRFToken();

        if (!csrfToken) {
            throw new Error(
                "CSRF token not found. Please refresh the page."
            );
        }

        const response = await fetch(
            "/api/issues/" + issueId + "/status/",
            {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin"
            }
        );

        if (!response.ok) {
            throw new Error(
                "Failed to resolve issue: " + response.status
            );
        }

        alert("Issue resolved successfully.");

        await loadIssues();

    } catch (error) {
        console.error(
            "Error resolving issue:",
            error
        );

        if (button) {
            button.disabled = false;
            button.textContent = "Resolve";
        }

        alert(
            error.message ||
            "Unable to resolve this issue."
        );
    }
}

    function populateIssueDetail(issue) {
        setText(
            "detailTitle",
            issue.title || "Issue Details"
        );

        const severityElement =
            document.getElementById("detailSeverity");

        if (severityElement) {
            severityElement.textContent =
                formatLabel(issue.severity);

            severityElement.className =
                "severity-badge " +
                getSeverityClass(issue.severity);
        }

        const statusElement =
            document.getElementById("detailStatus");

        if (statusElement) {
            statusElement.textContent =
                formatLabel(issue.status);

            statusElement.className =
                "issue-status " +
                getStatusClass(issue.status);
        }

        setText(
            "detailDescription",
            issue.description ||
            "No description available."
        );

        setText(
            "detailPipeline",
            issue.pipeline?.name || "—"
        );

        setText(
            "detailDataset",
            issue.dataset?.name || "—"
        );

        setText(
            "detailCheckName",
            issue.check?.name || "—"
        );

        setText(
            "detailColumn",
            issue.check?.column || "—"
        );

        setText(
            "detailCheckType",
            issue.check?.type || "—"
        );

        const qualityScore =
            issue.run?.quality_score;

        setText(
            "detailQualityScore",
            qualityScore !== null &&
            qualityScore !== undefined
                ? qualityScore + "%"
                : "—"
        );

        setText(
            "detailRowsChecked",
            issue.check?.rows_checked ?? "—"
        );

        setText(
            "detailRowsPassed",
            issue.check?.rows_passed ?? "—"
        );

        setText(
            "detailRowsFailed",
            issue.check?.rows_failed ?? "—"
        );

        const passRate =
            issue.check?.pass_rate;

        setText(
            "detailPassRate",
            passRate !== null &&
            passRate !== undefined
                ? passRate + "%"
                : "—"
        );

        setText(
            "detailAIAnalysis",
            issue.ai_analysis ||
            "No AI analysis available."
        );

        setText(
            "detailAIRecommendation",
            issue.ai_recommendation ||
            "No AI recommendation available."
        );

        const detailsElement =
            document.getElementById(
                "detailCheckDetails"
            );

        if (detailsElement) {
            const details = issue.check?.details;

            if (
                details !== null &&
                details !== undefined
            ) {
                detailsElement.textContent =
                    typeof details === "object"
                        ? JSON.stringify(
                            details,
                            null,
                            2
                        )
                        : String(details);
            } else {
                detailsElement.textContent =
                    "No additional details available.";
            }
        }

        setText(
            "detailIssueId",
            issue.id
        );

        setText(
            "detailRunId",
            issue.run?.id
        );

        setText(
            "detailCreatedAt",
            formatDate(issue.created_at)
        );
    }

    function closeIssueDetail() {
        if (detailModal) {
            detailModal.classList.add("hidden");
        }

        document.body.classList.remove(
            "modal-open"
        );
    }

    function setText(elementId, value) {
        const element =
            document.getElementById(elementId);

        if (!element) {
            return;
        }

        element.textContent =
            value === null ||
            value === undefined ||
            value === ""
                ? "—"
                : String(value);
    }

    function getSeverityClass(severity) {
        if (!severity) {
            return "";
        }

        return (
            "severity-" +
            String(severity).toLowerCase()
        );
    }

    function getStatusClass(status) {
        if (!status) {
            return "";
        }

        return (
            "status-" +
            String(status)
                .toLowerCase()
                .replace(/_/g, "-")
        );
    }

    function formatLabel(value) {
        if (!value) {
            return "—";
        }

        return String(value)
            .toLowerCase()
            .replace(/_/g, " ")
            .replace(/\b\w/g, function (letter) {
                return letter.toUpperCase();
            });
    }

    function formatDate(value) {
        if (!value) {
            return "—";
        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString();
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

    refreshButton?.addEventListener(
        "click",
        loadIssues
    );

    retryButton?.addEventListener(
        "click",
        loadIssues
    );

    severityFilter?.addEventListener(
        "change",
        function () {
            renderIssues(allIssues);
        }
    );

    statusFilter?.addEventListener(
        "change",
        function () {
            renderIssues(allIssues);
        }
    );

    closeDetailButton?.addEventListener(
        "click",
        closeIssueDetail
    );

    detailOverlay?.addEventListener(
        "click",
        closeIssueDetail
    );

    document.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key === "Escape" &&
                detailModal &&
                !detailModal.classList.contains("hidden")
            ) {
                closeIssueDetail();
            }
        }
    );

    loadIssues();
});
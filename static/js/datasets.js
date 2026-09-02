document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("datasetModal");
    const openButton = document.getElementById("uploadDatasetButton");
    const emptyButton = document.getElementById("emptyUploadButton");
    const closeButton = document.getElementById("closeDatasetForm");
    const cancelButton = document.getElementById("cancelDatasetButton");
    const fileInput = document.getElementById("datasetFile");
    const selectedFile = document.getElementById("selectedFileName");
    const searchInput = document.getElementById("datasetSearch");
    const sourceFilter = document.getElementById("datasetSourceFilter");
    const statusFilter = document.getElementById("datasetStatusFilter");

    function openModal() {
        if (!modal) {
            return;
        }

        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");

        const nameInput = document.getElementById("datasetName");

        if (nameInput) {
            setTimeout(function () {
                nameInput.focus();
            }, 100);
        }
    }

    function closeModal() {
        if (!modal) {
            return;
        }

        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
    }

    function updateSelectedFile() {
        if (!fileInput || !selectedFile) {
            return;
        }

        if (fileInput.files.length > 0) {
            selectedFile.textContent = fileInput.files[0].name;
        } else {
            selectedFile.textContent = "";
        }
    }

    function filterDatasets() {
        const cards = document.querySelectorAll(".dataset-card");

        const searchValue = searchInput
            ? searchInput.value.toLowerCase().trim()
            : "";

        const sourceValue = sourceFilter
            ? sourceFilter.value.toLowerCase()
            : "all";

        const statusValue = statusFilter
            ? statusFilter.value.toLowerCase()
            : "all";

        let visibleCount = 0;

        cards.forEach(function (card) {
            const name = card.dataset.name || "";
            const source = card.dataset.source || "";
            const status = card.dataset.status || "";

            const matchesSearch = name.includes(searchValue);
            const matchesSource =
                sourceValue === "all" ||
                source === sourceValue;

            const matchesStatus =
                statusValue === "all" ||
                status === statusValue;

            const visible =
                matchesSearch &&
                matchesSource &&
                matchesStatus;

            card.style.display = visible ? "" : "none";

            if (visible) {
                visibleCount++;
            }
        });

        const emptyState = document.getElementById("datasetsEmpty");

        if (emptyState && cards.length > 0) {
            emptyState.style.display =
                visibleCount === 0 ? "block" : "none";
        }
    }

    if (openButton) {
        openButton.addEventListener("click", openModal);
    }

    if (emptyButton) {
        emptyButton.addEventListener("click", openModal);
    }

    if (closeButton) {
        closeButton.addEventListener("click", closeModal);
    }

    if (cancelButton) {
        cancelButton.addEventListener("click", closeModal);
    }

    if (fileInput) {
        fileInput.addEventListener(
            "change",
            updateSelectedFile
        );
    }

    if (modal) {
        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener(
            "input",
            filterDatasets
        );
    }

    if (sourceFilter) {
        sourceFilter.addEventListener(
            "change",
            filterDatasets
        );
    }

    if (statusFilter) {
        statusFilter.addEventListener(
            "change",
            filterDatasets
        );
    }

    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape" &&
            modal &&
            !modal.classList.contains("hidden")
        ) {
            closeModal();
        }
    });
});
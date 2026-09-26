document.addEventListener("DOMContentLoaded", function () {
const modal = document.getElementById("createPipelineModal");
const openButton = document.getElementById("openCreatePipelineModal");
const openEmptyButton = document.getElementById("openCreatePipelineEmpty");
const closeButton = document.getElementById("closeCreatePipelineModal");
const cancelButton = document.getElementById("cancelCreatePipeline");


if (!modal) {
    return;
}

function openModal() {
    modal.classList.add("active");
    modal.setAttribute("aria-hidden", "false");

    const nameInput = document.getElementById("pipelineName");

    if (nameInput) {
        setTimeout(function () {
            nameInput.focus();
        }, 100);
    }

    document.body.classList.add("modal-open");
}

function closeModal() {
    modal.classList.remove("active");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
}

if (openButton) {
    openButton.addEventListener("click", openModal);
}

if (openEmptyButton) {
    openEmptyButton.addEventListener("click", openModal);
}

if (closeButton) {
    closeButton.addEventListener("click", closeModal);
}

if (cancelButton) {
    cancelButton.addEventListener("click", closeModal);
}

modal.addEventListener("click", function (event) {
    if (event.target === modal) {
        closeModal();
    }
});

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && modal.classList.contains("active")) {
        closeModal();
    }
});


});

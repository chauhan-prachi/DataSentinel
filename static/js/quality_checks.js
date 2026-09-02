document.addEventListener("DOMContentLoaded", function () {
const formContainer = document.getElementById(
"qualityCheckFormContainer"
);


const showButton = document.getElementById(
    "showQualityCheckForm"
);

const emptyButton = document.getElementById(
    "emptyAddQualityCheck"
);

const closeButton = document.getElementById(
    "closeQualityCheckForm"
);

const cancelButton = document.getElementById(
    "cancelQualityCheck"
);

function showForm() {
    if (formContainer) {
        formContainer.classList.remove("hidden");
    }
}

function hideForm() {
    if (formContainer) {
        formContainer.classList.add("hidden");
    }
}

if (showButton) {
    showButton.addEventListener(
        "click",
        showForm
    );
}

if (emptyButton) {
    emptyButton.addEventListener(
        "click",
        showForm
    );
}

if (closeButton) {
    closeButton.addEventListener(
        "click",
        hideForm
    );
}

if (cancelButton) {
    cancelButton.addEventListener(
        "click",
        hideForm
    );
}


});

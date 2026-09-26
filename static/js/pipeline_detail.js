document.addEventListener("DOMContentLoaded", function () {
    const runForms = document.querySelectorAll(
        'form[action*="/run/"]'
    );

    runForms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector(
                'button[type="submit"]'
            );

            if (!button || button.disabled) {
                return;
            }

            button.disabled = true;

            button.dataset.originalText =
                button.innerHTML;

            button.innerHTML =
                '<span class="run-icon">⏳</span> Running...';
        });
    });
});
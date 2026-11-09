// utils.js — utilitários compartilhados

export function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export function showLoading() {
    $("#loadingOverlay").show();
}

export function hideLoading() {
    $("#loadingOverlay").hide();
}

export function initializeTooltips() {
    // Inicializar tooltips do Bootstrap se disponível
    if (typeof bootstrap !== "undefined" && bootstrap.Tooltip) {
        $('[data-bs-toggle="tooltip"]').each(function () {
            new bootstrap.Tooltip(this);
        });
    }
}

export function showNotification(message, type = "info") {
    const $notification = $("<div>")
        .addClass(`alert alert-${type} alert-dismissible fade show position-fixed`)
        .css({
            top: "20px",
            right: "20px",
            "z-index": "9999",
            "min-width": "300px"
        })
        .html(`
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `);

    $("body").append($notification);

    setTimeout(() => {
        $notification.remove();
    }, 3000);
}

export function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = $("<a>").attr({
        href: url,
        download: filename,
        "data-no-loading": "true"
    })[0];

    $("body").append(link);
    link.click();
    $(link).remove();
    URL.revokeObjectURL(url);
}
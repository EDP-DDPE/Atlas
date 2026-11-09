// resize.js — redimensionamento de colunas
export function setupColumnResizing() {
    const $table = $("#estudosTable");
    let isResizing = false;
    let currentColumn = null;
    let startX = 0;
    let startWidth = 0;

    $(".resize-handle").on("mousedown", function (e) {
        e.preventDefault();
        isResizing = true;
        currentColumn = $(this).closest("th");
        startX = e.clientX;
        startWidth = parseInt(currentColumn.css("width"), 10);

        $(document).on("mousemove", handleResize);
        $(document).on("mouseup", stopResize);

        // Cursor de redimensionamento
        $("body").css("cursor", "col-resize");
        $table.css("user-select", "none");
    });

    function handleResize(e) {
        if (!isResizing) return;

        const width = startWidth + e.clientX - startX;
        if (width > 50) { // Largura mínima
            currentColumn.css({
                width: width + "px",
                "min-width": width + "px"
            });
        }
    }

    function stopResize() {
        isResizing = false;
        currentColumn = null;
        $("body").css("cursor", "");
        $table.css("user-select", "");

        $(document).off("mousemove", handleResize);
        $(document).off("mouseup", stopResize);
    }
}
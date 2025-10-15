// Lightweight drag & drop for Django tabular inlines
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".inline-group").forEach(function (group) {
    // Only activate when our handle exists (this is the FormField inline)
    if (!group.querySelector(".drag-handle")) return;

    const tbody = group.querySelector("tbody");
    if (!tbody) return;

    let draggingRow = null;

    // Make all inline rows draggable
    tbody.querySelectorAll("tr.form-row").forEach(prepareRow);

    function prepareRow(row) {
      row.setAttribute("draggable", "true");

      row.addEventListener("dragstart", function (e) {
        draggingRow = row;
        row.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
      });

      row.addEventListener("dragover", function (e) {
        e.preventDefault(); // allow drop
        const target = closestRow(e.target);
        if (!target || target === draggingRow) return;

        const rect = target.getBoundingClientRect();
        const after = (e.clientY - rect.top) > rect.height / 2;
        tbody.insertBefore(draggingRow, after ? target.nextSibling : target);
      });

      row.addEventListener("dragend", function () {
        row.classList.remove("dragging");
        draggingRow = null;
        renumber();
      });

      // Only start dragging when user grabs the handle (feel nicer)
      const handle = row.querySelector(".drag-handle");
      if (handle) {
        handle.addEventListener("mousedown", function () {
          row.setAttribute("draggable", "true");
        });
        handle.addEventListener("mouseup", function () {
          row.removeAttribute("draggable"); // prevent accidental drags via inputs
        });
      }
    }

    function closestRow(el) {
      while (el && el.tagName !== "TR") el = el.parentElement;
      return el && el.classList.contains("form-row") ? el : null;
    }

    // Write sequential values into the hidden "order" inputs
    function renumber() {
      const rows = tbody.querySelectorAll("tr.form-row");
      rows.forEach(function (row, idx) {
        const orderInput = row.querySelector('input[name$="-order"]');
        if (orderInput) orderInput.value = String(idx + 1);
      });
    }
  });
});
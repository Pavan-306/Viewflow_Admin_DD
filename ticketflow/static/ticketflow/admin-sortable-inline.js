<<<<<<< HEAD
console.log("✅ TicketFlow sortable script loaded");
window.__tf_test = true;

function initTicketFlowDrag() {
  // Try to locate your inline table dynamically
  const table =
    document.querySelector(".inline-group table") ||
    document.querySelector("table.tabular") ||
    document.querySelector("table[data-inline-formset]");

  if (!table) {
    console.warn("⏳ Waiting for inline table...");
    // Retry every 500ms until table appears (max 10 tries)
    window.__tf_tryCount = (window.__tf_tryCount || 0) + 1;
    if (window.__tf_tryCount < 10) {
      return setTimeout(initTicketFlowDrag, 500);
    }
    console.error("❌ No inline table found after waiting.");
    return;
  }

  console.log("📋 Found table:", table);

  const rows = table.querySelectorAll("tbody tr");
  rows.forEach((row) => {
    row.draggable = true;
    const handle = row.querySelector(".drag-handle");
    if (handle) {
      handle.style.cursor = "grab";
      handle.addEventListener("mousedown", (e) => e.stopPropagation());
    }

    row.addEventListener("dragstart", (e) => {
      row.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    row.addEventListener("dragend", () => {
      row.classList.remove("dragging");
      updateOrder();
    });
  });

  table.addEventListener("dragover", (e) => {
    e.preventDefault();
    const dragging = table.querySelector(".dragging");
    if (!dragging) return;
    const after = getDragAfterElement(table, e.clientY);
    if (after == null) {
      table.querySelector("tbody").appendChild(dragging);
    } else {
      table.querySelector("tbody").insertBefore(dragging, after);
    }
  });

  function getDragAfterElement(container, y) {
    const rows = [
      ...container.querySelectorAll("tbody tr:not(.dragging)"),
    ];
    return rows.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        } else {
          return closest;
        }
      },
      { offset: Number.NEGATIVE_INFINITY }
    ).element;
  }

  function updateOrder() {
    const visibleRows = table.querySelectorAll("tbody tr");
    visibleRows.forEach((tr, index) => {
      const orderInput = tr.querySelector('input[name$="-order"]');
      if (orderInput) {
        orderInput.value = index + 1;
      }
    });
    console.log("✅ Order updated and ready to save");
  }

  console.log("✅ Drag-and-drop initialized");
}

// Run after DOM ready (also works for new admin React load timing)
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(initTicketFlowDrag, 1000);
=======
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
>>>>>>> fdf29d2f0ac61c6446c9c584273eaf771456bb06
});
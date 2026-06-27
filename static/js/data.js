"use strict";
// Data viewer: filters, downloads, review modal (save-to-DB + add category).
(function () {
  const $ = s => document.querySelector(s);
  let currentId = null, currentDoc = null;

  function filterQS() {
    const p = new URLSearchParams();
    if ($("#f-vendor").value) p.set("vendor", $("#f-vendor").value);
    if ($("#f-category").value) p.set("category", $("#f-category").value);
    if ($("#f-status").value) p.set("status", $("#f-status").value);
    if ($("#f-from").value) p.set("date_from", $("#f-from").value);
    if ($("#f-to").value) p.set("date_to", $("#f-to").value);
    return p.toString();
  }
  function refreshDownloads() {
    const qs = filterQS();
    $("#dl-csv").href = "/processing/export/csv/?" + qs;
    $("#dl-xlsx").href = "/processing/export/xlsx/?" + qs;
    $("#dl-json").href = "/processing/export/json/?" + qs;
  }
  ["f-vendor","f-category","f-status","f-from","f-to"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", refreshDownloads);
  });
  refreshDownloads();

  // category select -> reveal "new category" field
  const catSel = $("#save-category"), newCat = $("#new-category");
  if (catSel) catSel.addEventListener("change", () => {
    newCat.style.display = catSel.value === "__new__" ? "" : "none";
    if (catSel.value === "__new__") newCat.focus();
  });

  // open review modal
  document.querySelectorAll(".view-btn").forEach(b =>
    b.addEventListener("click", () => openReview(b.dataset.id)));

  // toggle items sub-row
  document.querySelectorAll(".items-btn").forEach(b =>
    b.addEventListener("click", () => {
      const row = document.getElementById("items-" + b.dataset.id);
      if (!row) return;
      const visible = row.style.display !== "none";
      row.style.display = visible ? "none" : "";
      b.textContent = visible
        ? `Items (${b.dataset.id})`.replace(/\(\d+\)/, m => m)
        : b.textContent;
    }));

  async function openReview(id) {
    currentId = id;
    try {
      currentDoc = await window.DF.api(`/api/processing/documents/${id}/`);
      $("#json-target").innerHTML = window.DF.highlight(currentDoc.raw_json || currentDoc);
      if (currentDoc.category) catSel.value = String(currentDoc.category.id);
      else catSel.value = "";
      newCat.style.display = "none";
      $("#review-modal").classList.add("open");
    } catch (e) { alert("Could not load document"); }
  }
  $("#close-modal").addEventListener("click", () => $("#review-modal").classList.remove("open"));

  // Download JSON for just the extraction being reviewed (alongside save-to-DB)
  $("#modal-dl-json").addEventListener("click", e => {
    e.preventDefault();
    if (!currentDoc) return;
    const data = currentDoc.raw_json || currentDoc;
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `extraction-${currentId}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(a.href);
  });

  // save to database (optionally creating a new category)
  $("#save-db-btn").addEventListener("click", async () => {
    const body = {};
    if (catSel.value === "__new__") body.new_category = newCat.value.trim();
    else if (catSel.value) body.category_id = parseInt(catSel.value, 10);
    try {
      const d = await window.DF.api(`/api/processing/documents/${currentId}/save_to_db/`,
        {method: "POST", body: JSON.stringify(body)});
      const row = document.querySelector(`tr[data-id="${currentId}"]`);
      if (row) {
        row.children[4].textContent = d.category ? d.category.name : "—";
        row.children[5].innerHTML = '<span class="status-chip status-completed">saved</span>';
      }
      $("#review-modal").classList.remove("open");
    } catch (e) { alert("Save failed: " + (e.data && e.data.detail || e.status)); }
  });
})();

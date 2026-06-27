"use strict";
// Multi-file drag&drop upload with progress + status polling.
(function () {
  const dz = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const list = document.getElementById("upload-list");
  if (!dz) return;
  document.getElementById("browse-btn").addEventListener("click", () => input.click());
  dz.addEventListener("click", e => { if (e.target === dz) input.click(); });
  dz.addEventListener("dragover", e => { e.preventDefault(); dz.classList.add("drag"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
  dz.addEventListener("drop", e => {
    e.preventDefault(); dz.classList.remove("drag");
    if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
  });
  input.addEventListener("change", () => input.files.length && upload(input.files));

  function rowFor(name) {
    const el = document.createElement("div");
    el.className = "upload-row";
    el.innerHTML = `<span style="width:200px;overflow:hidden;text-overflow:ellipsis">${name}</span>
      <div class="progress"><div class="bar"></div></div>
      <span class="status-chip status-pending">queued</span>`;
    list.appendChild(el);
    return el;
  }

  function upload(files) {
    const fd = new FormData();
    const rows = [];
    [...files].forEach(f => { fd.append("files", f); rows.push(rowFor(f.name)); });
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/uploads/ingest/");
    xhr.setRequestHeader("X-CSRFToken", window.DF.csrf());
    xhr.upload.onprogress = e => {
      if (e.lengthComputable) {
        const pct = (e.loaded / e.total) * 100;
        rows.forEach(r => r.querySelector(".bar").style.width = pct + "%");
      }
    };
    xhr.onload = () => {
      let res = {};
      try { res = JSON.parse(xhr.responseText); } catch {}
      (res.files || []).forEach((f, i) => {
        const r = rows[i]; if (!r) return;
        const chip = r.querySelector(".status-chip");
        r.querySelector(".bar").style.width = "100%";
        if (f.ok) { chip.textContent = "processing"; chip.className = "status-chip status-processing";
          poll(f.file_id, chip); }
        else { chip.textContent = "rejected"; chip.className = "status-chip status-failed";
          chip.title = f.error; }
      });
    };
    xhr.onerror = () => rows.forEach(r => {
      const c = r.querySelector(".status-chip"); c.textContent = "error"; c.className = "status-chip status-failed";
    });
    xhr.send(fd);
  }

  async function poll(fileId, chip, tries = 0) {
    if (tries > 40) return;
    try {
      const d = await window.DF.api(`/api/uploads/files/${fileId}/`);
      chip.textContent = d.status;
      chip.className = "status-chip status-" + d.status;
      if (d.status === "processing" || d.status === "pending")
        setTimeout(() => poll(fileId, chip, tries + 1), 1500);
    } catch { setTimeout(() => poll(fileId, chip, tries + 1), 2000); }
  }
})();

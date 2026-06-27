"use strict";
// Review & Map: build a line payload and POST it to confirm the scan.
(function () {
  const el = document.getElementById("review-data");
  if (!el) return;
  const R = JSON.parse(el.textContent);
  const $ = s => document.querySelector(s);
  $("#raw-json").innerHTML = window.DF.highlight(R.raw || {});

  const tbody = $("#line-table").querySelector("tbody");
  function productSelect() {
    const opts = ['<option value="">— new product —</option>'].concat(
      (R.products || []).map(p =>
        `<option value="${p.id}">${escapeHtml(p.name)} (${escapeHtml(p.sku)})</option>`));
    return `<select class="field line-prod">${opts.join("")}</select>`;
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g,
      c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  }
  (R.items || []).forEach(it => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td><input class="field line-desc" value="${escapeHtml(it.name)}"></td>
       <td><input class="field line-qty" type="number" step="any" value="${it.quantity||0}" style="width:80px"></td>
       <td><input class="field line-rate" type="number" step="any" value="${it.unit_price||""}" style="width:100px"></td>
       <td><input class="field line-amt" type="number" step="any" value="${it.amount||""}" style="width:110px"></td>
       <td>${productSelect()}</td>`;
    tbody.appendChild(tr);
  });
  if (!(R.items || []).length) {
    tbody.innerHTML = '<tr><td colspan="5" class="muted">No line items detected — reject, or post and add stock manually.</td></tr>';
  }

  function collect() {
    return [...tbody.querySelectorAll("tr")].filter(tr => tr.querySelector(".line-desc")).map(tr => {
      const pid = tr.querySelector(".line-prod").value;
      const desc = tr.querySelector(".line-desc").value.trim();
      const spec = {
        description: desc,
        quantity: tr.querySelector(".line-qty").value || 0,
        unit_price: tr.querySelector(".line-rate").value || null,
        amount: tr.querySelector(".line-amt").value || null,
      };
      if (pid) spec.product_id = parseInt(pid, 10);
      else spec.new_product = {name: desc};
      return spec;
    });
  }
  async function send(body) {
    return window.DF.api(R.url, {method: "POST", body: JSON.stringify(body)});
  }
  $("#confirm-btn").addEventListener("click", async () => {
    try {
      const d = await send({kind: $("#m-kind").value, party_name: $("#m-party").value,
        number: $("#m-number").value, lines: collect()});
      alert(`Posted ${d.kind} (txn #${d.transaction_id}). Stock updated.`);
      window.location.href = R.queueUrl;
    } catch (e) { alert("Could not post: " + (e.data && e.data.detail || e.status)); }
  });
  $("#reject-btn").addEventListener("click", async () => {
    if (!confirm("Reject this scan?")) return;
    try { await send({action: "reject"}); window.location.href = R.queueUrl; }
    catch (e) { alert("Failed: " + (e.status || e)); }
  });
})();

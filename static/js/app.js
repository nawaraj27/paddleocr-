"use strict";
// Shared helpers: CSRF, theme, fetch wrapper.
window.DF = (function () {
  function csrf() {
    return window.CSRF_TOKEN ||
      (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  }
  async function api(url, opts = {}) {
    opts.headers = Object.assign(
      {"X-CSRFToken": csrf()},
      opts.body instanceof FormData ? {} : {"Content-Type": "application/json"},
      opts.headers || {});
    opts.credentials = "same-origin";
    const r = await fetch(url, opts);
    const ct = r.headers.get("content-type") || "";
    const data = ct.includes("application/json") ? await r.json() : await r.text();
    if (!r.ok) throw Object.assign(new Error("request failed"), {status: r.status, data});
    return data;
  }
  function highlight(obj) {
    const s = JSON.stringify(obj, null, 2) || "{}";
    return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))
      .replace(/("(\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(\.\d+)?/g,
        (m, str, _g, colon, kw) => {
          if (str) return colon ? `<span class="jkey">${str}</span>:`
                                : `<span class="jstr">${str}</span>`;
          if (kw === "true" || kw === "false") return `<span class="jbool">${m}</span>`;
          if (kw === "null") return `<span class="jnull">null</span>`;
          return `<span class="jnum">${m}</span>`;
        });
  }
  return {csrf, api, highlight};
})();

// Theme toggle
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("df-theme");
  if (saved) root.setAttribute("data-theme", saved);
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("df-theme", next);
  });
})();

// Shared UI behavior: button loading states on form submit, and a
// fetch-based report download so the button spinner reflects real
// completion instead of guessing with a timeout.

document.addEventListener("DOMContentLoaded", function () {
  // ---- Generic "disable + spinner" on any form submit ----
  // Opt out per-form with data-no-loading.
  document.querySelectorAll("form:not([data-no-loading])").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      // Forms that need a confirmation dialog declare it via
      // data-confirm="..." instead of an inline onsubmit handler, so we
      // can bail out here -- before showing any loading state -- if the
      // user cancels.
      const confirmMsg = form.getAttribute("data-confirm");
      if (confirmMsg && !window.confirm(confirmMsg)) {
        e.preventDefault();
        return;
      }

      // Respect the browser's own validation next -- don't lock the
      // button if required fields are empty or invalid.
      if (form.checkValidity && !form.checkValidity()) return;

      // e.submitter is the actual button that triggered this submit
      // (works whether or not it has an explicit type="submit").
      const submitBtn = e.submitter || form.querySelector('button[type="submit"], button:not([type])');
      if (!submitBtn || submitBtn.disabled || submitBtn.type === "button") return;

      const hasLabelAttr = submitBtn.hasAttribute("data-loading-text");
      const label = hasLabelAttr ? submitBtn.getAttribute("data-loading-text") : "Working…";
      submitBtn.dataset.originalHtml = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = label ? `<span class="spinner"></span> ${label}` : `<span class="spinner"></span>`;
    });
  });

  // ---- Sidebar collapse-to-icons, persisted across page loads ----
  const sidebar = document.getElementById("sidebar");
  const collapseBtn = document.getElementById("sidebarCollapseBtn");
  if (sidebar && collapseBtn) {
    if (localStorage.getItem("bookit_sidebar_collapsed") === "1") {
      sidebar.classList.add("collapsed");
    }
    collapseBtn.addEventListener("click", function () {
      const collapsed = sidebar.classList.toggle("collapsed");
      localStorage.setItem("bookit_sidebar_collapsed", collapsed ? "1" : "0");
    });
  }
});

// ---- Toast notifications ----
// Usage: showToast({ title: "Checked in", body: "...", variant: "success" })
// variant: "info" | "success" | "warning" | "danger"
function showToast({ title, body = "", variant = "info", duration = 5000 } = {}) {
  const stack = document.getElementById("toastStack");
  if (!stack) return;

  const icons = { info: "bi-info-circle", success: "bi-check-circle", warning: "bi-exclamation-triangle", danger: "bi-x-circle" };
  const toast = document.createElement("div");
  toast.className = `bookit-toast ${variant}`;
  toast.innerHTML = `
    <div class="toast-icon"><i class="bi ${icons[variant] || icons.info}"></i></div>
    <div>
      <div class="toast-title">${title}</div>
      ${body ? `<div class="toast-body">${body}</div>` : ""}
    </div>
    <button class="toast-close" aria-label="Dismiss">&times;</button>
  `;
  stack.appendChild(toast);

  function dismiss() {
    toast.classList.add("hide");
    setTimeout(() => toast.remove(), 200);
  }
  toast.querySelector(".toast-close").addEventListener("click", dismiss);
  if (duration > 0) setTimeout(dismiss, duration);
}

// ---- Report export: fetch the file so the button reflects real progress ----
async function exportReport(type, format, btn) {
  const from = document.getElementById(`${type}-from`).value;
  const to = document.getElementById(`${type}-to`).value;
  let url = `/reports/${type}/${format}?`;
  if (from) url += `date_from=${from}&`;
  if (to) url += `date_to=${to}&`;

  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Preparing…`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename=([^;]+)/);
    const filename = match ? match[1].trim() : `${type}_report.${format}`;

    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (err) {
    btn.insertAdjacentHTML(
      "afterend",
      `<div class="text-danger small mt-2 export-error">Couldn't generate the report. Try again.</div>`
    );
    setTimeout(() => document.querySelectorAll(".export-error").forEach(n => n.remove()), 4000);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

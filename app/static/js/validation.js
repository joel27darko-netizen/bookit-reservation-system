// Inline, cross-field validation feedback: end-after-start time checks,
// party size vs. resource capacity, and open/close hour sanity -- shown
// live as the person types/selects, backed by the browser's own
// constraint validation (setCustomValidity) as the enforcement layer.

function showFieldError(errorEl, message) {
  if (!errorEl) return;
  const span = errorEl.querySelector("span") || errorEl;
  span.textContent = message;
  errorEl.classList.add("show");
}

function clearFieldError(errorEl) {
  if (!errorEl) return;
  errorEl.classList.remove("show");
}

function wireTimeRangeValidation(form, startSelector, endSelector, errorSelector) {
  const startEl = form.querySelector(startSelector);
  const endEl = form.querySelector(endSelector);
  const errorEl = form.querySelector(errorSelector);
  if (!startEl || !endEl) return;

  function validate() {
    if (startEl.value && endEl.value && endEl.value <= startEl.value) {
      endEl.setCustomValidity("End time must be after start time");
      endEl.classList.add("is-invalid");
      startEl.classList.add("is-invalid");
      showFieldError(errorEl, "End time must be after the start time.");
      return false;
    }
    endEl.setCustomValidity("");
    endEl.classList.remove("is-invalid");
    startEl.classList.remove("is-invalid");
    clearFieldError(errorEl);
    return true;
  }
  startEl.addEventListener("input", validate);
  endEl.addEventListener("input", validate);
  form.addEventListener("submit", function (e) { if (!validate()) e.preventDefault(); });
}

function wirePartySizeValidation(form) {
  const resourceSelect = form.querySelector("#resourceSelect");
  const partyInput = form.querySelector("#partySizeInput");
  const errorEl = form.querySelector("#partySizeError");
  if (!resourceSelect || !partyInput) return;

  function validate() {
    const opt = resourceSelect.selectedOptions[0];
    const capacity = opt ? parseInt(opt.dataset.capacity || "0", 10) : 0;
    const size = parseInt(partyInput.value || "0", 10);

    if (opt && opt.value && size > capacity) {
      partyInput.setCustomValidity(`Max capacity is ${capacity}`);
      partyInput.classList.add("is-invalid");
      showFieldError(errorEl, `This resource holds up to ${capacity} ${capacity === 1 ? "guest" : "guests"}.`);
      return false;
    }
    partyInput.setCustomValidity("");
    partyInput.classList.remove("is-invalid");
    clearFieldError(errorEl);
    return true;
  }
  resourceSelect.addEventListener("change", validate);
  partyInput.addEventListener("input", validate);
  form.addEventListener("submit", function (e) { if (!validate()) e.preventDefault(); });
}

document.addEventListener("DOMContentLoaded", function () {
  const bookingForm = document.getElementById("bookingForm");
  if (bookingForm) {
    wireTimeRangeValidation(bookingForm, "#startTimeInput", "#endTimeInput", "#timeRangeError");
    wirePartySizeValidation(bookingForm);
  }

  document.querySelectorAll("form.js-reschedule-form").forEach(function (form) {
    wireTimeRangeValidation(form, 'input[name="start_time"]', 'input[name="end_time"]', ".field-error");
  });

  document.querySelectorAll("form.js-hours-form").forEach(function (form) {
    wireTimeRangeValidation(form, 'input[name="open_time"]', 'input[name="close_time"]', ".field-error");
  });
});

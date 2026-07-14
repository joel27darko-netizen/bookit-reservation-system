// Real-time availability checking: fetches the resource's slots for the
// selected date and shows a simple hint so users see conflicts before
// they submit (server still re-validates on submit as the source of truth).
document.addEventListener("DOMContentLoaded", function () {
  const resourceSelect = document.getElementById("resourceSelect");
  const dateInput = document.getElementById("bookingDate");
  const hint = document.getElementById("availabilityHint");
  const startInput = document.getElementById("startTimeInput");
  const endInput = document.getElementById("endTimeInput");

  if (!resourceSelect) return;

  async function refreshAvailability() {
    const resourceId = resourceSelect.value;
    const day = dateInput.value;
    if (!resourceId || !day) {
      hint.textContent = "";
      return;
    }
    hint.textContent = "Checking availability...";
    try {
      const res = await fetch(`/resources/${resourceId}/availability?day=${day}`);
      const slots = await res.json();
      const freeCount = slots.filter(s => s.available).length;
      if (slots.length === 0) {
        hint.textContent = "No slot data available.";
        return;
      }
      hint.innerHTML = `<span style="color:#0F6E5D;"><i class="bi bi-check-circle"></i> ${freeCount} of ${slots.length} slots free that day.</span>`;
    } catch (e) {
      hint.textContent = "";
    }
  }

  resourceSelect.addEventListener("change", refreshAvailability);
  dateInput.addEventListener("change", function () {
    // Prefill start/end datetime-local inputs with the chosen date.
    if (dateInput.value) {
      startInput.value = `${dateInput.value}T09:00`;
      endInput.value = `${dateInput.value}T10:00`;
    }
    refreshAvailability();
  });
});

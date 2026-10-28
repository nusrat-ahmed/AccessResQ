let map;
let markers = [];

const $ = (id) => document.getElementById(id);
const statusLabels = {needed: "Needed", in_progress: "In progress", delivered: "Delivered", closed: "Closed"};
const categoryLabels = {water:"Water", food:"Food", shelter:"Shelter", medical:"Medical", accessibility:"Accessibility", hazard:"Hazard", other:"Other"};

function initMap() {
  map = L.map("map", {scrollWheelZoom: false}).setView([4.7110, -74.0721], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map);
}

function markerColor(report) {
  if (report.verification === "sample") return "#52718b";
  if (report.status === "delivered") return "#18745d";
  if (report.status === "in_progress") return "#b87521";
  return "#bf4c4b";
}

function addMarkers(reports) {
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  reports.forEach(r => {
    const color = markerColor(r);
    const icon = L.divIcon({
      className: "custom-marker",
      html: `<div style="width:17px;height:17px;border-radius:50%;background:${color};border:3px solid white;box-shadow:0 1px 8px #18372e55"></div>`,
      iconSize: [17,17], iconAnchor: [8,8]
    });
    const marker = L.marker([r.lat, r.lng], {icon}).addTo(map);
    const gap = Math.max(0, Number(r.quantity_needed) - Number(r.quantity_delivered));
    marker.bindPopup(`<div style="font-family:Arial;min-width:190px"><strong>${escapeHtml(r.title)}</strong><p style="margin:6px 0;font-size:12px">${escapeHtml(r.area)} · ${categoryLabels[r.category] || "Other"}</p><p style="margin:6px 0;font-size:12px">Status: <b>${statusLabels[r.status] || r.status}</b><br>Verification: <b>${r.verification === "sample" ? "Demo data" : r.verification}</b><br>Reported unmet quantity: <b>${gap}</b></p><small>${escapeHtml(r.description)}</small></div>`);
    markers.push(marker);
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function renderTable(reports) {
  const body = $("reports-body");
  if (!reports.length) {
    body.innerHTML = '<tr><td colspan="5">No reports yet. Submit the first report using the form.</td></tr>';
    return;
  }
  body.innerHTML = reports.map(r => {
    const gap = Math.max(0, Number(r.quantity_needed) - Number(r.quantity_delivered));
    const demo = r.verification === "sample";
    return `<tr>
      <td>${escapeHtml(r.title)}<span class="subtext">${demo ? "DEMO DATA · " : ""}${escapeHtml(r.description)}</span></td>
      <td>${escapeHtml(r.area)}<span class="subtext">${categoryLabels[r.category] || "Other"}</span></td>
      <td><span class="status status-${r.status}">${statusLabels[r.status] || r.status}</span>
        <div class="review-controls"><select aria-label="New status" data-status-for="${r.id}">
          ${Object.entries(statusLabels).map(([value,label]) => `<option value="${value}" ${r.status===value?"selected":""}>${label}</option>`).join("")}
        </select><select aria-label="Verification status" data-verification-for="${r.id}">
          <option value="pending" ${r.verification==="pending"?"selected":""}>Pending</option>
          <option value="verified" ${r.verification==="verified"?"selected":""}>Verified</option>
          <option value="rejected" ${r.verification==="rejected"?"selected":""}>Rejected</option>
        </select><button class="review-save" data-save-report="${r.id}" type="button">Save</button></div>
      </td>
      <td><span class="verify verify-${r.verification}">${r.verification === "sample" ? "Demo data" : r.verification}</span></td>
      <td><strong>${gap}</strong><span class="subtext">reported units</span></td>
    </tr>`;
  }).join("");
}

async function loadData() {
  const [reportsRes, metricsRes] = await Promise.all([fetch("/api/reports"), fetch("/api/metrics")]);
  if (!reportsRes.ok || !metricsRes.ok) throw new Error("Could not load the dashboard. Please refresh.");
  const reports = await reportsRes.json();
  const metrics = await metricsRes.json();
  $("m-total").textContent = metrics.total_reports;
  $("m-pending").textContent = metrics.pending_verification;
  $("m-unmet").textContent = metrics.estimated_unmet_quantity_units.toLocaleString();
  $("m-verified").textContent = metrics.verified_reports;
  renderTable(reports);
  addMarkers(reports);
}

$("report-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  // Capture the form synchronously. event.currentTarget can be null after await.
  const reportForm = event.currentTarget;
  const button = reportForm.querySelector("button[type=submit]");
  const msg = $("form-message");

  button.disabled = true;
  button.textContent = "Submitting…";
  msg.textContent = "";
  msg.className = "form-message";

  const form = new FormData(reportForm);
  const payload = {
    title: form.get("title"),
    category: form.get("category"),
    area: form.get("area"),
    description: form.get("description"),
    lat: Number(form.get("lat")),
    lng: Number(form.get("lng")),
    quantity_needed: Number(form.get("quantity_needed") || 0),
    quantity_delivered: Number(form.get("quantity_delivered") || 0),
    people_affected: Number(form.get("people_affected") || 0),
    source: "Community report"
  };

  try {
    const response = await fetch("/api/reports", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail;
      const message = Array.isArray(detail)
        ? detail.map(item => item.msg).join("; ")
        : detail;
      throw new Error(message || "Could not submit report.");
    }

    reportForm.reset();
    $("lat").value = "4.711";
    $("lng").value = "-74.072";
    msg.textContent = "Report saved. It is marked pending and is not verified yet.";

    await loadData();
    map.setView([data.lat, data.lng], 13);
  } catch (error) {
    msg.textContent = error.message || "Could not submit report.";
    msg.classList.add("error");
  } finally {
    button.disabled = false;
    button.innerHTML = 'Submit report <span>↗</span>';
  }
});


$("reports-body").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-save-report]");
  if (!button) return;
  const id = button.dataset.saveReport;
  const token = $("admin-token").value.trim();
  const status = document.querySelector(`[data-status-for="${id}"]`).value;
  const verification = document.querySelector(`[data-verification-for="${id}"]`).value;
  const msg = $("admin-message");
  if (!token) {
    msg.textContent = "Enter the server-configured admin token first. Admin review may be disabled on this deployment.";
    msg.className = "form-message error";
    return;
  }
  button.disabled = true;
  button.textContent = "Saving…";
  try {
    const response = await fetch(`/api/reports/${id}/status`, {
      method: "PATCH",
      headers: {"Content-Type": "application/json", "X-Admin-Token": token},
      body: JSON.stringify({status, verification})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not update report.");
    msg.textContent = `Report #${id} review status updated.`;
    msg.className = "form-message";
    await loadData();
  } catch (error) {
    msg.textContent = error.message || "Could not update report.";
    msg.className = "form-message error";
  } finally {
    button.disabled = false;
    button.textContent = "Save";
  }
});

$("refresh-btn").addEventListener("click", async () => {
  try { await loadData(); } catch (e) { alert(e.message); }
});

initMap();
loadData().catch(err => {
  $("reports-body").innerHTML = `<tr><td colspan="5">${escapeHtml(err.message)}</td></tr>`;
});

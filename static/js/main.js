document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("predictForm");
  const resBox = document.getElementById("predictResult");

  if (!form || !resBox) return;

  // ================= PREDICT =================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const input = document.getElementById("symptoms").value;

    const symptoms = input
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    if (symptoms.length === 0) {
      resBox.innerHTML = `<div class="alert alert-warning">Enter valid symptoms</div>`;
      return;
    }

    resBox.innerHTML = `
      <div class="glass-card text-center p-4">
        <div class="spinner-border text-info"></div>
        <p class="mt-2">AI analyzing symptoms...</p>
      </div>
    `;

    try {
      const resp = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        resBox.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        return;
      }

      renderPrediction(data);
    } catch (err) {
      resBox.innerHTML = `<div class="alert alert-danger">Network error</div>`;
    }
  });

  // ================= RENDER =================
  function renderPrediction(data) {
    let html = `
      <div class="glass-card p-4 mt-3">
        <h5 class="text-success text-center">Prediction Result</h5>

        <div class="text-center mb-3">
          <span class="badge bg-success fs-5 px-3 py-2">
            ${data.predicted_disease}
          </span>
        </div>

        <h6>Top Possibilities:</h6>
        <ul>
    `;

    data.top3.forEach(([d, p]) => {
      html += `<li>${d} - ${p}%</li>`;
    });

    html += `</ul>`;

    if (data.medicines) {
      html += `
        <div class="alert alert-success">
          💊 Medicines: ${data.medicines}
        </div>`;
    }

    html += `
      <button id="hospitalBtn" class="btn btn-outline-info w-100 mt-2">
        📍 Find Nearby Hospitals
      </button>

      <div id="hospitalList" class="mt-3"></div>
    </div>
    `;

    resBox.innerHTML = html;
  }

  // ================= EVENT DELEGATION (FIXED CLICK ISSUE) =================
  document.addEventListener("click", (e) => {
    if (e.target && e.target.id === "hospitalBtn") {
      getHospitals();
    }
  });

  // ================= HOSPITAL FUNCTION =================
  function getHospitals() {
    const listBox = document.getElementById("hospitalList");

    if (!listBox) return;

    listBox.innerHTML = `
      <div class="text-info text-center">
        📍 Getting location...
      </div>
    `;

    if (!navigator.geolocation) {
      listBox.innerHTML = `<div class="alert alert-danger">Geolocation not supported</div>`;
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;

        listBox.innerHTML = `
          <div class="text-info text-center">
            🏥 Searching hospitals...
          </div>
        `;

        try {
          const res = await fetch(`/hospitals?lat=${lat}&lng=${lng}`);
          const data = await res.json();

          if (!res.ok || data.error) {
            listBox.innerHTML = `
              <div class="alert alert-danger">
                ${data.error || "Server error"}
              </div>`;
            return;
          }

          if (!Array.isArray(data) || data.length === 0) {
            listBox.innerHTML = `
              <div class="alert alert-warning">
                No hospitals found
              </div>`;
            return;
          }

          let html = `<h6 class="text-info">Nearby Hospitals</h6>`;

          data.forEach((h) => {
            html += `
              <div class="border p-2 mb-2 rounded">
                <b>🏥 ${h.name}</b><br>
                <small>${h.address}</small><br>
                ⭐ ${h.rating ?? "N/A"}
              </div>
            `;
          });

          listBox.innerHTML = html;
        } catch (err) {
          console.error(err);
          listBox.innerHTML = `
            <div class="alert alert-danger">
              API error / server not responding
            </div>`;
        }
      },
      (err) => {
        console.error(err);
        listBox.innerHTML = `
          <div class="alert alert-warning">
            Location permission denied or timeout
          </div>`;
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  }
});

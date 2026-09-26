let qualityTrendChart = null;
let checkResultsChart = null;

function getJsonData(id, fallback) {
  const element = document.getElementById(id);

  if (!element) {
    return fallback;
  }

  try {
    return JSON.parse(element.textContent);
  } catch (error) {
    console.error("Dashboard data parsing failed:", error);
    return fallback;
  }
}

function renderQualityTrendChart(runs) {
  const canvas = document.getElementById("qualityTrendChart");

  if (!canvas) {
    console.error("Quality trend canvas not found.");
    return;
  }

  if (typeof Chart === "undefined") {
    console.error("Chart.js is not loaded.");
    return;
  }

  if (!Array.isArray(runs)) {
    console.error("Quality trend data is not an array.");
    return;
  }

  const validRuns = runs
    .filter(run => run.quality_score !== null)
    .reverse();

  if (!validRuns.length) {
    console.warn("No quality score data available for chart.");
    return;
  }

  if (qualityTrendChart) {
    qualityTrendChart.destroy();
  }

  qualityTrendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: validRuns.map(run => run.date),
      datasets: [
        {
          label: "Quality Score",
          data: validRuns.map(run => run.quality_score),
          tension: 0.35,
          fill: false,
          borderWidth: 3,
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index"
      },
      scales: {
        x: {
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: value => value + "%"
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: context => "Quality: " + context.parsed.y + "%"
          }
        }
      }
    }
  });
}

function renderCheckResultsChart(passed, failed) {
  const canvas = document.getElementById("checkResultsChart");

  if (!canvas) {
    console.error("Check results canvas not found.");
    return;
  }

  if (typeof Chart === "undefined") {
    console.error("Chart.js is not loaded.");
    return;
  }

  if (checkResultsChart) {
    checkResultsChart.destroy();
  }

  checkResultsChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Passed", "Failed"],
      datasets: [
        {
          data: [passed, failed],
          borderWidth: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const qualityTrendData = getJsonData("quality-trend-data", []);
  const passedChecks = Number(getJsonData("passed-checks-data", 0));
  const failedChecks = Number(getJsonData("failed-checks-data", 0));

  renderQualityTrendChart(qualityTrendData);
  renderCheckResultsChart(passedChecks, failedChecks);
});

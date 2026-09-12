const chartElement = document.getElementById("annual-score-chart");
const colors = ["#6ea8fe", "#75b798", "#ffda6a", "#ea868f", "#a98eda", "#79dfc1"];

const response = await fetch(chartElement.dataset.apiUrl, { credentials: "same-origin" });
if (!response.ok) {
  throw new Error(`Unable to load score history (${response.status})`);
}
const chartData = await response.json();

const table = document.getElementById("annual-score-table");
const tableBody = table.querySelector("tbody");
const rowTemplate = document.getElementById("annual-score-row-template");
const headerRow = document.createElement("tr");
const personHeader = document.createElement("th");
personHeader.scope = "col";
personHeader.textContent = "Person";
headerRow.appendChild(personHeader);
chartData.labels.forEach((label) => {
  const header = document.createElement("th");
  header.scope = "col";
  header.textContent = label;
  headerRow.appendChild(header);
});
table.querySelector("thead").appendChild(headerRow);

chartData.datasets.forEach((dataset) => {
  const row = document.importNode(rowTemplate.content, true).firstElementChild;
  row.querySelector("[data-person]").textContent = dataset.label;
  dataset.data.forEach((score) => {
    const cell = document.createElement("td");
    cell.textContent = score;
    row.appendChild(cell);
  });
  tableBody.appendChild(row);
});

if (chartData.datasets.length === 0) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = chartData.labels.length + 1;
  cell.textContent = "No score history available.";
  row.appendChild(cell);
  tableBody.appendChild(row);
}

new Chart(chartElement, {
  type: "line",
  data: {
    labels: chartData.labels,
    datasets: chartData.datasets.map((dataset, index) => ({
      ...dataset,
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length],
      tension: 0.2,
    })),
  },
  options: {
    maintainAspectRatio: false,
    scales: {
      y: { beginAtZero: true, ticks: { precision: 0 } },
    },
  },
});

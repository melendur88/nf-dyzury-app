const meta = document.querySelector("#meta");
const results = document.querySelector("#results");

fetch("report.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error("Brak raportu");
    return response.json();
  })
  .then((report) => {
    const updated = new Date(report.updatedAt).toLocaleString("pl-PL", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/Warsaw",
    });
    meta.textContent = `Okres: ${report.period}. Ostatnie odświeżenie: ${updated}.`;
    results.replaceChildren(...report.results.map((result) => {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${result.username}</td><td>${result.weekdays.join(", ")}</td><td>${result.commented}/${result.eligible} (${result.percentage.toFixed(1)}%)</td><td><strong class="${result.passed ? "pass" : "fail"}">${result.passed ? "TAK" : "NIE"}</strong></td>`;
      return row;
    }));
  })
  .catch(() => {
    meta.textContent = "Raport nie jest jeszcze dostępny. Spróbuj ponownie za chwilę.";
  });

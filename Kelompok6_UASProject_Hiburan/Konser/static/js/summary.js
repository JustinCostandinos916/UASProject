
document.addEventListener('DOMContentLoaded', function () {
  const fieldsets = document.querySelectorAll('.ticket-option');
  const kategoriList = Array.from(fieldsets).map(fs => fs.dataset.field);

  kategoriList.forEach(function(fieldName) {
    const el = document.getElementById(fieldName);
    if (el) {
      el.addEventListener('change', function () {
        updateSummary(kategoriList);
      });
    }
  });

  updateSummary(kategoriList);
});

function updateSummary(kategoriList) {
  let totalTiket = 0;
  let totalHarga = 0;

  kategoriList.forEach(function(fieldName) {
    const select = document.getElementById(fieldName);
    const jumlah = parseInt(select?.value || "0");
    const harga = parseInt(select?.dataset.harga || "0");

    totalTiket += jumlah;
    totalHarga += jumlah * harga;
  });

  const ticketCountEl = document.getElementById("ticketCount");
  const subtotalEl = document.getElementById("subtotal");

  if (ticketCountEl) ticketCountEl.textContent = totalTiket;
  if (subtotalEl) subtotalEl.textContent = totalHarga.toLocaleString('id-ID');
}
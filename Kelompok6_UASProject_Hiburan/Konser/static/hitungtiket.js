const selects = document.querySelectorAll(".kategori");
const totalharga = document.getElementById("subtotal");
const jumlahtiket = document.getElementById("ticketCount");
const totalhargainput = document.getElementById("totalHargaInput");
const totalhargatiket = document.getElementById("totalTiketInput");
let hargaPerKategori = {};

selects.forEach((tiket) => {
  tiket.addEventListener("change", totalTiket);
});

selects.forEach((hrg) => {
  hrg.addEventListener("change", () => {
    const harga = Number(hrg.dataset.harga);
    const kuanti = Number(hrg.value);
    const id = hrg.id;
    hargaPerKategori[id] = harga * kuanti;
    console.log(hargaPerKategori);
  });
});

selects.forEach((price) => {
  price.addEventListener("change", totalHarga);
});

function totalTiket() {
  let sum = 0;
  selects.forEach((tiket) => {
    const val = tiket.value;
    if (val) {
      sum += parseInt(val);
    }
  });
  jumlahtiket.textContent = sum;
  totalhargatiket.value = sum;
}

let hargaperkategori = [];
function totalHarga() {
  let sum = 0;
  selects.forEach((price) => {
    const kuanti = parseInt(price.value);
    const harga = parseInt(price.dataset.harga);
    sum += kuanti * harga;
  });
  totalharga.textContent = sum.toLocaleString();
  totalhargainput.value = sum;
}

document.getElementById("cat1harga").innerText = `Rp. ${hargaPerKategori.cat1.toLocaleString("id-ID")}`;

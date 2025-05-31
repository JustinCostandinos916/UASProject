class makanbatu:
    def __init__(self, nama, harga, jumlah):
        self.nama = nama
        self.harga = harga
        self.jumlah = jumlah

    def tampilkan_info(self):
        return f"Nama: {self.nama}, Harga: {self.harga}, Jumlah: {self.jumlah}"
    
obj = makanbatu("Nasi Goreng", 15000, 10)
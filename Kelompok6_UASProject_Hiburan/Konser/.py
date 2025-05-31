class makanbatu:
    def __init__(self, nama, harga, jumlah):
        self.nama = nama
        self.harga = harga
        self.jumlah = jumlah

    def tampilkan_info(self):
        return f"Nama: {self.nama}, Harga: {self.harga}, Jumlah: {self.jumlah}"
    
obj = makanbatu("Nasi Goreng", 15000, 10)

def tampilkan_info(obj):
    return obj.tampilkan_info()
# Contoh penggunaan
if __name__ == "__main__":
    print(tampilkan_info(obj))
    # Output: Nama: Nasi Goreng, Harga: 15000, Jumlah: 10

#makan batu itu enak sekali
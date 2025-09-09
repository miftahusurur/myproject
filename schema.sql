-- Hapus tabel lama jika ada
DROP TABLE IF EXISTS transaksi;
DROP TABLE IF EXISTS pelanggan;
DROP TABLE IF EXISTS gas;
DROP TABLE IF EXISTS users;

-- Tabel Pengguna (users)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    is_admin TINYINT(1) DEFAULT 0
);

-- Tabel Gas
CREATE TABLE gas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    jenis_gas VARCHAR(255) NOT NULL UNIQUE,
    harga DECIMAL(10,2) NOT NULL,
    stok INT NOT NULL,
    tanggal_masuk DATE NOT NULL
    gambar VARCHAR(255) NULL;
);

-- Tabel Pelanggan
CREATE TABLE pelanggan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(255) NOT NULL,
    telepon VARCHAR(50),
    alamat TEXT
);

-- Tabel Transaksi
CREATE TABLE transaksi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_pelanggan VARCHAR(255) NOT NULL,
    gas_id INT NOT NULL,
    jumlah_jual INT NOT NULL,
    harga_satuan DECIMAL(10,2) NOT NULL,
    total_harga DECIMAL(10,2) NOT NULL,
    tanggal_transaksi DATE NOT NULL,
    FOREIGN KEY (gas_id) REFERENCES gas(id)
);

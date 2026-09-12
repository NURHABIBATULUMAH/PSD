# Eksplorasi Data: Integrasi Data menggunakan Aiven Cloud PostgreSQL, pgAdmin, dan Knime

Pada tugas ini memuat dokumentasi panduan langkah untuk manajemen analisis data kualitas udara di Kabupaten Tuban (khususnya wilayah Kerek).

## 1. Pembuatan Akun dan Layanan PostgreSQL di Aiven

Langkah awal untuk menyediakan server database berbasis cloud yang dapat diakses dari mana saja.

1. Buka situs Aiven Console lalu buat akun baru atau masuk (login) menggunakan kredensial Anda

2. Pada halaman beranda konsol, klik tombol Create service

3. Pilih layanan database PostgreSQL

4. Pilih penyedia cloud (misalnya DigitalOcean, AWS, atau Google Cloud) serta pilih region server yang terdekat

5. Pilih paket layanan (bisa menggunakan paket Free tier atau Startup yang tersedia)

6. Beri nama layanan, lalu klik Create service

7. Tunggu beberapa saat hingga status layanan berubah menjadi Running

## 2. Pengambilan Kredensial dan Sertifikat SSL Aiven

Sebelum menghubungkan database ke pgAdmin, Anda memerlukan informasi koneksi serta sertifikat keamanan.

1. Masuk ke halaman Overview dari layanan PostgreSQL yang baru saja Anda buat di Aiven

2. Cari bagian Connection information:

Simpan semua informasi ini untuk mengkoneksikan ke pgadmin

![Foto Saya](../img/overview.png)

## 3. Menghubungkan Aiven PostgreSQL ke pgAdmin 

Menghubungkan aplikasi manajemen basis data lokal (pgAdmin) ke server cloud Aiven

1. Buka aplikasi pgAdmin

2. Klik kanan pada folder Servers di panel kiri, pilih Create > Server...

3. Pada tab General, isi nama server (misal: Aiven Postgres)

Berikut tampilan ketika sudah berhasil terkoneksi dengan server aiven

![Foto Saya](../img/aiven.png)

## 4. Import File CSV Kualitas Udara Ke PostgreSQL

1. Di panel kiri pgAdmin, arahkan ke database Anda > Schemas > public > Tables

2. Klik kanan pada tabel kualitas_udara, lalu pilih Import/Export Data...

3. Pada tab General:

- Atur toggle Import/Export menjadi Import

- Pilih file `KualitasUdaraKerek.csv` pada bagian Filename

- Atur Format ke csv dan pastikan Header diatur ke Yes

Berikut tampilan ketika data sudah berhasil di import ke pgAdmin:

![Foto Saya](../img/data-kerek.png)

## 5. Integrasi Data Menggunakan Knime

Menghubungkan data dari Aiven PostgreSQL ke KNIME Analytics Platform untuk pengolahan lebih lanjut. Konfigurasikan Host, Port, Database name, User, dan Password yang disesuaikan dengan kredensial Aiven.

Berikut nodes - nodes yang digunakan:

![Foto Saya](../img/knime_polusi.png)

## 6. Penjelasan, Rumus, dan Contoh Perhitungan dari Seluruh Fitur pada Nodes *Statistik*

Pada implementasi knime, kolom yang digunakan adalah **CO** dan **O3**, berikut hasil dari statistiknya

![Foto Saya](../img/kerek1.png)


![Foto Saya](../img/kerek2.png)

### 1. Column
Pada fitur **Column** berisi nama kolom yaitu sebagai polutan apa saja yang ada pada data, pada data tersebut terdapat **CO** dan **O3**.

### 2. Min
Pada fitur min berisi nilai minimal dari data pada setiap kolom, untuk nilai min dari pada **CO** dan **O3** sebagai berikut:

- **CO** = 0.0216

- **O3** = 0.1095

### 3. Max
Pada fitur max berisi nilai maximal dari data pada setiap kolom, untuk nilai max dari pada **CO** dan **O3** sebagai berikut:

- **CO** = 0.0427

- **O3** = 0.1234

### 4. Mean
Pada fitur mean berisi nilai rata-rata keseluruhan dari data valid, dihitung dengan menjumlahkan seluruh nilai data lalu dibagi dengan jumlah data valid ($n$).

**Rumus Mean:**

$$\bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i$$

**Contoh perhitungan:**

$$\bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i = \frac{x_1 + x_2 + x_3 + x_4 + \dots + x_{251}}{251}$$

$$\bar{x} = \frac{0.027419 + 0.026418 + 0.025624 + \dots + x_{251}}{251}$$

Sehingga pada kolom **CO** dan **O3** diperoleh mean:

- **CO** = 0.0300
- **O3** = 0.1158

### 5. Standard Deviasi 
Standard Deviasi digunakan untuk mengetahui seberapa jauh sebaran angka - angka di dalam dataset dari nilai rata - rata. Jika nilai standard deviasi kecil artinya data-data berkumpul rapat disekitar nilai rata-rata, tetapi jika nilai standard deviasi besar artinya data menyebar sangat luas dan jauh dari rata - rata.

**Rumus Standard Deviasi:**

Berikut adalah rumus **standard deviasi sample:**

$$s = \sqrt{\frac{\sum_{i=1}^{n} (x_i - \bar{x})^2}{n - 1}}$$

Keterangan:

$s$ = Standar deviasi sampel

$x_i$ = Nilai data ke-$i$

$\bar{x}$ = Nilai rata-rata (mean)

$n$ = Jumlah total data valid (count)

Berikut adalah rumus **standard deviasi populasi:**

$$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}$$

Keterangan:

$\sigma$ = Standar deviasi populasi

$x_i$ = Nilai data ke-$i$

$\mu$ = Nilai rata-rata populasi (population mean)

$N$ = Jumlah total keseluruhan data populasi

**Contoh perhitungan:**

Pada perhitungan ini dicontohkan untuk standard deviasi populasi, karena pada kolom **CO** terdapat missing value sebanyak 115, maka untuk $N$ pembagi menjadi $366 - 115 = 251$

$$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}$$

$$\sigma = \sqrt{\frac{1}{251} \sum_{i=1}^{251} (x_i - \mu)^2}$$

$$\sigma = \sqrt{\frac{0.003329}{251}} = \sqrt{0.00001327} = \mathbf{0.0036427} \approx \mathbf{0.00364}$$

Sehingga pada kolom **CO** dan **O3** diperoleh standard deviasi:

- **CO** = 0.0036500 (sampel) / 0.0036427 (populasi)

- **O3** = 0.0025488 (sampel) / 0.0025453 (populasi)

### 6. Variansi
Pada fitur variansi ini merupakan ukuran penyebaran statistik yang mengukur seberapa jauh setiap angka dalam kumpulan data tersebar dari nilai rata-ratanya. Hubungannya dengan **standard deviasi** adalah variansi merupakan kuadrat dari standard deviasi ($\text{Varians} = s^2$ atau $\sigma^2$).

**Rumus variansi:**

$$s^2 = \frac{1}{n - 1} \sum_{i=1}^{n} (x_i - \bar{x})^2$$

$$\sigma^2 = \frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2$$

**Contoh Perhitungan:**

Untuk perhitungan pada variansi cukup dengan mengkuadratkan standard deviasi, yaitu sebagai berikut untuk contoh perhitungan variansi populasi pada **CO**:

$$\text{Varians} = \sigma^2 = 0.0036427^2 \approx 1.33E-05$$

Sehingga pada kolom **CO** dan **O3** diperoleh variansi:

- **CO** = 1.33E-05

- **O3** = 6.48E-06

### 7. Skewness
Skewness merupakan bentuk penyebaran data apakah simetris atau tidak simetris (miring) terhadap nilai rata - ratanya.

- Skewness Positif (Right Skewed) : Nilainya > 0
- Skewness Negatif (Left Skewed) : Nilainya < 0
- Simetris : Nilainya mendekati 0

**Rumus skewness:**

$$\text{Skewness} = \frac{n}{(n - 1)(n - 2)} \sum_{i=1}^{n} \left( \frac{x_i - \bar{x}}{s} \right)^3$$

Sehingga pada kolom **CO** dan **O3** diperoleh skewness:

- **CO** = 0.450
- **O3** = 0.425

### 8. Kurtosis
Kurtosis adalah ukuran statistik yang mendeskripsikan seberapa runcing atau landai puncak suatu distribusi data dibandingkan dengan distribusi normal standar.

**Rumus Kurtosis:**

$$\text{Kurtosis} = \left[ \frac{n(n+1)}{(n-1)(n-2)(n-3)} \sum_{i=1}^{n} \left( \frac{x_i - \bar{x}}{s} \right)^4 \right] - \frac{3(n-1)^2}{(n-2)(n-3)}$$

Sehingga pada kolom **CO** dan **O3** diperoleh excess kurtosis:

- **CO** = 0.274

- **O3** = -0.173

### 9. Overall Sum
Overall sum adalah jumlah total keseluruhan dari seluruh nilai data valid yang terdapat pada suatu kolom atau fitur tertentu.

**Rumus Overall Sum:**

$$\text{Overall Sum} = \sum_{i=1}^{n} x_i = x_1 + x_2 + x_3 + \dots + x_n$$

Sehingga pada kolom **CO** dan **O3** diperoleh overall sum:

- **CO** = 7.532

- **O3** = 41.684

### 10. No Missing Value
Jumlah baris data yang kosong, tidak tercatat, atau bernilai null pada suatu kolom.

**Rumus:**
$$\text{Missing Values} = N_{\text{total}} - n$$

Sehingga pada kolom **CO** dan **O3** diperoleh jumlah missing values:

- **CO** = 115

- **O3** = 6

### 11. No Nans
Jumlah baris data yang bernilai Not a Number (NaN).

Sehingga pada kolom **CO** dan **O3** diperoleh jumlah NaNs:

- **CO** = 0

- **O3** = 0

### 12. No. +∞s (Positive Infinity)
Jumlah baris data yang bernilai tak terhingga positif ($+\infty$).

Sehingga pada kolom **CO** dan **O3** diperoleh jumlah +∞s:

- **CO** = 0

- **O3** = 0

### 13. No. -∞s (Negative Infinity)
Jumlah baris data yang bernilai tak terhingga negatif ($-\infty$).

Sehingga pada kolom **CO** dan **O3** diperoleh jumlah -∞s:

- **CO** = 0

- **O3** = 0

### 14. Median
Nilai tengah dari sekumpulan data valid yang telah diurutkan dari terkecil hingga terbesar.

Sehingga pada kolom **CO** dan **O3** diperoleh nilai median:

- **CO** = 0.0297

- **O3** = 0.1155

### 15. Row Count
Jumlah total baris yang terdapat di dalam suatu kolom (data valid ditambah missing values).

$$\text{Row Count} = N_{\text{total}} = n + \text{Missing Values}$$

Sehingga pada kolom **CO** dan **O3** diperoleh total row count:

- **CO** = 366

- **O3** = 366
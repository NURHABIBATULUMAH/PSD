# Ringkasan Fitur TSFEL dan Rumus Matematika

## 1. Domain Statistical
Domain ini mengekstrak metrik kuantitatif, karakteristik sebaran, dan bentuk distribusi dari sinyal deret waktu tanpa mempertimbangkan urutan kemunculan waktunya.

* **Ukuran Pemusat & Ekstrem:**
  * `calc_max`, `calc_min`, `calc_mean`, `calc_median`: Nilai maksimum, minimum, rata-rata dan median dari data deret waktu.
  
  $$\mu = \frac{1}{N}\sum_{i=1}^{N}x_i$$ 
  
* **Penyebaran Data:**
  * `calc_std`, `calc_var`: 
  
  Standar deviasi 
  
  $$\sigma = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^2}$$
  
  varians 
  
  $$\sigma^2 = \frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^2$$

* **Distribusi Kumulatif (ECDF):**
  * `ecdf`, `ecdf_percentile`, `ecdf_percentile_count`, `ecdf_slope`: Berdasarkan Empirical Cumulative Distribution Function 
  
  $$F_N(x) = \frac{1}{N}\sum_{i=1}^{N} I(x_i \le x)$$

* **Bentuk & Karakteristik Sebaran:**
  * `hist_mode`: Nilai kemunculan terbanyak (modus) dalam histogram data.
  * `interq_range`: Interquartile Range ($IQR = Q_3 - Q_1$).
  * `kurtosis`: Tingkat kelancipan distribusi data dibandingkan distribusi normal:

    $$\text{Kurtosis} = \frac{\frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^4}{\sigma^4}$$

  * `skewness`: Ukuran ketidaksimetrisan (kemiringan) distribusi data:

    $$\text{Skewness} = \frac{\frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^3}{\sigma^3}$$

* **Deviasi & Energi:**
  * `mean_abs_deviation`: Rata-rata deviasi absolut:

    $$\text{MAD} = \frac{1}{N}\sum_{i=1}^{N}\vert{}x_i - \mu\vert{}$$

  * `median_abs_deviation`: Median dari deviasi absolut terhadap median data.
  * `rms`: Root Mean Square:

    $$\text{RMS} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}x_i^2}$$

---

## 2. Domain Temporal
Domain temporal mengevaluasi sinyal berdasarkan urutan waktunya untuk menemukan tren, siklus, autokorelasi, dan kompleksitas.

* **Energi & Area:**
  * `abs_energy`: Total energi absolut:

    $$\text{Energy} = \sum_{i=1}^{N}x_i^2$$

  * `auc`: Area Under the Curve (aturan trapesium):

    $$\text{AUC} = \sum_{i=1}^{N-1} \frac{x_i + x_{i+1}}{2} \Delta t$$

  * `average_power`: Rata-rata kekuatan sinyal dalam domain waktu 
  
    $$\frac{1}{N}\sum x_i^2$$

* **Dinamika & Fluktuasi:**
  * `autocorr`: Autokorelasi pada lag $k$:

    $$R(k) = \frac{\sum_{i=1}^{N-k}(x_i - \mu)(x_{i+k} - \mu)}{\sum_{i=1}^{N}(x_i - \mu)^2}$$

  * `calc_centroid`: Titik pusat massa sinyal di sepanjang sumbu waktu.
  * `dfa`: Detrended Fluctuation Analysis, mengukur dependensi jangka panjang atau fraktalitas sinyal.
  * `distance`: Total jarak lintasan pergerakan titik data:

    $$\text{Distance} = \sum_{i=1}^{N-1} \sqrt{(t_{i+1} - t_i)^2 + (x_{i+1} - x_i)^2}$$

* **Kompleksitas & Fraktal:**
  * `entropy`: Shannon Entropy dari probabilitas distribusi nilai sinyal.
  * `higuchi_fractal_dimension`, `petrosian_fractal_dimension`: Dimensi fraktal untuk menilai tingkat kekasaran/kegerigian matematis sinyal.
  * `hurst_exponent`: Mengevaluasi memori tren jangka panjang dalam deret waktu.
  * `lempel_ziv`: Tingkat kompresibilitas atau kekayaan pola biner pada sinyal.
* **Perubahan & Kesalahan (Diff & MSE):**
  * `mean_abs_diff`: Rata-rata selisih absolut antar-data berurutan 
  
    $$\Delta x_i = x_{i+1} - x_i$$

    $$\text{Mean Abs Diff} = \frac{1}{N-1}\sum_{i=1}^{N-1}\vert{}x_{i+1} - x_i\vert{}$$

  * `mse`: Mean Squared Error:

    $$\text{MSE} = \frac{1}{N}\sum_{i=1}^{N}(x_i - \mu)^2$$

  * `slope`: Kemiringan tren data linear secara keseluruhan 
  
    $$x_t = m \cdot t + c$$

* **Titik Belok & Puncak:**
  * `negative_turning`, `positive_turning`: Jumlah titik belok perubahan arah tren.
  * `pk_pk_distance`: Jarak vertikal Peak-to-Peak.
  * `zero_cross`: Frekuensi pemotongan garis nol (*baseline*).

---

## 3. Domain Spectral
Domain spektral mentransformasikan deret waktu ke ranah frekuensi menggunakan Fast Fourier Transform (FFT) atau dekomposisi wavelet.

* **Frekuensi & Daya Dominan:**
  * `fundamental_frequency`: Frekuensi dengan magnitudo tertinggi:

    $$f_{\text{fund}} = \arg\max_f \vert{}X(f)\vert{}$$

  * `max_power_spectrum`: Nilai daya tertinggi pada spektrum frekuensi 
  
    $$\max \vert{}X(f)\vert{}^2$$

  * `power_bandwidth`: Lebar pita frekuensi tempat sebagian besar energi sinyal terkonsentrasi.

* **Karakteristik & Statistik Spektral:**
  * `spectral_centroid`: Titik pusat massa spektrum frekuensi:

    $$\text{Centroid} = \frac{\sum f \cdot \vert{}X(f)\vert{}}{\sum \vert{}X(f)\vert{}}$$

  * `spectral_entropy`: Entropi spektral mengukur kerataan distribusi daya.
  * `spectral_kurtosis`, `spectral_skewness`: Parameter bentuk kelancipan dan kemiringan kurva densitas spektrum.
  * `spectral_roll_off`: Titik frekuensi konsentrasi daya (misal 95%):

    $$\sum_{f=0}^{f_{\text{rolloff}}} \vert{}X(f)\vert{}^2 = 0.95 \sum_{f=0}^{max} \vert{}X(f)\vert{}^2$$

* **Transformasi Wavelet:**
  * `wavelet_energy`, `wavelet_entropy`, `wavelet_std`: Parameter statistik dari koefisien Transformasi Wavelet Diskrit (CWT/DWT).

Berikut adalah contoh perhitungan manual untuk fitur **Wavelet Entropy** (`wavelet_entropy`) menggunakan pendekatan Shannon Entropy berbasis energi koefisien wavelet pada berbagai level dekomposisi.

---

### Langkah-Langkah Penghitungan Manual Wavelet Entropy

#### 1. Dekomposisi Sinyal Menggunakan Wavelet
Misalkan kita memiliki sinyal deret waktu kecil yang telah didekomposisi menjadi 3 level koefisien (misal melalui *Discrete Wavelet Transform*), menghasilkan energi pada masing-level skala ($j = 1, 2, 3$):
* Energi level 1 ($E_1$) = $10$
* Energi level 2 ($E_2$) = $30$
* Energi level 3 ($E_3$) = $60$

*(Catatan: Energi tiap level dihitung dari jumlah kuadrat koefisien wavelet pada level tersebut: $E_j = \sum \vert{}c_{j,k}\vert{}^2$)*

#### 2. Menghitung Total Energi Keseluruhan ($E_{tot}$)
Jumlahkan seluruh energi dari setiap level dekomposisi:
$$E_{tot} = \sum_{j} E_j = 10 + 30 + 60 = 100$$

#### 3. Menghitung Probabilitas Relatif Tiap Level ($p_j$)
Bagi energi di setiap level dengan total energi keseluruhan untuk mendapatkan distribusi probabilitas relatif ($p_j = \frac{E_j}{E_{tot}}$):
* $p_1 = \frac{10}{100} = 0.10$
* $p_2 = \frac{30}{100} = 0.30$
* $p_3 = \frac{60}{100} = 0.60$

*(Pastikan total probabilitas $\sum p_j = 0.10 + 0.30 + 0.60 = 1.0$)*

#### 4. Menghitung Nilai Wavelet Entropy ($H_{WE}$)
Gunakan rumus Shannon Entropy berdasarkan probabilitas energi wavelet:

$$H_{WE} = - \sum_{j} p_j \log_2(p_j)$$

Masukkan nilai probabilitas yang sudah dihitung (menggunakan log berbasis 2):
* Untuk level 1: $- (0.10 \times \log_2(0.10)) = - (0.10 \times -3.3219) = 0.3322$
* Untuk level 2: $- (0.30 \times \log_2(0.30)) = - (0.30 \times -1.7370) = 0.5211$
* Untuk level 3: $- (0.60 \times \log_2(0.60)) = - (0.60 \times -0.7370) = 0.4422$

#### 5. Hasil Akhir
Jumlahkan seluruh hasil komponen di atas:

$$H_{WE} = 0.3322 + 0.5211 + 0.4422 = 1.2955\text{ bits}$$

Nilai **1.2955** inilah yang merepresentasikan tingkat kompleksitas atau ketidakteraturan distribusi energi sinyal pada domain waktu-frekuensi melalui *Wavelet Entropy*.
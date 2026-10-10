import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Sistem Informasi Geografis LULC Jatim", layout="wide")
st.title("Sistem Informasi Geografis: Analisis Spasial Penggunaan Lahan")
st.markdown("**Studi Kasus: Klasifikasi Tutupan Lahan (LULC) Provinsi Jawa Timur Menggunakan Citra Sentinel-2A**")
st.write("---")

# Membuat dua tab terpisah untuk Peta dan Laporan Statis
tab1, tab2 = st.tabs(["Peta Interaktif (Deployment)", "Deskriptif"])

# ==============================================================================
# TAB 1: PETA INTERAKTIF (Sama seperti kode Anda sebelumnya)
# ==============================================================================
with tab1:
    st.subheader("Peta Interaktif Sebaran Tutupan Lahan")
    
    @st.cache_data
    def load_data():
        return pd.read_csv("dataset_uts_klasifikasi.csv")

    df = load_data()

    # Sidebar Filter
    st.sidebar.header("Filter Data")
    daftar_kelas = df['Kelas'].unique().tolist()
    kelas_terpilih = st.sidebar.multiselect(
        "Pilih Kelas Tutupan Lahan:",
        options=daftar_kelas,
        default=daftar_kelas
    )
    df_filtered = df[df['Kelas'].isin(kelas_terpilih)]

    # Sidebar Statistik
    st.sidebar.write("---")
    st.sidebar.header("Informasi Dataset")
    st.sidebar.write(f"**Total Titik Ditampilkan:** {len(df_filtered)}")
    if not df_filtered.empty:
        st.sidebar.dataframe(df_filtered['Kelas'].value_counts())

    warna_kelas = {
        "Sawah": "lightgreen", "Bangunan": "red", "Lahan Hijau": "green",
        "Mangrove": "darkgreen", "Ranu": "lightblue", "Perairan Laut": "blue"
    }

    # Inisialisasi Peta
    peta_jatim = folium.Map(location=[-7.25, 112.75], zoom_start=8)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        overlay=False,
        control=True
    ).add_to(peta_jatim)

    # Marker
    for idx, row in df_filtered.iterrows():
        kelas_aktual = row['Kelas']
        popup_html = f"""
        <b>Koordinat:</b> {row['Latitude']:.4f}, {row['Longitude']:.4f}<br>
        <b>Klasifikasi:</b> {kelas_aktual}<br>
        <b>NDVI:</b> {row['NDVI']:.2f}<br>
        <b>NDWI:</b> {row['NDWI']:.2f}
        """
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=7,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=kelas_aktual,
            color=warna_kelas.get(kelas_aktual, 'gray'),
            fill=True,
            fill_opacity=0.9
        ).add_to(peta_jatim)

    folium.LayerControl().add_to(peta_jatim)

    if kelas_terpilih:
        st_data = st_folium(peta_jatim, width=1000, height=550)
    else:
        st.warning("Silakan pilih minimal satu kelas di panel sebelah kiri untuk menampilkan peta.")

# ==============================================================================
# TAB 2: LAPORAN ANALISIS WEB STATIS (Sesuai kerangka CRISP-DM)
# ==============================================================================
with tab2:
    st.markdown("""
    ## 1. Business Understanding (Pemahaman Bisnis / Konteks Proyek)
    ### 1.1. Latar Belakang Masalah
    Provinsi Jawa Timur merupakan salah satu pusat pertumbuhan ekonomi dan lumbung pangan nasional. Dinamika pembangunan yang pesat memicu terjadinya konversi tutupan lahan secara masif, seperti alih fungsi lahan pertanian (sawah) menjadi area pemukiman atau industri, serta menyusutnya luasan kawasan lindung seperti hutan mangrove di pesisir. 
    
    Pemantauan perubahan tutupan lahan (*Land Use and Land Cover* / LULC) menggunakan survei lapangan konvensional memakan biaya besar, waktu yang lama, dan cakupan spasial yang terbatas. Diperlukan sebuah pendekatan otomatis berbasis Sistem Informasi Geografis (SIG) dan teknologi Penginderaan Jauh (*Remote Sensing*) yang dipadukan dengan *Machine Learning* untuk memetakan kondisi lahan secara cepat, akurat, dan luas.

    ### 1.2. Tujuan Proyek
    1. **Otomatisasi Pemetaan Lahan:** Mengklasifikasikan 6 (enam) kelas tutupan lahan secara otomatis menggunakan data citra satelit Sentinel-2A.
    2. **Mendukung Kebijakan Spasial:** Menyediakan peta digital aktual sebagai instrumen evaluasi kebijakan tata ruang, pengawasan deforestasi, dan ketahanan pangan.
    
    ---

    ## 2. Data Understanding (Pemahaman Data)
    ### 2.1. Sumber Data (Data Collecting)
    Data diekstrak dari **Citra Satelit Sentinel-2A Level-2A (Bottom of Atmosphere)**. Proses akuisisi dilakukan melalui komputasi *cloud* di server **Copernicus Data Space Ecosystem (OpenEO)** dengan mengambil komposit nilai *median* dari rentang waktu observasi untuk menghilangkan gangguan tutupan awan.

    ### 2.2. Deskripsi Dataset dan Label Kelas
    Eksperimen ini menggunakan total **150 data titik sampel koordinat** (25 sampel per kelas) yang merujuk pada Standar Nasional Indonesia (SNI 7645-1:2014):
    1. **Sawah:** Area lahan basah pertanian.
    2. **Bangunan:** Area terbangun, pemukiman, dan infrastruktur padat.
    3. **Lahan Hijau:** Vegetasi non-pertanian, hutan daratan, atau ruang terbuka hijau.
    4. **Mangrove:** Vegetasi payau di sepanjang pesisir.
    5. **Ranu (Danau):** Badan air tawar tertutup.
    6. **Perairan Laut:** Wilayah perairan laut lepas.

    ### 2.3. Ekstraksi Fitur (Feature Engineering)
    Dataset dibentuk dari ekstraksi 7 fitur utama per piksel citra:
    * **Band Spektral:** B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), B11 (SWIR).
    * **Indeks Transformasi:** 
      * **NDVI** (Normalized Difference Vegetation Index) untuk kerapatan vegetasi.
      * **NDWI** (Normalized Difference Water Index) untuk deteksi badan air.

    ---

    ## 3. Data Preparation (Persiapan Data)
    Tahapan persiapan data meliputi penyelarasan *Coordinate Reference System* (CRS) ke EPSG:4326, ekstraksi nilai piksel dari citra GeoTIFF menggunakan pustaka `rasterio`, kalkulasi matematis matriks untuk indeks spektral, dan penyusunan struktur data ke dalam format tabular (CSV).

    ---

    ## 4. Modeling (Pemodelan)
    Data berjumlah 150 sampel dipecah dengan rasio **80:20** (120 data latih, 30 data uji) menggunakan pendekatan *stratified sampling*. Algoritma yang digunakan adalah **Gradient Boosting Classifier**, yang bekerja secara sekuensial membangun pohon keputusan (*decision tree*) untuk mengenali batas non-linear pada fitur spektral berdimensi tinggi secara optimal.

    ---

    ## 5. Evaluation (Evaluasi)
    Pengukuran performa dilakukan menggunakan metrik klasifikasi standar (*Classification Report*) yang mencakup *Accuracy, Precision, Recall*, dan *F1-Score*, serta dibuktikan penyebaran tebakannya menggunakan *Confusion Matrix* untuk memastikan tidak ada dominasi bias prediksi antar kelas lahan yang memiliki pola spektral serupa.

    ---
    
    ## 6. Deployment (Penerapan Sistem)
    Tahap akhir diimplementasikan melalui dua antarmuka (terdapat pada Tab 1 aplikasi ini):
    1. **Inferensi Spasial:** Menggunakan model kecerdasan buatan terlatih untuk memprediksi jutaan piksel pada citra satelit dan membentuk pemetaan raster berskala provinsi.
    2. **Web GIS:** Menampilkan sebaran titik observasi dan atribut spektralnya secara interaktif menggunakan integrasi pustaka Streamlit dan Folium.
    """)
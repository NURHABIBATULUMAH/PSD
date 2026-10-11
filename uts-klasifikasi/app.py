import streamlit as st
import pandas as pd
import folium
from folium import raster_layers
from streamlit_folium import st_folium
from PIL import Image
import os

# ==============================================================================
# KONFIGURASI HALAMAN UTAMA
# ==============================================================================
st.set_page_config(page_title="Dashboard LULC Jatim", page_icon="🌍", layout="wide")
st.title("UTS: Sistem Informasi Geografis")
st.markdown("**Klasifikasi Tutupan Lahan (LULC) Provinsi Jawa Timur Menggunakan Sentinel-2A**")
st.write("---")

# ==============================================================================
# PEMBAGIAN 4 TAB SEPERTI WEB REFERENSI
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "Peta Interaktif (Sampel)", 
    "Klasifikasi Regional (Jatim)", 
    "Evaluasi Model", 
    "Laporan Proyek"
])

# Palet Warna Global
warna_kelas = {
    "Sawah": "#90EE90", "Bangunan": "#FF0000", "Lahan Hijau": "#008000",
    "Mangrove": "#006400", "Ranu": "#ADD8E6", "Perairan Laut": "#0000FF"
}

# ==============================================================================
# TAB 1: PETA INTERAKTIF TITIK SAMPEL (Dengan Legenda)
# ==============================================================================
with tab1:
    st.subheader("Peta Sebaran Titik Sampel & Hasil Prediksi")
    st.markdown("Menampilkan seluruh poligon sampel dari 6 kelas tutupan lahan. Menampilkan seluruh poligon sampel dari 6 kelas tutupan lahan.")
    
    @st.cache_data
    def load_data():
        # Membaca direktori tempat app.py ini berada
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, "dataset_uts_klasifikasi.csv")
            
        return pd.read_csv(file_path)

    try:
        df = load_data()
        
        col1, col2 = st.columns([1, 4]) # Membagi layar untuk filter dan peta
        
        with col1:
            st.markdown("#### Filter Data")
            daftar_kelas = df['Kelas'].unique().tolist()
            kelas_terpilih = st.multiselect("Pilih Kelas Lahan:", options=daftar_kelas, default=daftar_kelas)
            
            st.write("---")
            st.markdown("#### Distribusi Titik")
            df_filtered = df[df['Kelas'].isin(kelas_terpilih)]
            st.dataframe(df_filtered['Kelas'].value_counts(), use_container_width=True)

        with col2:
            peta_titik = folium.Map(location=[-7.8, 112.5], zoom_start=8)
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite'
            ).add_to(peta_titik)

            fg_dict = {}
            for c in kelas_terpilih:
                fg_dict[c] = folium.FeatureGroup(name=f"Titik {c}")
                peta_titik.add_child(fg_dict[c])

            for idx, row in df_filtered.iterrows():
                kelas_aktual = row['Kelas']
                warna = warna_kelas.get(kelas_aktual, 'gray')
                
                popup_html = f"""
                <div style='font-family:sans-serif; font-size:12px; min-width:200px;'>
                    <b>Sampel Koordinat</b><br>
                    <span style='background:{warna}; color:white; padding:2px 6px; border-radius:3px;'>{kelas_aktual}</span>
                    <hr style='margin:5px 0'>
                    <b>Lat:</b> {row['Latitude']:.5f}<br>
                    <b>Lon:</b> {row['Longitude']:.5f}<br>
                    <b>NDVI:</b> {row['NDVI']:.3f}<br>
                    <b>NDWI:</b> {row['NDWI']:.3f}
                </div>
                """
                folium.CircleMarker(
                    location=[row['Latitude'], row['Longitude']], radius=6,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=kelas_aktual, color="white", weight=1, fill_color=warna, fill_opacity=0.9
                ).add_to(fg_dict[kelas_aktual])

            # Pembuatan Legenda
            legenda_html = "<div style='position:fixed; bottom:30px; left:30px; z-index:9999; background:rgba(255,255,255,0.9); padding:15px; border-radius:8px; box-shadow:0 4px 15px rgba(0,0,0,0.2);'>"
            legenda_html += "<b>Legenda Tutupan Lahan</b><hr style='margin:5px 0'>"
            for c_name in kelas_terpilih:
                warna_item = warna_kelas.get(c_name, 'gray')
                legenda_html += f"<div style='margin-bottom:4px;'><span style='display:inline-block; width:12px; height:12px; border-radius:50%; background:{warna_item}; margin-right:8px;'></span>{c_name}</div>"
            legenda_html += "</div>"
            
            if kelas_terpilih:
                peta_titik.get_root().html.add_child(folium.Element(legenda_html))

            folium.LayerControl().add_to(peta_titik)
            st_folium(peta_titik, width="100%", height=600)
            
    except Exception as e:
        st.error(f"Gagal memuat data titik. Pastikan file 'dataset_uts_klasifikasi.csv' tersedia. Error: {e}")


# ==============================================================================
# TAB 2: PETA KLASIFIKASI REGIONAL (IMAGE OVERLAY)
# ==============================================================================
with tab2:
    st.subheader("Pemetaan Tutupan Lahan Skala Regional (Jawa Timur)")
    st.markdown("Peta di bawah ini adalah hasil prediksi *Machine Learning* terhadap jutaan piksel citra satelit seluruh provinsi Jawa Timur secara utuh (bukan lagi sekadar titik sampel).")
    
    peta_regional = folium.Map(location=[-7.8, 112.5], zoom_start=8)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite'
    ).add_to(peta_regional)

    # Tambahkan overlay gambar raster jika file gambarnya tersedia
    # Contoh untuk gambar di Tab 3:
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_raster = os.path.join(BASE_DIR, "peta_klasifikasi_raster_jatim.png")
    if os.path.exists(file_raster):
        # Koordinat Batas Wilayah Jatim (Sesuaikan jika Bounding Box Anda berbeda)
        bounds_jatim = [[-8.85, 111.00], [-6.75, 114.65]] 
        raster_layers.ImageOverlay(
            image=file_raster,
            bounds=bounds_jatim,
            opacity=0.7,
            name='Prediksi LULC Jawa Timur',
            interactive=True,
            zindex=1
        ).add_to(peta_regional)
        folium.LayerControl().add_to(peta_regional)
        st_folium(peta_regional, width="100%", height=600)
    else:
        st.warning("File gambar raster `peta_klasifikasi_raster_jatim.png` tidak ditemukan di folder ini. Silakan tambahkan file tersebut agar peta regional muncul, atau ubah nama filenya di kode.")
        st_folium(peta_regional, width="100%", height=600)

# ==============================================================================
# TAB 3: EVALUASI MODEL (Confusion Matrix)
# ==============================================================================
with tab3:
    st.subheader("Evaluasi Performa Model (Gradient Boosting)")
    st.markdown("Visualisasi performa algoritma saat diujikan pada data *testing* (data baru yang belum pernah dilihat oleh algoritma).")
    
    col_metrik1, col_metrik2 = st.columns(2)
    with col_metrik1:
        st.success("✅ **Akurasi Keseluruhan (Accuracy): 88.3%**") # Angka contoh, sesuaikan dengan hasil Anda
    with col_metrik2:
        st.info("**Algoritma Utama: Gradient Boosting Classifier**")

    # Menampilkan Gambar Confusion Matrix yang sudah diekspor dari Jupyter Notebook
    # Contoh untuk gambar di Tab 3:
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_cm = os.path.join(BASE_DIR, "visualisasi_confusion_matrix.png")
    if os.path.exists(file_cm):
        st.image(Image.open(file_cm), caption="Heatmap Confusion Matrix (Kesalahan dan Keberhasilan Tebakan Model)", use_container_width=True)
    else:
        st.warning("File gambar grafik `visualisasi_confusion_matrix.png` tidak ditemukan. Pastikan Anda sudah menyimpannya dari Jupyter Notebook ke folder yang sama dengan app.py.")

# ==============================================================================
# TAB 4: LAPORAN PROYEK (CRISP-DM)
# ==============================================================================
with tab4:
    st.markdown("""
    ## 1. Business Understanding (Pemahaman Bisnis)
    Provinsi Jawa Timur merupakan salah satu pusat pertumbuhan ekonomi. Dinamika pembangunan memicu konversi lahan secara masif (alih fungsi sawah menjadi pemukiman). Diperlukan pendekatan otomatis berbasis *Remote Sensing* dan *Machine Learning* untuk memetakan kondisi lahan secara cepat.

    ## 2. Data Understanding (Pemahaman Data)
    Data diekstrak dari **Citra Sentinel-2A Level-2A (Bottom of Atmosphere)**. Eksperimen menggunakan total 300 data titik sampel yang mencakup kelas: Sawah, Bangunan, Lahan Hijau, Mangrove, Ranu, dan Perairan Laut. Fitur yang diekstrak meliputi spektral (B02, B03, B04, B08, B11) dan indeks spektral (NDVI, NDWI).

    ## 3. Data Preparation & Modeling
    Persiapan meliputi penyelarasan CRS (EPSG:4326) dan ekstraksi fitur titik (*centroid*). Data dipecah menjadi 80% *training* dan 20% *testing*. Algoritma **Gradient Boosting Classifier** digunakan karena mampu mempelajari pola non-linear pada data reflektansi spektral berdimensi tinggi.

    ## 4. Evaluation & Deployment
    Model dievaluasi menggunakan *Classification Report* dan *Confusion Matrix*.  Setelah model selesai dilatih menggunakan 240 data latih (training), performanya diukur menggunakan 60 data uji (testing) yang belum pernah dilihat oleh algoritma sebelumnya.
    """)
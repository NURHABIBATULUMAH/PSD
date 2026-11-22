import os, sys, joblib
import numpy as np, pandas as pd, cv2
import streamlit as st
from PIL import Image
from scipy.stats import skew
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern

st.set_page_config(page_title="Klasifikasi Kerapian Ruangan", page_icon="🏠", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "hasil", "model_svm_ruangan.joblib")
SIZE = 256

def extract_features_from_bgr(bgr):
    bgr = cv2.resize(bgr, (SIZE, SIZE))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    feats = {}
    for i, c in enumerate(['B', 'G', 'R']):
        ch = bgr[:, :, i].astype(float)
        feats[f'mean_{c}'] = ch.mean(); feats[f'std_{c}'] = ch.std(); feats[f'skew_{c}'] = float(skew(ch.ravel()))
    for i, c in enumerate(['H', 'S', 'V']):
        ch = hsv[:, :, i].astype(float)
        feats[f'mean_hsv_{c}'] = ch.mean(); feats[f'std_hsv_{c}'] = ch.std(); feats[f'skew_hsv_{c}'] = float(skew(ch.ravel()))
    for i, c in enumerate(['L', 'A', 'B_lab']):
        ch = lab[:, :, i].astype(float)
        feats[f'mean_lab_{c}'] = ch.mean(); feats[f'std_lab_{c}'] = ch.std()
    g_64 = (gray // 4).astype(np.uint8)
    P = graycomatrix(g_64, [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=64, symmetric=True, normed=True)
    feats['glcm_energy'] = graycoprops(P, 'energy').mean()
    feats['glcm_contrast'] = graycoprops(P, 'contrast').mean()
    feats['glcm_corr'] = graycoprops(P, 'correlation').mean()
    feats['glcm_homog'] = graycoprops(P, 'homogeneity').mean()
    p = P.mean(axis=(2, 3)); p = p[p > 0]
    feats['glcm_entropy'] = -(p * np.log2(p)).sum()
    edges_low = cv2.Canny(gray, 30, 100)
    edges_mid = cv2.Canny(gray, 50, 150)
    feats['edge_density_low'] = np.count_nonzero(edges_low) / (SIZE * SIZE)
    feats['edge_density_mid'] = np.count_nonzero(edges_mid) / (SIZE * SIZE)
    contours, _ = cv2.findContours(edges_mid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    feats['num_contours'] = len(contours)
    areas = [cv2.contourArea(cnt) for cnt in contours]
    feats['contour_area_mean'] = np.mean(areas) if len(areas) > 0 else 0
    feats['contour_area_std'] = np.std(areas) if len(areas) > 0 else 0
    h_third = SIZE // 3
    top_e = edges_mid[:h_third, :]; mid_e = edges_mid[h_third:2*h_third, :]; bot_e = edges_mid[2*h_third:, :]
    feats['edge_density_top'] = np.count_nonzero(top_e) / (SIZE * h_third)
    feats['edge_density_mid'] = np.count_nonzero(mid_e) / (SIZE * h_third)
    feats['edge_density_bot'] = np.count_nonzero(bot_e) / (SIZE * h_third)
    feats['clutter_ratio_bot_top'] = (feats['edge_density_bot'] + 1e-4) / (feats['edge_density_top'] + 1e-4)
    feats['clutter_ratio_mid_top'] = (feats['edge_density_mid'] + 1e-4) / (feats['edge_density_top'] + 1e-4)
    orb = cv2.ORB_create(nfeatures=1000)
    kp = orb.detect(gray, None)
    feats['num_keypoints_total'] = len(kp)
    bot_kp = [k for k in kp if k.pt[1] >= SIZE // 2]
    feats['num_keypoints_bottom'] = len(bot_kp)
    feats['kp_ratio_bottom'] = len(bot_kp) / (len(kp) + 1e-5)
    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    feats['lbp_mean'] = lbp.mean(); feats['lbp_std'] = lbp.std()
    return feats, edges_mid

st.title("🏠 Klasifikasi Kerapian Ruangan")
st.write("Sistem Cerdas Deteksi Kamar **Rapi vs. Berantakan** Berbasis Fitur Multimodal Computer Vision & Support Vector Machine (SVM).")

uploaded_file = st.file_uploader("Unggah Foto Ruangan (JPG / PNG):", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    img_pil = Image.open(uploaded_file).convert("RGB")
    img_np = np.array(img_pil)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    col1, col2 = st.columns(2)
    with col1:
        st.image(img_pil, caption="Foto Ruangan Diunggah", use_container_width=True)
        
    with st.spinner("Mengekstrak 44 fitur & menganalisis gambar..."):
        feats, edges = extract_features_from_bgr(img_bgr)
        model = joblib.load(MODEL_PATH)
        df_feat = pd.DataFrame([feats])
        pred_label = model.predict(df_feat)[0]
        probas = model.predict_proba(df_feat)[0]
        classes = model.classes_
        
        proba_dict = {cls: proba for cls, proba in zip(classes, probas)}
        
    with col2:
        st.image(edges, caption="Peta Deteksi Garis & Kontur (Canny Edge)", use_container_width=True, clamp=True)
        
    st.divider()
    
    if pred_label == "rapi":
        st.success(f"### Hasil Prediksi: 🟢 RAPI")
    else:
        st.error(f"### Hasil Prediksi: 🔴 BERANTAKAN")
        
    st.write(f"**Tingkat Keyakinan Model:** {proba_dict[pred_label]*100:.1f}%")
    st.progress(float(proba_dict[pred_label]))
    
    st.subheader("📊 Metrik Analisis Fisik Ruangan")
    m1, m2, m3 = st.columns(3)
    m1.metric("Kerapatan Garis Tepi", f"{feats['edge_density_mid']*100:.2f}%")
    m2.metric("Jumlah Kontur Tercecer", f"{feats['num_contours']}")
    m3.metric("ORB Clutter Keypoints", f"{feats['num_keypoints_total']}")

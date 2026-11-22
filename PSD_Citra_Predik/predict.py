import os, sys, joblib
import numpy as np, pandas as pd, cv2
from scipy.stats import skew
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "hasil", "model_svm_ruangan.joblib")
SIZE = 256

def extract_features(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File tidak ditemukan: {image_path}")
    
    bgr = cv2.imread(image_path)
    if bgr is None:
        raise ValueError(f"File bukan citra yang valid atau rusak: {image_path}")
        
    bgr = cv2.resize(bgr, (SIZE, SIZE))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    
    feats = {}
    
    # 1. RGB Moments
    for i, c in enumerate(['B', 'G', 'R']):
        ch = bgr[:, :, i].astype(float)
        feats[f'mean_{c}'] = ch.mean()
        feats[f'std_{c}'] = ch.std()
        feats[f'skew_{c}'] = float(skew(ch.ravel()))
        
    # 2. HSV Moments
    for i, c in enumerate(['H', 'S', 'V']):
        ch = hsv[:, :, i].astype(float)
        feats[f'mean_hsv_{c}'] = ch.mean()
        feats[f'std_hsv_{c}'] = ch.std()
        feats[f'skew_hsv_{c}'] = float(skew(ch.ravel()))
        
    # 3. Lab Moments
    for i, c in enumerate(['L', 'A', 'B_lab']):
        ch = lab[:, :, i].astype(float)
        feats[f'mean_lab_{c}'] = ch.mean()
        feats[f'std_lab_{c}'] = ch.std()
        
    # 4. GLCM Texture
    g_64 = (gray // 4).astype(np.uint8)
    P = graycomatrix(g_64, [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=64, symmetric=True, normed=True)
    feats['glcm_energy'] = graycoprops(P, 'energy').mean()
    feats['glcm_contrast'] = graycoprops(P, 'contrast').mean()
    feats['glcm_corr'] = graycoprops(P, 'correlation').mean()
    feats['glcm_homog'] = graycoprops(P, 'homogeneity').mean()
    p = P.mean(axis=(2, 3)); p = p[p > 0]
    feats['glcm_entropy'] = -(p * np.log2(p)).sum()
    
    # 5. Edges & Contours
    edges_low = cv2.Canny(gray, 30, 100)
    edges_mid = cv2.Canny(gray, 50, 150)
    feats['edge_density_low'] = np.count_nonzero(edges_low) / (SIZE * SIZE)
    feats['edge_density_mid'] = np.count_nonzero(edges_mid) / (SIZE * SIZE)
    contours, _ = cv2.findContours(edges_mid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    feats['num_contours'] = len(contours)
    areas = [cv2.contourArea(cnt) for cnt in contours]
    feats['contour_area_mean'] = np.mean(areas) if len(areas) > 0 else 0
    feats['contour_area_std'] = np.std(areas) if len(areas) > 0 else 0
    
    # 6. Spatial Bands
    h_third = SIZE // 3
    top_e = edges_mid[:h_third, :]
    mid_e = edges_mid[h_third:2*h_third, :]
    bot_e = edges_mid[2*h_third:, :]
    feats['edge_density_top'] = np.count_nonzero(top_e) / (SIZE * h_third)
    feats['edge_density_mid'] = np.count_nonzero(mid_e) / (SIZE * h_third)
    feats['edge_density_bot'] = np.count_nonzero(bot_e) / (SIZE * h_third)
    feats['clutter_ratio_bot_top'] = (feats['edge_density_bot'] + 1e-4) / (feats['edge_density_top'] + 1e-4)
    feats['clutter_ratio_mid_top'] = (feats['edge_density_mid'] + 1e-4) / (feats['edge_density_top'] + 1e-4)
    
    # 7. ORB Keypoints
    orb = cv2.ORB_create(nfeatures=1000)
    kp = orb.detect(gray, None)
    feats['num_keypoints_total'] = len(kp)
    bot_kp = [k for k in kp if k.pt[1] >= SIZE // 2]
    feats['num_keypoints_bottom'] = len(bot_kp)
    feats['kp_ratio_bottom'] = len(bot_kp) / (len(kp) + 1e-5)
    
    # 8. LBP
    lbp = local_binary_pattern(gray, P=8, R=1, method='uniform')
    feats['lbp_mean'] = lbp.mean()
    feats['lbp_std'] = lbp.std()
    
    return feats

def predict_image(image_path):
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model belum dilatih: {MODEL_PATH}")
        
    model = joblib.load(MODEL_PATH)
    feats = extract_features(image_path)
    df_feat = pd.DataFrame([feats])
    
    pred_label = model.predict(df_feat)[0]
    pred_proba = model.predict_proba(df_feat)[0]
    classes = model.classes_
    
    proba_dict = {cls: proba for cls, proba in zip(classes, pred_proba)}
    
    return pred_label, proba_dict, feats

if __name__ == "__main__":
    if len(sys.argv) > 1:
        img_target = sys.argv[1]
    else:
        sample_path = os.path.join(BASE_DIR, "data-1", "rapi", "rapi_001.jpg")
        print("Penggunaan: python predict.py <path_ke_foto.jpg>")
        print(f"Tidak ada argumen input, menjalankan sampel default: {sample_path}\n")
        img_target = sample_path
        
    try:
        label, probas, f_dict = predict_image(img_target)
        
        print("=" * 55)
        print("HASIL PREDIKSI KLASIFIKASI RUANGAN")
        print("=" * 55)
        print(f"File Citra  : {img_target}")
        print(f"Status      : >>> {label.upper()} <<<")
        print("-" * 55)
        print("Probabilitas Keyakinan Model:")
        for cls_name, p_val in probas.items():
            bar_len = int(p_val * 30)
            bar_str = "#" * bar_len + "-" * (30 - bar_len)
            print(f"  - {cls_name:12s}: {p_val*100:5.1f}% [{bar_str}]")
        print("-" * 55)
        print("Indikator Fisik Citra:")
        print(f"  - Kerapatan Garis Tepi (Canny Edge) : {f_dict['edge_density_mid']*100:.2f}%")
        print(f"  - Jumlah Kontur Objek Tercecer      : {f_dict['num_contours']} kontur")
        print(f"  - Jumlah Titik Kunci (ORB Clutter)  : {f_dict['num_keypoints_total']} keypoints")
        print(f"  - Rasio Clutter (Lantai / Dinding)  : {f_dict['clutter_ratio_bot_top']:.2f}x")
        print("=" * 55)
    except Exception as e:
        print(f"Error: {e}")

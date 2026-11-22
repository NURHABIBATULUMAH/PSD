"""
=============================================================
EKSTRAKSI FITUR CITRA - KLASIFIKASI KAMAR (RAPI vs BERANTAKAN)
=============================================================
Tahapan:
  1. Business Understanding
  2. Data Understanding
  3. Data Preparation
  4. Feature Extraction (Color: Mean, Std, Skewness + Texture: GLCM)
  5. Modeling (Decision Tree, Random Forest, KNN, SVM, Naive Bayes)
=============================================================
"""

import os
import warnings
from typing import Optional
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import skew
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray
from skimage import img_as_ubyte
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 0. KONFIGURASI PATH
# ─────────────────────────────────────────────
BASE_DIR    = Path(r"c:\Users\LENOVO\Documents\JP\psd\klasifikasi_citra")
BERANTAKAN  = BASE_DIR / "berantakan"
RAPI        = BASE_DIR / "rapi"
OUTPUT_CSV1 = BASE_DIR / "fitur_warna.csv"          # Mean, Std, Skewness
OUTPUT_CSV2 = BASE_DIR / "fitur_lengkap.csv"         # Warna + GLCM + Label
IMG_SIZE    = (256, 256)                              # Resize target

EXTENSIONS  = {".jpg", ".jpeg", ".png", ".heic"}

# ─────────────────────────────────────────────
# 1. FUNGSI UTILITAS
# ─────────────────────────────────────────────
def load_valid_images(folder: Path, label: str):
    """Memuat daftar path gambar yang valid dari sebuah folder."""
    images = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in EXTENSIONS:
            images.append((f, label))
    return images


def load_image_rgb(path: Path) -> Optional[np.ndarray]:
    """Membuka gambar, konversi ke RGB, dan resize ke IMG_SIZE."""
    try:
        img = Image.open(path).convert("RGB")
        img = img.resize(IMG_SIZE, Image.LANCZOS)
        return np.array(img, dtype=np.float32)
    except Exception as e:
        print(f"  [SKIP] {path.name}: {e}")
        return None


# ─────────────────────────────────────────────
# 2. EKSTRAKSI FITUR WARNA (Mean, Std, Skewness)
# ─────────────────────────────────────────────
def extract_color_features(img: np.ndarray) -> dict:
    """
    Menghitung Mean, Std, dan Skewness untuk tiap channel RGB.
    img shape: (H, W, 3), nilai 0-255.
    """
    feats = {}
    channels = ["R", "G", "B"]
    for i, ch in enumerate(channels):
        pix = img[:, :, i].flatten()
        feats[f"mean_{ch}"]  = float(np.mean(pix))
        feats[f"std_{ch}"]   = float(np.std(pix))
        feats[f"skew_{ch}"]  = float(skew(pix))
    return feats


# ─────────────────────────────────────────────
# 3. EKSTRAKSI FITUR TEKSTUR GLCM
# ─────────────────────────────────────────────
def extract_glcm_features(img: np.ndarray) -> dict:
    """
    Konversi ke grayscale → matriks GLCM →
    Energi, Entropi, Kontras, Korelasi, Homogenitas.
    img shape: (H, W, 3), nilai 0-255.
    """
    # Konversi ke grayscale (0-1 float) lalu ke uint8
    gray = rgb2gray(img / 255.0)
    gray_uint8 = img_as_ubyte(gray)

    # Hitung GLCM: sudut 0°, jarak 1 piksel, 256 level
    glcm = graycomatrix(
        gray_uint8,
        distances=[1],
        angles=[0],
        levels=256,
        symmetric=True,
        normed=True
    )

    contrast    = float(graycoprops(glcm, "contrast")[0, 0])
    correlation = float(graycoprops(glcm, "correlation")[0, 0])
    energy      = float(graycoprops(glcm, "energy")[0, 0])
    homogeneity = float(graycoprops(glcm, "homogeneity")[0, 0])

    # Entropi: -Σ p * log2(p+ε)
    p = glcm[:, :, 0, 0]
    entropy = float(-np.sum(p * np.log2(p + 1e-10)))

    return {
        "glcm_energy":      energy,
        "glcm_entropy":     entropy,
        "glcm_contrast":    contrast,
        "glcm_correlation": correlation,
        "glcm_homogeneity": homogeneity,
    }


# ─────────────────────────────────────────────
# 4. PIPELINE UTAMA
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  EKSTRAKSI FITUR CITRA KAMAR KOST")
    print("=" * 60)

    # Kumpulkan semua path
    all_images = []
    all_images += load_valid_images(BERANTAKAN, "berantakan")
    all_images += load_valid_images(RAPI,       "rapi")

    print(f"\n[INFO] Total gambar ditemukan: {len(all_images)}")
    print(f"       Berantakan : {sum(1 for _,l in all_images if l=='berantakan')}")
    print(f"       Rapi       : {sum(1 for _,l in all_images if l=='rapi')}")

    # ── Tahap A: Fitur Warna ──────────────────────────────
    print("\n[STEP 1] Ekstraksi fitur WARNA (Mean, Std, Skewness)...")
    color_rows = []
    for path, label in all_images:
        img = load_image_rgb(path)
        if img is None:
            continue
        feats = extract_color_features(img)
        feats["filename"] = path.name
        feats["label"]    = label
        color_rows.append(feats)

    df_color = pd.DataFrame(color_rows)
    # Susun kolom agar rapi
    col_order = ["filename",
                 "mean_R","mean_G","mean_B",
                 "std_R","std_G","std_B",
                 "skew_R","skew_G","skew_B",
                 "label"]
    df_color = df_color[col_order]
    df_color.to_csv(OUTPUT_CSV1, index=False)
    print(f"  → Tersimpan: {OUTPUT_CSV1}")
    print(df_color.head(5).to_string())

    # ── Tahap B: Fitur Warna + GLCM ──────────────────────
    print("\n[STEP 2] Ekstraksi fitur GLCM (Energi, Entropi, Kontras, Korelasi, Homogenitas)...")
    full_rows = []
    for path, label in all_images:
        img = load_image_rgb(path)
        if img is None:
            continue
        color_feats = extract_color_features(img)
        glcm_feats  = extract_glcm_features(img)
        row = {"filename": path.name}
        row.update(color_feats)
        row.update(glcm_feats)
        row["label"] = label
        full_rows.append(row)

    df_full = pd.DataFrame(full_rows)
    col_full = ["filename",
                "mean_R","mean_G","mean_B",
                "std_R","std_G","std_B",
                "skew_R","skew_G","skew_B",
                "glcm_energy","glcm_entropy","glcm_contrast",
                "glcm_correlation","glcm_homogeneity",
                "label"]
    df_full = df_full[col_full]
    df_full.to_csv(OUTPUT_CSV2, index=False)
    print(f"  → Tersimpan: {OUTPUT_CSV2}")
    print(df_full.head(5).to_string())

    # ── Statistik ─────────────────────────────────────────
    print("\n[INFO] Statistik Deskriptif:")
    print(df_full.describe().to_string())

    # ── Visualisasi Distribusi Fitur ──────────────────────
    print("\n[STEP 3] Membuat visualisasi distribusi fitur...")
    _plot_feature_distributions(df_full, BASE_DIR)

    return df_full


# ─────────────────────────────────────────────
# 5. VISUALISASI
# ─────────────────────────────────────────────
def _plot_feature_distributions(df: pd.DataFrame, out_dir: Path):
    features = ["mean_R","mean_G","mean_B",
                "std_R","std_G","std_B",
                "skew_R","skew_G","skew_B",
                "glcm_energy","glcm_entropy","glcm_contrast",
                "glcm_correlation","glcm_homogeneity"]

    fig, axes = plt.subplots(4, 4, figsize=(20, 16))
    axes = axes.flatten()
    for i, feat in enumerate(features):
        ax = axes[i]
        for label, grp in df.groupby("label"):
            ax.hist(grp[feat], bins=15, alpha=0.6, label=label)
        ax.set_title(feat, fontsize=10)
        ax.legend(fontsize=7)
    # Sembunyikan subplot kosong
    for j in range(len(features), len(axes)):
        axes[j].set_visible(False)

    plt.suptitle("Distribusi Fitur per Kelas", fontsize=14, y=1.01)
    plt.tight_layout()
    out_path = out_dir / "distribusi_fitur.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"  → Plot tersimpan: {out_path}")


# ─────────────────────────────────────────────
# 6. MODELING (Opsional — jalankan setelah CSV siap)
# ─────────────────────────────────────────────
def run_modeling(csv_path: Path = None):
    """
    Melatih dan mengevaluasi beberapa classifier:
      - Decision Tree
      - Random Forest
      - K-Nearest Neighbors
      - Support Vector Machine
      - Naive Bayes (Gaussian)
    """
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC
    from sklearn.naive_bayes import GaussianNB
    from sklearn.metrics import (classification_report,
                                 confusion_matrix, accuracy_score)

    print("\n" + "=" * 60)
    print("  MODELING - KLASIFIKASI CITRA KAMAR")
    print("=" * 60)

    if csv_path is None:
        csv_path = BASE_DIR / "fitur_lengkap.csv"

    df = pd.read_csv(csv_path)

    feature_cols = ["mean_R","mean_G","mean_B",
                    "std_R","std_G","std_B",
                    "skew_R","skew_G","skew_B",
                    "glcm_energy","glcm_entropy","glcm_contrast",
                    "glcm_correlation","glcm_homogeneity"]

    X = df[feature_cols].values
    le = LabelEncoder()
    y = le.fit_transform(df["label"].values)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scaling
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    models = {
        "Decision Tree":   DecisionTreeClassifier(random_state=42),
        "Random Forest":   RandomForestClassifier(n_estimators=100, random_state=42),
        "KNN (k=5)":       KNeighborsClassifier(n_neighbors=5),
        "SVM (RBF)":       SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42),
        "Naive Bayes":     GaussianNB(),
    }

    results = []
    for name, clf in models.items():
        # Tree-based tidak perlu scaling
        if name in ["Decision Tree", "Random Forest", "Naive Bayes"]:
            X_tr, X_te = X_train, X_test
        else:
            X_tr, X_te = X_train_sc, X_test_sc

        clf.fit(X_tr, y_train)
        y_pred = clf.predict(X_te)
        acc    = accuracy_score(y_test, y_pred)
        cv_acc = cross_val_score(clf, X, y, cv=5, scoring="accuracy").mean()

        print(f"\n── {name} ──")
        print(f"   Accuracy (test) : {acc:.4f}")
        print(f"   CV Accuracy (5) : {cv_acc:.4f}")
        print(classification_report(y_test, y_pred,
                                    target_names=le.classes_))

        cm = confusion_matrix(y_test, y_pred)
        results.append({
            "Model":       name,
            "Acc_Test":    round(acc, 4),
            "Acc_CV5":     round(cv_acc, 4),
            "CM":          cm.tolist()
        })

    # Simpan ringkasan
    df_res = pd.DataFrame([{k: v for k, v in r.items() if k != "CM"}
                            for r in results])
    df_res.to_csv(BASE_DIR / "hasil_modeling.csv", index=False)
    print("\n[Ringkasan Modeling]")
    print(df_res.sort_values("Acc_Test", ascending=False).to_string(index=False))
    print(f"\n→ Tersimpan: {BASE_DIR / 'hasil_modeling.csv'}")

    # Plot Confusion Matrix
    _plot_confusion_matrices(results, le.classes_, BASE_DIR)

    return df_res


def _plot_confusion_matrices(results, classes, out_dir: Path):
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(5*n, 4))
    if n == 1:
        axes = [axes]
    for ax, r in zip(axes, results):
        cm = np.array(r["CM"])
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.set_title(r["Model"], fontsize=10)
        ax.set_xticks(range(len(classes)))
        ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(classes, rotation=30)
        ax.set_yticklabels(classes)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(cm[i, j]),
                        ha="center", va="center", fontsize=12,
                        color="white" if cm[i, j] > cm.max()/2 else "black")
        ax.set_xlabel("Prediksi")
        ax.set_ylabel("Aktual")
    plt.suptitle("Confusion Matrix per Model", fontsize=12)
    plt.tight_layout()
    out_path = out_dir / "confusion_matrix.png"
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close()
    print(f"  → Confusion matrix: {out_path}")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    df_full = main()
    run_modeling()
    print("\n[SELESAI] Semua proses ekstraksi fitur dan modeling telah selesai.")

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import joblib
import librosa
import numpy as np
import pandas as pd
import sounddevice as sd
import pyttsx3

class LiveAutoNoiseDetector:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistem Pemantauan Otomatis & Peringatan Suara (SVM)")
        self.root.geometry("600x520")
        self.root.resizable(False, False)
        
        # Variabel kontrol
        self.is_running = False
        self.q = queue.Queue()
        self.last_warning_time = 0  # Cooldown agar suara peringatan tidak spam

        # Inisialisasi Text-to-Speech (TTS)
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Kecepatan bicara
            self.tts_engine.setProperty('volume', 1.0) # Volume maksimal
        except Exception as e:
            print(f"Gagal menginisialisasi TTS: {e}")

        # Muat Model SVM dan Artefak
        try:
            self.model = joblib.load("svm_audio_model.pkl")
            self.scaler = joblib.load("audio_scaler.pkl")
            self.feature_names = joblib.load("feature_names.pkl")
        except Exception as e:
            print(f"Error memuat model: {e}")

        self.setup_ui()
        
        # Mulai pengecekan antrean data dari background thread ke GUI
        self.root.after(100, self.process_queue)

    def setup_ui(self):
        # Header Title
        title_label = tk.Label(self.root, text="🎙️ Auto-Monitoring & Voice Warning System", font=("Arial", 14, "bold"), fg="#333")
        title_label.pack(pady=10)

        # Status Frame (Indikator Warna)
        self.status_frame = tk.Frame(self.root, bg="#2ecc71", width=520, height=110, relief="raised", bd=2)
        self.status_frame.pack_propagate(False)
        self.status_frame.pack(pady=10)

        self.status_label = tk.Label(self.status_frame, text="SISTEM STANDBY (SIAP)", font=("Arial", 14, "bold"), bg="#2ecc71", fg="white")
        self.status_label.pack(expand=True)

        self.conf_label = tk.Label(self.status_frame, text="Keyakinan: 0.00%", font=("Arial", 10), bg="#2ecc71", fg="white")
        self.conf_label.pack(expand=True)

        # Tombol Kontrol (Start & Stop)
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="▶ Aktifkan Auto-Monitoring", font=("Arial", 11, "bold"), bg="#2ecc71", fg="white", width=22, command=self.start_monitoring)
        self.start_btn.grid(row=0, column=0, padx=10)

        self.stop_btn = tk.Button(btn_frame, text="⏹ Matikan Sistem", font=("Arial", 11, "bold"), bg="#e74c3c", fg="white", width=22, state="disabled", command=self.stop_monitoring)
        self.stop_btn.grid(row=0, column=1, padx=10)

        # Log Aktivitas / Riwayat Deteksi
        log_label = tk.Label(self.root, text="Log Aktivitas & Respon Otomatis:", font=("Arial", 10, "bold"), anchor="w")
        log_label.pack(fill="x", padx=40, pady=(10, 2))

        self.log_area = scrolledtext.ScrolledText(self.root, width=68, height=10, font=("Consolas", 9))
        self.log_area.pack(padx=40, pady=5)
        self.log_area.config(state="disabled")

    def log_message(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def start_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.log_message(">> Sistem pemantauan otomatis diaktifkan...")
            
            # Jalankan stream audio di latar belakang (background thread)
            threading.Thread(target=self.audio_stream_worker, daemon=True).start()

    def stop_monitoring(self):
        if self.is_running:
            self.is_running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status_frame.config(bg="#2ecc71")
            self.status_label.config(text="SISTEM DIMATIKAN", bg="#2ecc71")
            self.conf_label.config(text="Keyakinan: 0.00%", bg="#2ecc71")
            self.log_message(">> Sistem pemantauan dimatikan.")

    def audio_stream_worker(self):
        SR = 22050
        DURATION = 2.0  # Menganalisis suara tiap potongan 2 detik
        BLOCK_SIZE = int(SR * DURATION)

        def callback(indata, frames, time_info, status):
            if not self.is_running:
                raise sd.CallbackStop()
            audio_chunk = indata[:, 0]
            self.q.put(audio_chunk)

        try:
            with sd.InputStream(channels=1, samplerate=SR, blocksize=BLOCK_SIZE, callback=callback):
                while self.is_running:
                    time.sleep(0.1)
        except Exception as e:
            self.q.put(("ERROR", str(e)))

    def process_queue(self):
        while not self.q.empty():
            item = self.q.get()
            if isinstance(item, tuple) and item[0] == "ERROR":
                self.log_message(f"Error Audio: {item[1]}")
                continue

            audio_chunk = item
            try:
                # Ekstraksi 16 Fitur Asli
                rms = librosa.feature.rms(y=audio_chunk)
                centroid = librosa.feature.spectral_centroid(y=audio_chunk, sr=22050)
                zcr = librosa.feature.zero_crossing_rate(y=audio_chunk)
                mfcc = librosa.feature.mfcc(y=audio_chunk, sr=22050, n_mfcc=13)

                row_data = {
                    'rms': np.mean(rms),
                    'centroid': np.mean(centroid),
                    'zcr': np.mean(zcr),
                }
                mfcc_mean = np.mean(mfcc, axis=1)
                for i, val in enumerate(mfcc_mean, start=1):
                    row_data[f'mfcc_{i}'] = val

                df_input = pd.DataFrame([row_data])[self.feature_names]
                input_scaled = self.scaler.transform(df_input)
                
                # Prediksi dengan Model SVM
                prediction = self.model.predict(input_scaled)[0]
                confidence = np.max(self.model.predict_proba(input_scaled)[0]) * 100

                timestamp = time.strftime("%H:%M:%S")

                # KONDISI: Jika terdeteksi BERISIK dengan keyakinan >= 80%
                if prediction.lower() == 'berisik' and confidence >= 80:
                    self.status_frame.config(bg="#e74c3c")
                    self.status_label.config(text="⚠️ TERDETEKSI BERISIK!", bg="#e74c3c")
                    self.conf_label.config(text=f"Keyakinan: {confidence:.2f}%", bg="#e74c3c")
                    
                    self.log_message(f"[{timestamp}] Status: BERISIK ({confidence:.2f}%)")

                    # Logika Peringatan Suara Otomatis dengan Cooldown (4 detik)
                    current_time = time.time()
                    if current_time - self.last_warning_time > 4.0:
                        self.last_warning_time = current_time
                        self.log_message(f"[{timestamp}] 🔊 Mengeluarkan Peringatan Suara...")
                        # Jalankan suara di thread terpisah agar UI tidak lag
                        threading.Thread(target=self.speak_warning, daemon=True).start()
                else:
                    self.status_frame.config(bg="#2ecc71")
                    self.status_label.config(text="✔ AMAN (NON-BERISIK)", bg="#2ecc71")
                    self.conf_label.config(text=f"Keyakinan: {confidence:.2f}%", bg="#2ecc71")

            except Exception as e:
                print(f"Error processing chunk: {e}")

        self.root.after(100, self.process_queue)

    def speak_warning(self):
        try:
            self.tts_engine.say("Tolong tenang, jangan berisik.")
            self.tts_engine.runAndWait()
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = LiveAutoNoiseDetector(root)
    root.mainloop()
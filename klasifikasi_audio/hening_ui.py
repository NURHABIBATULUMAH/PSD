import tkinter as tk
from tkinter import font as tkfont
import threading
import queue
import time
import joblib
import librosa
import numpy as np
import pandas as pd
import sounddevice as sd
import pyttsx3
import soundfile as sf
import os

# ---------------------------------------------------------------
# Token desain
# ---------------------------------------------------------------
BG = "#DDE4E7"      # latar jendela, abu kebiruan pucat
PANEL = "#EEF2F3"   # permukaan panel
LINE = "#C5CFD3"    # garis dan slot kosong
INK = "#16252D"     # teks utama
DIM = "#66777F"     # teks redup
QUIET = "#1E7B73"   # tenang
LOUD = "#B3205F"    # berisik

SR = 22050
WINDOW_SECONDS = 2.0   # panjang suara yang dinilai model (sama seperti saat training)
HOP_SECONDS = 0.25     # seberapa sering penilaian diperbarui
ATTACK_HITS = 2        # berapa penilaian berturut-turut di atas ambang sebelum menegur
RELEASE_CALMS = 4      # berapa penilaian berturut-turut di bawah ambang sebelum kembali tenang
STRONG_PCT = 95        # peluang sangat tinggi: langsung menegur tanpa menunggu
READ_SECONDS = 0.1     # ukuran potongan kecil dari mikrofon
DEFAULT_THRESHOLD = 80
COOLDOWN = 4.0
HISTORY = 40
WARNING_AUDIO = "peringatan.wav"  # taruh di folder yang sama dengan script


def pick_font(candidates):
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"


def list_input_devices():
    """Daftar (index, nama) perangkat yang punya input mikrofon."""
    devices = []
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                devices.append((i, d["name"]))
    except Exception:
        pass
    return devices


class HistoryStrip(tk.Canvas):
    """Satu batang = satu potongan 2 detik.
    Tinggi = peluang berisik, warna = hasil keputusan, garis putus = ambang teguran."""

    BAR_W, GAP, H = 8, 4, 96

    def __init__(self, parent):
        self.total_w = HISTORY * (self.BAR_W + self.GAP) - self.GAP
        super().__init__(parent, width=self.total_w, height=self.H, bg=PANEL, highlightthickness=0)
        self.items = []
        self.threshold = DEFAULT_THRESHOLD
        self.draw()

    def push(self, level, noisy):
        self.items.append((level, noisy))
        self.items = self.items[-HISTORY:]
        self.draw()

    def clear(self):
        self.items = []
        self.draw()

    def set_threshold(self, value):
        self.threshold = value
        self.draw()

    def draw(self):
        self.delete("all")
        offset = HISTORY - len(self.items)
        for slot in range(HISTORY):
            x0 = slot * (self.BAR_W + self.GAP)
            x1 = x0 + self.BAR_W
            if slot < offset:
                self.create_rectangle(x0, self.H - 3, x1, self.H, fill=LINE, width=0)
                continue
            level, noisy = self.items[slot - offset]
            h = max(3, int(level * self.H))
            self.create_rectangle(x0, self.H - h, x1, self.H,
                                  fill=LOUD if noisy else QUIET, width=0)
        y = self.H - self.threshold / 100 * self.H
        self.create_line(0, y, self.total_w, y, fill=INK, dash=(4, 3))


class FlatButton(tk.Canvas):
    def __init__(self, parent, text, command, font, width=200, height=44):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, cursor="hand2")
        self.command = command
        self.w, self.h = width, height
        self.font = font
        self.fill, self.fg = INK, PANEL
        self.label = text
        self.enabled = True
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._paint(hover=True))
        self.bind("<Leave>", lambda e: self._paint())
        self._paint()

    def style(self, text, fill, fg):
        self.label, self.fill, self.fg = text, fill, fg
        self._paint()

    def _paint(self, hover=False):
        self.delete("all")
        fill = self.fill
        if hover and self.enabled:
            fill = LOUD if self.fill == INK else DIM
        self.create_rectangle(0, 0, self.w, self.h, fill=fill, width=0)
        self.create_text(self.w / 2, self.h / 2, text=self.label, fill=self.fg, font=self.font)

    def _click(self, _event):
        if self.enabled:
            self.command()


class LiveAutoNoiseDetector:
    def __init__(self, root):
        self.root = root
        self.root.title("Hening")
        self.root.geometry("580x730")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.is_running = False
        self.q = queue.Queue()
        self.last_warning_time = 0
        self.speaking = False
        self.model_ready = False
        self.threshold = DEFAULT_THRESHOLD
        self.noisy_idx = None
        self.session = 0
        self.window_len = int(SR * WINDOW_SECONDS)
        self.ring = np.zeros(self.window_len, dtype=np.float32)
        self.filled = 0
        self.lock = threading.Lock()
        self.was_noisy = False
        self.last_log = 0
        self.hit_count = 0
        self.calm_count = 0
        self.alarm = False

        self.f_ui = pick_font(["Inter", "Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans"])
        self.f_mono = pick_font(["JetBrains Mono", "IBM Plex Mono", "Consolas", "Menlo", "DejaVu Sans Mono"])

        self.devices = list_input_devices()

        try:
            self.model = joblib.load("svm_audio_model.pkl")
            self.scaler = joblib.load("audio_scaler.pkl")
            self.feature_names = joblib.load("feature_names.pkl")
            classes = [str(c).lower() for c in self.model.classes_]
            if "berisik" in classes:
                self.noisy_idx = classes.index("berisik")
            self.model_ready = True
        except Exception as e:
            self.model_error = str(e)

        self.setup_ui()

        if not self.model_ready:
            self.log_message(f"Model tidak bisa dimuat: {self.model_error}", "alert")
            self.toggle_btn.enabled = False
            self.toggle_btn.style("Model tidak ditemukan", LINE, DIM)
        elif self.noisy_idx is None:
            self.log_message("Kelas 'berisik' tidak ada di model. Periksa label saat training.", "alert")
            self.toggle_btn.enabled = False
            self.toggle_btn.style("Label model tidak cocok", LINE, DIM)

        if not self.devices:
            self.log_message("Tidak ada mikrofon yang terdeteksi.", "alert")
            self.toggle_btn.enabled = False
            self.toggle_btn.style("Mikrofon tidak ditemukan", LINE, DIM)

        self.root.after(100, self.process_queue)

    # -----------------------------------------------------------
    # UI
    # -----------------------------------------------------------
    def setup_ui(self):
        pad = 32

        tk.Label(self.root, text="Hening", font=(self.f_ui, 22, "bold"),
                 bg=BG, fg=INK, anchor="w").pack(fill="x", padx=pad, pady=(28, 0))
        tk.Label(self.root, text="Mendengarkan ruangan dan menegur saat terlalu ramai",
                 font=(self.f_ui, 10), bg=BG, fg=DIM, anchor="w").pack(fill="x", padx=pad)

        # Panel utama
        panel = tk.Frame(self.root, bg=PANEL)
        panel.pack(fill="x", padx=pad, pady=(22, 0))
        inner = tk.Frame(panel, bg=PANEL)
        inner.pack(fill="x", padx=20, pady=20)

        self.status_label = tk.Label(inner, text="Belum mendengarkan",
                                     font=(self.f_ui, 30, "bold"),
                                     bg=PANEL, fg=DIM, anchor="w")
        self.status_label.pack(fill="x")

        self.conf_label = tk.Label(inner, text="Tekan Mulai untuk membuka mikrofon",
                                   font=(self.f_mono, 11), bg=PANEL, fg=DIM, anchor="w")
        self.conf_label.pack(fill="x", pady=(2, 18))

        self.strip = HistoryStrip(inner)
        self.strip.pack(anchor="w")

        tk.Label(inner, text=f"Batang baru muncul tiap {HOP_SECONDS:g} detik".replace(".", ",") + f" dan menilai {WINDOW_SECONDS:g} detik suara terakhir. Tinggi = peluang berisik, garis putus = ambang teguran.",
                 font=(self.f_ui, 9), bg=PANEL, fg=DIM, anchor="w",
                 wraplength=self.strip.total_w, justify="left").pack(fill="x", pady=(8, 0))

        # Pengaturan
        settings = tk.Frame(self.root, bg=BG)
        settings.pack(fill="x", padx=pad, pady=(22, 0))
        settings.columnconfigure(1, weight=1)

        tk.Label(settings, text="Mikrofon", font=(self.f_ui, 10), bg=BG, fg=DIM,
                 anchor="w", width=14).grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.device_names = [f"{i}: {name}"[:46] for i, name in self.devices] or ["Tidak ada"]
        self.device_var = tk.StringVar(value=self.device_names[self._default_device_position()])
        self.mic_menu = tk.OptionMenu(settings, self.device_var, *self.device_names)
        self.mic_menu.config(font=(self.f_ui, 10), bg=PANEL, fg=INK, activebackground=LINE,
                             activeforeground=INK, relief="flat", bd=0, highlightthickness=0,
                             anchor="w", indicatoron=False, padx=10, pady=6)
        self.mic_menu["menu"].config(font=(self.f_ui, 10), bg=PANEL, fg=INK,
                                     activebackground=INK, activeforeground=PANEL, bd=0)
        self.mic_menu.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        tk.Label(settings, text="Ambang teguran", font=(self.f_ui, 10), bg=BG, fg=DIM,
                 anchor="w", width=14).grid(row=1, column=0, sticky="w")

        self.thr_scale = tk.Scale(settings, from_=50, to=95, resolution=5, orient="horizontal",
                                  showvalue=False, bg=BG, troughcolor=LINE, fg=INK,
                                  highlightthickness=0, bd=0, sliderrelief="flat",
                                  activebackground=INK, length=240, command=self.on_threshold)
        self.thr_scale.set(DEFAULT_THRESHOLD)
        self.thr_scale.grid(row=1, column=1, sticky="w")

        self.thr_label = tk.Label(settings, text=f"{DEFAULT_THRESHOLD}%", font=(self.f_mono, 10),
                                  bg=BG, fg=INK, anchor="e", width=5)
        self.thr_label.grid(row=1, column=2, sticky="e")

        # Tombol tunggal
        self.toggle_btn = FlatButton(self.root, "Mulai", self.toggle,
                                     font=(self.f_ui, 11, "bold"), width=160)
        self.toggle_btn.pack(anchor="w", padx=pad, pady=(20, 0))

        # Log
        tk.Label(self.root, text="Riwayat", font=(self.f_ui, 10, "bold"),
                 bg=BG, fg=INK, anchor="w").pack(fill="x", padx=pad, pady=(24, 6))

        log_wrap = tk.Frame(self.root, bg=LINE)
        log_wrap.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        self.log_area = tk.Text(log_wrap, height=6, font=(self.f_mono, 9), bg=BG, fg=INK,
                                relief="flat", bd=0, padx=12, pady=10, wrap="word",
                                highlightthickness=0, cursor="arrow")
        self.log_area.pack(fill="both", expand=True, pady=(1, 0))
        self.log_area.tag_config("alert", foreground=LOUD)
        self.log_area.tag_config("dim", foreground=DIM)
        self.log_area.config(state="disabled")

    def _default_device_position(self):
        try:
            default_idx = sd.default.device[0]
            for pos, (i, _) in enumerate(self.devices):
                if i == default_idx:
                    return pos
        except Exception:
            pass
        return 0

    def selected_device(self):
        try:
            return self.devices[self.device_names.index(self.device_var.get())][0]
        except (ValueError, IndexError):
            return None

    def on_threshold(self, value):
        self.threshold = int(float(value))
        self.thr_label.config(text=f"{self.threshold}%")
        self.strip.set_threshold(self.threshold)

    def log_message(self, message, tag="dim"):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def set_status(self, word, color, detail):
        self.status_label.config(text=word, fg=color)
        self.conf_label.config(text=detail)

    # -----------------------------------------------------------
    # Kontrol
    # -----------------------------------------------------------
    def toggle(self):
        if self.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        if self.is_running:
            return
        device = self.selected_device()
        self.is_running = True
        self.mic_menu.config(state="disabled")
        self.toggle_btn.style("Berhenti", LINE, INK)
        self.set_status("Mendengarkan", INK, "Mengumpulkan 2 detik suara pertama")
        self.log_message(f"[{time.strftime('%H:%M:%S')}] Mulai mendengarkan dari {self.device_var.get()}")
        self.session += 1
        sid = self.session
        with self.lock:
            self.ring = np.zeros(self.window_len, dtype=np.float32)
            self.filled = 0
        self.was_noisy = False
        self.hit_count = 0
        self.calm_count = 0
        self.alarm = False
        threading.Thread(target=self.audio_stream_worker, args=(device, sid), daemon=True).start()
        threading.Thread(target=self.analysis_worker, args=(sid,), daemon=True).start()

    def stop_monitoring(self):
        if not self.is_running:
            return
        self.is_running = False
        self.mic_menu.config(state="normal")
        self.toggle_btn.style("Mulai", INK, PANEL)
        self.set_status("Berhenti", DIM, "Mikrofon ditutup")
        self.strip.clear()
        self.log_message(f"[{time.strftime('%H:%M:%S')}] Berhenti mendengarkan")

    # -----------------------------------------------------------
    # Audio
    # -----------------------------------------------------------
    def audio_stream_worker(self, device, sid):
        block_size = int(SR * READ_SECONDS)

        def callback(indata, frames, time_info, status):
            if not self.is_running or sid != self.session:
                raise sd.CallbackStop()
            block = indata[:, 0].copy()
            n = len(block)
            with self.lock:
                self.ring = np.concatenate([self.ring[n:], block])
                self.filled = min(self.filled + n, self.window_len)

        try:
            with sd.InputStream(device=device, channels=1, samplerate=SR,
                                blocksize=block_size, callback=callback):
                while self.is_running and sid == self.session:
                    time.sleep(0.1)
        except Exception as e:
            self.q.put(("ERROR", str(e), sid))

    def analysis_worker(self, sid):
        """Menilai 2 detik suara terakhir setiap HOP_SECONDS, di luar thread GUI."""
        next_tick = time.time() + HOP_SECONDS
        while self.is_running and sid == self.session:
            time.sleep(max(0, next_tick - time.time()))
            next_tick += HOP_SECONDS
            with self.lock:
                if self.filled < self.window_len:
                    continue  # buffer awal belum penuh
                window = self.ring.copy()
            try:
                p_noisy, db = self.score_window(window)
                self.q.put(("RESULT", p_noisy, db, sid))
            except Exception as e:
                print(f"Error processing window: {e}")

    def score_window(self, audio):
        rms = librosa.feature.rms(y=audio)
        centroid = librosa.feature.spectral_centroid(y=audio, sr=SR)
        zcr = librosa.feature.zero_crossing_rate(y=audio)
        mfcc = librosa.feature.mfcc(y=audio, sr=SR, n_mfcc=13)

        row_data = {
            "rms": np.mean(rms),
            "centroid": np.mean(centroid),
            "zcr": np.mean(zcr),
        }
        for i, val in enumerate(np.mean(mfcc, axis=1), start=1):
            row_data[f"mfcc_{i}"] = val

        df_input = pd.DataFrame([row_data])[self.feature_names]
        input_scaled = self.scaler.transform(df_input)
        proba = self.model.predict_proba(input_scaled)[0]

        p_noisy = float(proba[self.noisy_idx]) * 100
        db = 20 * np.log10(max(float(np.mean(rms)), 1e-6))
        return p_noisy, db

    def process_queue(self):
        while not self.q.empty():
            item = self.q.get()
            if item[-1] != self.session or not self.is_running:
                continue  # buang sisa dari sesi lama

            if item[0] == "ERROR":
                self.log_message(f"Mikrofon bermasalah: {item[1]}", "alert")
                self.stop_monitoring()
            elif item[0] == "RESULT":
                self.apply_result(item[1], item[2])

        self.root.after(50, self.process_queue)

    def apply_result(self, p_noisy, db):
        now = time.time()
        timestamp = time.strftime("%H:%M:%S")
        raw_noisy = p_noisy >= self.threshold

        # Batang menampilkan hasil model apa adanya
        self.strip.push(p_noisy / 100, raw_noisy)
        detail = f"peluang berisik {p_noisy:.0f}%   {db:.0f} dB"

        # Keputusan teguran dihaluskan: cepat menyala, lambat padam
        if raw_noisy:
            self.hit_count += 1
            self.calm_count = 0
        else:
            self.calm_count += 1
            self.hit_count = 0

        strong = p_noisy >= max(STRONG_PCT, self.threshold)
        if not self.alarm and (strong or self.hit_count >= ATTACK_HITS):
            self.alarm = True
        elif self.alarm and self.calm_count >= RELEASE_CALMS:
            self.alarm = False

        if self.alarm:
            self.set_status("Berisik", LOUD, detail)
            if not self.was_noisy or now - self.last_log > 2.0:
                self.log_message(f"[{timestamp}] Berisik, peluang {p_noisy:.0f}%", "alert")
                self.last_log = now

            if now - self.last_warning_time > COOLDOWN:
                self.last_warning_time = now
                self.log_message(f"[{timestamp}] Peringatan suara diputar")
                threading.Thread(target=self.speak_warning, daemon=True).start()
        else:
            self.set_status("Tenang", QUIET, detail)

        self.was_noisy = self.alarm

    def speak_warning(self):
        if self.speaking:
            return
        self.speaking = True
        try:
            if os.path.exists(WARNING_AUDIO):
                data, rate = sf.read(WARNING_AUDIO, dtype="float32")
                sd.play(data, rate)
                sd.wait()
            else:
                # Cadangan: suara TTS jika file audio tidak ditemukan
                engine = pyttsx3.init()
                engine.setProperty("rate", 150)
                engine.setProperty("volume", 1.0)
                engine.say("Tolong tenang, jangan berisik.")
                engine.runAndWait()
                engine.stop()
        except Exception as e:
            print(f"Gagal memutar peringatan: {e}")
        finally:
            self.speaking = False


if __name__ == "__main__":
    root = tk.Tk()
    app = LiveAutoNoiseDetector(root)
    root.mainloop()
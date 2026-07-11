import os
import sys
import re
import shutil
import subprocess
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QFrame,
    QDialog,
    QLineEdit,
    QProgressBar,
    QFileDialog,
    QTextEdit,
)
from PySide6.QtCore import Qt, QUrl, QObject, Signal, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QIntValidator, QTextCursor

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class ConsoleInterceptor(QObject):
    progress_updated = Signal(int)

    def __init__(self):
        super().__init__()
        self.original_stderr = sys.stderr
        sys.stderr = self

    def write(self, message):
        self.original_stderr.write(message)
        match = re.search(r"(\d+)%", message)
        if match:
            self.progress_updated.emit(int(match.group(1)))

    def flush(self):
        self.original_stderr.flush()

class GenerationProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(18)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QProgressBar {
                background-color: #0E0E0E;
                border: 1px solid #2A2A2A;
                border-radius: 4px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #2ECC8F;
                border-radius: 3px;
            }
        """)
        self.setValue(0)
        self.hide()

class HardwareMonitorWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            "QFrame { background-color: #0B0E14; border: 1px solid #1A1A1A; border-radius: 4px; padding: 10px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        lbl = QLabel("SYSTEM RESOURCES")
        lbl.setStyleSheet(
            "color: #737373; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
        )
        layout.addWidget(lbl)
        self.cpu_lbl = QLabel("CPU: 0%")
        self.cpu_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-weight: bold;"
        )
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFixedHeight(4)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setStyleSheet(
            "QProgressBar { background-color: #1A1A1A; border: none; } QProgressBar::chunk { background-color: #6C9BFF; }"
        )
        layout.addWidget(self.cpu_lbl)
        layout.addWidget(self.cpu_bar)
        self.vram_lbl = QLabel("VRAM: 0.0GB")
        self.vram_lbl.setStyleSheet(
            "color: #E2E8F0; font-size: 11px; font-weight: bold;"
        )
        self.vram_bar = QProgressBar()
        self.vram_bar.setFixedHeight(4)
        self.vram_bar.setTextVisible(False)
        self.vram_bar.setStyleSheet(
            "QProgressBar { background-color: #1A1A1A; border: none; } QProgressBar::chunk { background-color: #F5A524; }"
        )
        layout.addWidget(self.vram_lbl)
        layout.addWidget(self.vram_bar)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def update_stats(self):
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent()
            self.cpu_lbl.setText(f"CPU: {cpu}%")
            self.cpu_bar.setValue(int(cpu))
        else:
            self.cpu_lbl.setText("CPU: N/A (Install psutil)")
        if HAS_TORCH and torch.cuda.is_available():
            try:
                mem_alloc = torch.cuda.memory_allocated(0) / (1024**3)
                mem_tot = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                self.vram_lbl.setText(f"VRAM: {mem_alloc:.1f}GB / {mem_tot:.1f}GB")
                self.vram_bar.setValue(int((mem_alloc / mem_tot) * 100))
            except:
                pass

class SettingsDialog(QDialog):
    def __init__(
        self, current_settings, is_global=False, hide_basic=False, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(
            "Global Conversation Settings" if is_global else "Generation Settings"
        )
        self.setFixedSize(400, 650 if not hide_basic else 500)
        self.setStyleSheet(
            "QDialog { background-color: #0B0E14; border: 1px solid #2A2A2A; }"
        )
        self.settings = current_settings.copy()
        self.apply_to_all = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        header = QLabel("NEURAL ENGINE PARAMETERS")
        header.setStyleSheet(
            "color: #FFFFFF; font-size: 14px; font-weight: 900; letter-spacing: 2px;"
        )
        layout.addWidget(header)
        layout.addSpacing(10)
        self.sliders = {}

        def add_adv_slider(name, key, min_val, max_val, current_val, divisor=100.0):
            group = QWidget()
            l = QVBoxLayout(group)
            l.setContentsMargins(0, 0, 0, 0)
            hl = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #737373; font-size: 11px; font-weight: bold;")
            val_lbl = QLabel(f"{current_val/divisor:.2f}")
            val_lbl.setStyleSheet("color: #6C9BFF; font-size: 12px; font-weight: bold;")
            hl.addWidget(lbl)
            hl.addStretch()
            hl.addWidget(val_lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(current_val)
            slider.setStyleSheet(
                "QSlider::groove:horizontal { border-radius: 2px; height: 3px; background: #2A2A2A; } QSlider::handle:horizontal { background: #FFFFFF; width: 14px; margin: -5px 0; border-radius: 7px; } QSlider::sub-page:horizontal { background: #6C9BFF; }"
            )
            slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v/divisor:.2f}"))
            l.addLayout(hl)
            l.addWidget(slider)
            self.sliders[key] = slider
            layout.addWidget(group)

        if not hide_basic:
            add_adv_slider(
                "EMOTION EXAGGERATION",
                "exag",
                0,
                100,
                int(self.settings.get("exag", 0.5) * 100),
            )
            add_adv_slider(
                "CFG WEIGHT", "cfg", 0, 100, int(self.settings.get("cfg", 0.5) * 100)
            )
            add_adv_slider(
                "TEMPERATURE", "temp", 0, 100, int(self.settings.get("temp", 0.8) * 100)
            )
            layout.addWidget(
                QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Sunken)
            )
        add_adv_slider(
            "SPEED MULTIPLIER",
            "speed",
            50,
            200,
            int(self.settings.get("speed", 1.0) * 100),
        )
        add_adv_slider(
            "MIN-P", "min_p", 0, 100, int(self.settings.get("min_p", 0.05) * 100)
        )
        add_adv_slider(
            "TOP-P", "top_p", 0, 100, int(self.settings.get("top_p", 1.0) * 100)
        )
        add_adv_slider(
            "REPETITION PENALTY",
            "rep_pen",
            100,
            200,
            int(self.settings.get("rep_pen", 1.2) * 100),
        )
        seed_group = QWidget()
        sl = QVBoxLayout(seed_group)
        sl.setContentsMargins(0, 0, 0, 0)
        seed_lbl = QLabel("SEED (0 FOR RANDOM)")
        seed_lbl.setStyleSheet("color: #737373; font-size: 11px; font-weight: bold;")
        self.seed_input = QLineEdit(str(self.settings.get("seed", 0)))
        self.seed_input.setValidator(QIntValidator(0, 999999999, self))
        self.seed_input.setStyleSheet(
            "QLineEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; }"
        )
        sl.addWidget(seed_lbl)
        sl.addWidget(self.seed_input)
        layout.addWidget(seed_group)
        layout.addStretch()
        if is_global:
            self.apply_all_btn = QPushButton("OVERWRITE ALL LINES")
            self.apply_all_btn.setStyleSheet(
                "QPushButton { background-color: #F5A524; color: #000000; font-weight: bold; padding: 10px; border-radius: 4px; border: none; margin-bottom: 10px; }"
            )
            self.apply_all_btn.clicked.connect(self.set_apply_to_all)
            layout.addWidget(self.apply_all_btn)
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #2A2A2A; }"
        )
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton("SAVE SETTINGS")
        apply_btn.setStyleSheet(
            "QPushButton { background-color: #6C9BFF; color: #0B1220; font-weight: 900; padding: 10px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #8AAFFF; }"
        )
        apply_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def set_apply_to_all(self):
        self.apply_to_all = True
        self.save_and_close()

    def save_and_close(self):
        for key, slider in self.sliders.items():
            self.settings[key] = slider.value() / 100.0
        self.settings["seed"] = (
            int(self.seed_input.text()) if self.seed_input.text() else 0
        )
        self.accept()

    def get_settings(self):
        return self.settings

class CustomAudioPlayer(QFrame):
    def __init__(self):
        super().__init__()
        self.current_path = None
        self.setStyleSheet(
            "QFrame { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; margin-top: 10px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet(
            "QPushButton { background-color: #2A2A2A; color: #FFFFFF; border-radius: 18px; font-size: 16px; border: none; } QPushButton:hover { background-color: #3A3A3A; } QPushButton:disabled { color: #555555; background-color: #151515; }"
        )
        self.play_btn.clicked.connect(self.toggle_playback)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal { border-radius: 2px; height: 3px; background: #2A2A2A; } QSlider::handle:horizontal { background: #FFFFFF; width: 10px; margin: -3px 0; border-radius: 5px; } QSlider::sub-page:horizontal { background: #6C9BFF; }"
        )
        self.slider.sliderMoved.connect(self.set_position)
        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet(
            "color: #737373; font-size: 12px; font-weight: bold; border: none; font-family: monospace;"
        )
        self.export_btn = QPushButton("📤 EXPORT")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #2ECC8F; border-radius: 4px; font-size: 11px; font-weight: bold; padding: 10px 15px; border: none; } QPushButton:hover { background-color: #252525; } QPushButton:disabled { color: #555555; background-color: #151515; }"
        )
        self.export_btn.clicked.connect(self.export_audio)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.slider)
        layout.addWidget(self.time_lbl)
        layout.addStretch()
        layout.addWidget(self.export_btn)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.update_state)

    def set_audio(self, path):
        self.current_path = path
        if path and os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.play_btn.setEnabled(True)
            self.slider.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.slider.setValue(0)
        else:
            self.play_btn.setEnabled(False)
            self.slider.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.player.stop()
            self.player.setSource(QUrl())
            self.time_lbl.setText("00:00 / 00:00")

    def toggle_playback(self):
        (
            self.player.pause()
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            else self.player.play()
        )

    def update_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
            self.play_btn.setStyleSheet(
                "QPushButton { background-color: #6C9BFF; color: #0B1220; border-radius: 18px; font-size: 14px; font-weight: 900; border: none; }"
            )
        else:
            self.play_btn.setText("▶")
            self.play_btn.setStyleSheet(
                "QPushButton { background-color: #2A2A2A; color: #FFFFFF; border-radius: 18px; font-size: 16px; border: none; } QPushButton:hover { background-color: #3A3A3A; }"
            )

    def format_time(self, ms):
        s = round(ms / 1000)
        m, s = divmod(s, 60)
        return f"{m:02}:{s:02}"

    def update_position(self, p):
        if not self.slider.isSliderDown():
            self.slider.setValue(p)
        self.time_lbl.setText(
            f"{self.format_time(p)} / {self.format_time(self.player.duration())}"
        )

    def update_duration(self, d):
        self.slider.setRange(0, d)
        self.time_lbl.setText(f"00:00 / {self.format_time(d)}")

    def set_position(self, p):
        self.player.setPosition(p)

    def export_audio(self):
        if not self.current_path:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Export Lossless Audio",
            "",
            "Original Uncompressed (*.wav);;FLAC Lossless (*.flac);;MP3 High Quality 320kbps (*.mp3)",
        )
        if dest:
            try:
                if dest.endswith(".wav"):
                    shutil.copy(self.current_path, dest)
                else:
                    CREATE_NO_WINDOW = 0x08000000
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", self.current_path, "-b:a", "320k", dest],
                        creationflags=CREATE_NO_WINDOW,
                    )
            except FileNotFoundError:
                print("FFmpeg not installed. Exporting as WAV.")
                shutil.copy(
                    self.current_path,
                    dest.replace(".flac", ".wav").replace(".mp3", ".wav"),
                )

class LiveTerminal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SYSTEM TERMINAL - CHATTERBOX STUDIO")
        self.resize(750, 450)
        self.setStyleSheet("background-color: #0B0E14; border: 1px solid #2A2A2A;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)

        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #050505;
                color: #E2E8F0;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #1A1A1A;
                padding: 10px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.text_area)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.clear_btn = QPushButton("🗑 CLEAR CONSOLE")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton { background-color: #1A1A1A; color: #737373; font-weight: bold; padding: 8px 15px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #2A2A2A; color: #FFFFFF; }
        """)
        self.clear_btn.clicked.connect(self.text_area.clear)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

    def append_log(self, level, message):

        color = "#E2E8F0"
        if level in ["ERROR", "CRITICAL"]:
            color = "#F1594F"
        elif level == "WARNING":
            color = "#F5A524"
        elif level == "INFO":
            color = "#6C9BFF"

        html_msg = f'<span style="color: {color};">{message}</span><br>'

        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_area.setTextCursor(cursor)
        self.text_area.insertHtml(html_msg)
        self.text_area.ensureCursorVisible()

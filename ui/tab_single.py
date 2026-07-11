import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QSlider,
    QComboBox,
    QPushButton,
    QFrame,
    QFileDialog,
    QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from voice_manager import get_saved_voices
from ui.components import CustomAudioPlayer, SettingsDialog, GenerationProgressBar
from ui.workers import GenerationWorker

class SingleGenerationUI(QWidget):
    def __init__(self):
        super().__init__()
        self.uploaded_ref_path = None
        self.adv_settings = {
            "speed": 1.0,
            "min_p": 0.05,
            "top_p": 1.0,
            "rep_pen": 1.2,
            "seed": 0,
        }

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        header = QLabel("SINGLE VOICE GENERATION")
        header.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: 900; letter-spacing: 2px;"
        )
        main_layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        main_layout.addLayout(content_layout)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter your script here...")
        self.text_input.setStyleSheet(
            "QTextEdit { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; color: #E2E8F0; padding: 15px; font-size: 15px; line-height: 1.5; } QTextEdit:focus { border: 1px solid #555555; }"
        )
        content_layout.addWidget(self.text_input, stretch=6)

        settings_frame = QFrame()
        settings_frame.setStyleSheet(
            "QFrame { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; }"
        )
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(25, 25, 25, 25)

        p_lbl = QLabel("PROJECT NAME")
        p_lbl.setStyleSheet("color: #F5A524; font-size: 11px; font-weight: bold;")
        settings_layout.addWidget(p_lbl)

        self.proj_input = QLineEdit()
        self.proj_input.setPlaceholderText("e.g. ad_campaign_01")
        self.proj_input.setStyleSheet(
            "QLineEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; font-weight: bold; }"
        )
        settings_layout.addWidget(self.proj_input)
        settings_layout.addSpacing(15)

        lbl1 = QLabel("REFERENCE VOICE")
        lbl1.setStyleSheet("color: #737373; font-size: 11px; font-weight: bold;")
        settings_layout.addWidget(lbl1)

        self.voice_combo = QComboBox()
        self.voice_combo.addItems(get_saved_voices())
        self.voice_combo.setStyleSheet(
            "QComboBox { background-color: #050505; border: 1px solid #2A2A2A; border-radius: 4px; color: #FFFFFF; padding: 10px; font-size: 13px; }"
        )
        settings_layout.addWidget(self.voice_combo)

        upload_layout = QHBoxLayout()
        self.upload_btn = QPushButton("UPLOAD CUSTOM")
        self.upload_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #E2E8F0; border: 1px solid #333333; border-radius: 4px; padding: 8px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #252525; }"
        )
        self.upload_btn.clicked.connect(self.browse_reference_file)

        self.upload_lbl = QLabel("No file selected")
        self.upload_lbl.setStyleSheet("color: #737373; font-size: 11px; border: none;")

        upload_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(self.upload_lbl, stretch=1)
        settings_layout.addLayout(upload_layout)
        settings_layout.addSpacing(15)

        self.sliders = {}

        def add_slider(name, key, default_val):
            group = QWidget()
            l = QVBoxLayout(group)
            l.setContentsMargins(0, 0, 0, 0)
            hl = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setStyleSheet("color: #737373; font-size: 11px; font-weight: bold;")
            val_lbl = QLabel(f"{default_val/100:.2f}")
            val_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
            hl.addWidget(lbl)
            hl.addStretch()
            hl.addWidget(val_lbl)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(default_val)
            slider.setStyleSheet(
                "QSlider::groove:horizontal { border-radius: 2px; height: 3px; background: #2A2A2A; } QSlider::handle:horizontal { background: #FFFFFF; width: 14px; margin: -5px 0; border-radius: 7px; } QSlider::sub-page:horizontal { background: #737373; }"
            )
            slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v/100:.2f}"))
            l.addLayout(hl)
            l.addWidget(slider)
            self.sliders[key] = slider
            return group

        settings_layout.addWidget(add_slider("EMOTION EXAGGERATION", "exag", 50))
        settings_layout.addWidget(add_slider("CFG WEIGHT", "cfg", 50))
        settings_layout.addWidget(add_slider("TEMPERATURE", "temp", 80))

        settings_layout.addSpacing(10)
        self.adv_btn = QPushButton("⚙️ ADVANCED SETTINGS")
        self.adv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #6C9BFF; border: 1px solid #2A2A2A; border-radius: 4px; padding: 10px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #151A22; }"
        )
        self.adv_btn.clicked.connect(self.open_advanced_settings)
        settings_layout.addWidget(self.adv_btn)
        settings_layout.addStretch()
        content_layout.addWidget(settings_frame, stretch=4)

        self.status_lbl = QLabel("READY")
        self.status_lbl.setStyleSheet(
            "color: #2ECC8F; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        main_layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        self.gen_btn = QPushButton("INITIALIZE GENERATION")
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #000000; font-weight: 900; font-size: 13px; letter-spacing: 1.5px; border-radius: 4px; padding: 16px; border: none; } QPushButton:hover { background-color: #E5E5E5; } QPushButton:disabled { background-color: #2A2A2A; color: #737373; }"
        )
        self.gen_btn.clicked.connect(self.start_generation)
        main_layout.addWidget(self.gen_btn)

        self.progress_bar = GenerationProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.audio_player = CustomAudioPlayer()
        main_layout.addWidget(self.audio_player)

    def browse_reference_file(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select Audio", "", "Audio (*.wav *.mp3)"
        )
        if p:
            self.uploaded_ref_path = p
            self.upload_lbl.setText(os.path.basename(p)[:15] + "...")
            self.upload_lbl.setStyleSheet("color: #E2E8F0; font-size: 11px;")

    def refresh_voices(self):
        self.voice_combo.clear()
        self.voice_combo.addItems(get_saved_voices())

    def open_advanced_settings(self):
        dialog = SettingsDialog(self.adv_settings, hide_basic=True, parent=self)
        if dialog.exec():
            self.adv_settings = dialog.get_settings()
            self.status_lbl.setText("ADVANCED SETTINGS SAVED")
            self.status_lbl.setStyleSheet(
                "color: #F5A524; font-size: 11px; font-weight: bold;"
            )

    def start_generation(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            return

        text = self.text_input.toPlainText().strip()
        proj_name = self.proj_input.text().strip()

        if not proj_name:
            self.status_lbl.setText("ERROR: PROJECT NAME IS REQUIRED")
            self.status_lbl.setStyleSheet(
                "color: #F1594F; font-size: 11px; font-weight: bold;"
            )
            return

        if not text:
            return

        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("GENERATING AUDIO...")
        self.status_lbl.setText("PROCESSING NEURAL NETWORK...")
        self.status_lbl.setStyleSheet(
            "color: #F5A524; font-size: 11px; font-weight: bold;"
        )
        self.audio_player.set_audio(None)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        settings = {
            "voice_name": self.voice_combo.currentText(),
            "ref_audio": self.uploaded_ref_path,
            "exag": self.sliders["exag"].value() / 100.0,
            "cfg": self.sliders["cfg"].value() / 100.0,
            "temp": self.sliders["temp"].value() / 100.0,
        }
        settings.update(self.adv_settings)

        self.worker = GenerationWorker(text, settings, proj_name)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_success(self, path):
        self.progress_bar.setValue(100)
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("INITIALIZE GENERATION")
        self.status_lbl.setText(f"SUCCESS: SAVED AT {os.path.basename(path)}")
        self.status_lbl.setStyleSheet(
            "color: #2ECC8F; font-size: 11px; font-weight: bold;"
        )
        self.audio_player.set_audio(path)
        QTimer.singleShot(1500, self.progress_bar.hide)

    def on_error(self, err):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("TRY AGAIN")
        self.status_lbl.setText("ERROR: PROCESS FAILED")
        self.status_lbl.setStyleSheet(
            "color: #F1594F; font-size: 11px; font-weight: bold;"
        )
        self.progress_bar.hide()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Generation Error")
        msg.setText("The generation process could not be completed.")
        msg.setInformativeText("Click 'Show Details' to view the complete error log.")

        msg.setDetailedText(str(err))

        msg.setStyleSheet("""
            QMessageBox { background-color: #0B0E14; border: 1px solid #2A2A2A; }
            QLabel { color: #E2E8F0; font-size: 13px; }
            QPushButton {
                background-color: #1A1A1A;
                color: #FFFFFF;
                padding: 6px 15px;
                border-radius: 4px;
                border: 1px solid #333333;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2A2A2A; }
            QTextEdit {
                background-color: #050505;
                color: #F1594F;
                border: 1px solid #2A2A2A;
                font-family: Consolas, monospace;
            }
        """)
        msg.exec()

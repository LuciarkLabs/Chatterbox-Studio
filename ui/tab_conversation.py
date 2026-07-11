import os
import json
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QComboBox,
    QPushButton,
    QFrame,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QSpinBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from config import OUTPUTS_DIR
from voice_manager import get_saved_voices
from ui.components import CustomAudioPlayer, SettingsDialog, GenerationProgressBar
from ui.workers import ConversationWorker


class ConversationUI(QWidget):
    def __init__(self):
        super().__init__()
        self.conversation_state = []
        self.editing_index = None
        self.global_settings = {
            "exag": 0.5,
            "cfg": 0.5,
            "temp": 0.8,
            "speed": 1.0,
            "min_p": 0.05,
            "top_p": 1.0,
            "rep_pen": 1.2,
            "seed": 0,
        }

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        header = QLabel("CONVERSATION STUDIO")
        header.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: 900; letter-spacing: 2px;"
        )
        main_layout.addWidget(header)

        top_bar = QHBoxLayout()
        proj_lbl = QLabel("PROJECT FOLDER:")
        proj_lbl.setStyleSheet("color: #F5A524; font-size: 11px; font-weight: bold;")

        self.proj_input = QLineEdit()
        self.proj_input.setPlaceholderText("e.g. documentary_ep1")
        self.proj_input.setFixedWidth(250)
        self.proj_input.setStyleSheet(
            "QLineEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; font-weight: bold; }"
        )

        self.save_btn = QPushButton("💾 SAVE .CBX")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #FFFFFF; font-weight: bold; padding: 10px 20px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #2A2A2A; }"
        )
        self.save_btn.clicked.connect(self.save_project)

        self.load_btn = QPushButton("📂 LOAD .CBX")
        self.load_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #FFFFFF; font-weight: bold; padding: 10px 20px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #2A2A2A; }"
        )
        self.load_btn.clicked.connect(self.load_project)

        top_bar.addWidget(proj_lbl)
        top_bar.addWidget(self.proj_input)
        top_bar.addStretch()
        top_bar.addWidget(self.load_btn)
        top_bar.addWidget(self.save_btn)
        main_layout.addLayout(top_bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["#", "VOICE", "SCRIPT", "STATUS", "ACTIONS"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(4, 250)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; color: #E2E8F0; font-size: 13px; } QHeaderView::section { background-color: #050505; color: #737373; font-weight: bold; font-size: 11px; padding: 10px; border: none; border-bottom: 1px solid #2A2A2A; } QTableWidget::item { padding: 10px 15px; border-bottom: 1px solid #1A1A1A; } QTableWidget::item:selected { background-color: #1A1A1A; }"
        )
        main_layout.addWidget(self.table)

        add_frame = QFrame()
        add_frame.setStyleSheet(
            "QFrame { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; }"
        )
        add_layout = QHBoxLayout(add_frame)

        self.conv_voice_combo = QComboBox()
        self.conv_voice_combo.addItems(get_saved_voices())
        self.conv_voice_combo.setStyleSheet(
            "QComboBox { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; font-weight: bold; }"
        )

        self.conv_text_input = QTextEdit()
        self.conv_text_input.setFixedHeight(45)
        self.conv_text_input.setPlaceholderText("Enter script for this line...")
        self.conv_text_input.setStyleSheet(
            "QTextEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; font-size: 13px; }"
        )

        self.add_btn = QPushButton("ADD LINE ➕")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #000000; font-weight: 900; padding: 12px 20px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #E5E5E5; }"
        )
        self.add_btn.clicked.connect(self.save_or_add_line)

        add_layout.addWidget(self.conv_voice_combo, stretch=1)
        add_layout.addWidget(self.conv_text_input, stretch=4)
        add_layout.addWidget(self.add_btn)
        main_layout.addWidget(add_frame)

        bottom_actions = QHBoxLayout()
        self.status_lbl = QLabel("READY")
        self.status_lbl.setStyleSheet(
            "color: #737373; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        bottom_actions.addWidget(self.status_lbl)
        bottom_actions.addStretch()

        gap_lbl = QLabel("⏱️ GAP (ms):")
        gap_lbl.setStyleSheet("color: #F5A524; font-size: 11px; font-weight: bold;")
        bottom_actions.addWidget(gap_lbl)

        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 5000)
        self.gap_spin.setValue(500)
        self.gap_spin.setSingleStep(100)
        self.gap_spin.setFixedWidth(110)
        self.gap_spin.setStyleSheet("""
            QSpinBox {
                background-color: #050505;
                border: 1px solid #2A2A2A;
                color: #FFFFFF;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 25px;
            }
        """)
        bottom_actions.addWidget(self.gap_spin)

        self.clear_btn = QPushButton("🗑 CLEAR ALL")
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #F1594F; border: 1px solid #331515; padding: 12px 20px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #1A0A0A; }"
        )
        self.clear_btn.clicked.connect(self.clear_all)
        bottom_actions.addWidget(self.clear_btn)

        self.global_settings_btn = QPushButton("⚙️ GLOBAL SETTINGS")
        self.global_settings_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #6C9BFF; border: 1px solid #2A2A2A; padding: 12px 20px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #151A22; }"
        )
        self.global_settings_btn.clicked.connect(self.open_global_settings)
        bottom_actions.addWidget(self.global_settings_btn)

        self.gen_all_btn = QPushButton("SMART MIX & GENERATE")
        self.gen_all_btn.setStyleSheet(
            "QPushButton { background-color: #6C9BFF; color: #0B1220; font-weight: 900; letter-spacing: 1px; padding: 12px 24px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #8AAFFF; } QPushButton:disabled { background-color: #2A2A2A; color: #737373; }"
        )
        self.gen_all_btn.clicked.connect(self.generate_all)
        bottom_actions.addWidget(self.gen_all_btn)

        main_layout.addLayout(bottom_actions)

        self.progress_bar = GenerationProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.audio_player = CustomAudioPlayer()
        main_layout.addWidget(self.audio_player)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.auto_save)
        self.autosave_timer.start(120000)

        self.check_and_load_autosave()

    def auto_save(self):
        if not self.conversation_state:
            return

        proj_name = self.proj_input.text().strip() or "untitled_project"
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        autosave_path = os.path.join(OUTPUTS_DIR, "autosave_recovery.cbx")

        try:
            with open(autosave_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "project_name": proj_name,
                        "global_settings": self.global_settings,
                        "lines": self.conversation_state,
                        "mix_gap_ms": self.gap_spin.value(),
                        "is_autosave": True,
                    },
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

            current_text = self.status_lbl.text()
            current_style = self.status_lbl.styleSheet()

            self.status_lbl.setText("💾 AUTO-SAVED TO RECOVERY FILE")
            self.status_lbl.setStyleSheet(
                "color: #737373; font-size: 11px; font-weight: bold;"
            )

            def restore_status():
                if self.status_lbl.text() == "💾 AUTO-SAVED TO RECOVERY FILE":
                    self.status_lbl.setText(current_text)
                    self.status_lbl.setStyleSheet(current_style)

            QTimer.singleShot(2000, restore_status)
        except:
            pass

    def check_and_load_autosave(self):
        autosave_path = os.path.join(OUTPUTS_DIR, "autosave_recovery.cbx")
        if os.path.exists(autosave_path):
            try:
                with open(autosave_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.proj_input.setText(data.get("project_name", ""))
                self.global_settings = data.get("global_settings", self.global_settings)
                self.conversation_state = data.get("lines", [])
                self.gap_spin.setValue(data.get("mix_gap_ms", 500))
                self.render_table()
                self.status_lbl.setText("🔄 RECOVERED UNSAVED SESSION")
                self.status_lbl.setStyleSheet(
                    "color: #F5A524; font-size: 11px; font-weight: bold;"
                )
            except:
                pass

    def refresh_voices(self):
        self.conv_voice_combo.clear()
        self.conv_voice_combo.addItems(get_saved_voices())

    def clear_autosave(self):

        autosave_path = os.path.join(OUTPUTS_DIR, "autosave_recovery.cbx")
        if os.path.exists(autosave_path):
            try:
                os.remove(autosave_path)
            except:
                pass

    def clear_all(self):
        self.conversation_state = []
        self.render_table()
        self.audio_player.set_audio(None)

        self.clear_autosave()
        self.status_lbl.setText("PROJECT CLEARED")

    def save_project(self):
        if not self.conversation_state:
            self.status_lbl.setText("ERROR: NOTHING TO SAVE")
            self.status_lbl.setStyleSheet(
                "color: #F1594F; font-size: 11px; font-weight: bold;"
            )
            return False

        proj_name = self.proj_input.text().strip() or "untitled_project"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", f"{proj_name}.cbx", "Chatterbox Project Files (*.cbx)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "project_name": proj_name,
                            "global_settings": self.global_settings,
                            "lines": self.conversation_state,
                            "mix_gap_ms": self.gap_spin.value(),
                        },
                        f,
                        indent=4,
                        ensure_ascii=False,
                    )
                self.status_lbl.setText("PROJECT SAVED SUCCESSFULLY")
                self.status_lbl.setStyleSheet(
                    "color: #2ECC8F; font-size: 11px; font-weight: bold;"
                )
                return True
            except Exception as e:
                self.status_lbl.setText(f"ERROR SAVING: {str(e)}")
                self.status_lbl.setStyleSheet(
                    "color: #F1594F; font-size: 11px; font-weight: bold;"
                )
                return False
        return False

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Chatterbox Project Files (*.cbx)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.proj_input.setText(data.get("project_name", ""))
                self.global_settings = data.get("global_settings", self.global_settings)
                self.conversation_state = data.get("lines", [])
                self.gap_spin.setValue(data.get("mix_gap_ms", 500))
                self.render_table()
                self.status_lbl.setText("PROJECT LOADED SUCCESSFULLY")
                self.status_lbl.setStyleSheet(
                    "color: #2ECC8F; font-size: 11px; font-weight: bold;"
                )
            except Exception as e:
                self.status_lbl.setText(f"ERROR LOADING: {str(e)}")
                self.status_lbl.setStyleSheet(
                    "color: #F1594F; font-size: 11px; font-weight: bold;"
                )

    def render_table(self):
        self.table.setRowCount(0)
        for i, row in enumerate(self.conversation_state):
            self.table.insertRow(i)

            self.table.setRowHeight(i, 45)

            i_num = QTableWidgetItem(str(i + 1))
            i_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            i_num.setForeground(QColor("#737373"))

            i_voice = QTableWidgetItem(row["voice"].upper())
            i_voice.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            i_txt = QTableWidgetItem(
                row["text"] if len(row["text"]) <= 50 else row["text"][:50] + "..."
            )

            i_status = QTableWidgetItem(row["status"])
            i_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            i_status.setForeground(QColor(row["color"]))

            self.table.setItem(i, 0, i_num)
            self.table.setItem(i, 1, i_voice)
            self.table.setItem(i, 2, i_txt)
            self.table.setItem(i, 3, i_status)
            self.table.setCellWidget(i, 4, self.create_action_widget(i))
        self.table.scrollToBottom()

    def create_action_widget(self, index):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(5, 0, 5, 0)
        l.setSpacing(6)

        btn_style = """
            QPushButton {
                background: transparent;
                font-size: 15px;
                border: none;
                min-width: 28px;
                min-height: 28px;
                max-width: 28px;
                max-height: 28px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #2A2A2A;
            }
        """

        up_b = QPushButton("⬆️")
        up_b.setStyleSheet(btn_style)
        up_b.clicked.connect(lambda: self.move_row(index, -1))

        down_b = QPushButton("⬇️")
        down_b.setStyleSheet(btn_style)
        down_b.clicked.connect(lambda: self.move_row(index, 1))

        play_b = QPushButton("▶️")
        play_b.setStyleSheet(btn_style)
        play_b.clicked.connect(lambda: self.play_line(index))

        edit_b = QPushButton("✏️")
        edit_b.setStyleSheet(btn_style)
        edit_b.clicked.connect(lambda: self.edit_line(index))

        set_b = QPushButton("⚙️")
        set_b.setStyleSheet(btn_style)
        set_b.clicked.connect(lambda: self.open_line_settings(index))

        regen_b = QPushButton("🔄")
        regen_b.setStyleSheet(btn_style)
        regen_b.clicked.connect(lambda: self.regenerate_line(index))

        del_b = QPushButton("🗑️")
        del_b.setStyleSheet(btn_style)
        del_b.clicked.connect(lambda: self.delete_line(index))

        l.addWidget(up_b)
        l.addWidget(down_b)
        l.addWidget(play_b)
        l.addWidget(edit_b)
        l.addWidget(set_b)
        l.addWidget(regen_b)
        l.addWidget(del_b)
        return w

    def move_row(self, index, d):
        if 0 <= index + d < len(self.conversation_state):
            self.conversation_state[index], self.conversation_state[index + d] = (
                self.conversation_state[index + d],
                self.conversation_state[index],
            )
            self.render_table()

    def play_line(self, index):
        path = self.conversation_state[index].get("path")
        if path and os.path.exists(path):
            self.audio_player.set_audio(path)
            self.audio_player.toggle_playback()
        else:
            self.status_lbl.setText("AUDIO NOT GENERATED YET")

    def edit_line(self, index):
        self.editing_index = index
        row = self.conversation_state[index]
        self.conv_voice_combo.setCurrentText(row["voice"])
        self.conv_text_input.setPlainText(row["text"])
        self.add_btn.setText("UPDATE LINE 💾")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #F5A524; color: #000000; font-weight: 900; padding: 12px 20px; border-radius: 4px; border: none; }"
        )

    def open_line_settings(self, index):
        dialog = SettingsDialog(self.conversation_state[index]["settings"], parent=self)
        if dialog.exec():
            self.conversation_state[index]["settings"] = dialog.get_settings()
            self.conversation_state[index]["path"] = None
            self.conversation_state[index]["status"] = "⏳ PENDING"
            self.conversation_state[index]["color"] = "#737373"
            self.render_table()

    def regenerate_line(self, index):
        self.conversation_state[index]["path"] = None
        self.conversation_state[index]["status"] = "⏳ PENDING"
        self.conversation_state[index]["color"] = "#737373"
        self.render_table()
        self.generate_all()

    def delete_line(self, index):
        del self.conversation_state[index]
        if self.editing_index == index:
            self.reset_edit_mode()
        self.render_table()

    def open_global_settings(self):
        dialog = SettingsDialog(self.global_settings, is_global=True, parent=self)
        if dialog.exec():
            self.global_settings = dialog.get_settings()
            if dialog.apply_to_all:
                for row in self.conversation_state:
                    row["settings"] = self.global_settings.copy()
                    row["path"] = None
                    row["status"] = "⏳ PENDING"
                    row["color"] = "#737373"
                self.render_table()
                self.status_lbl.setText("GLOBAL SETTINGS APPLIED TO ALL LINES")

    def save_or_add_line(self):
        voice = self.conv_voice_combo.currentText()
        text = self.conv_text_input.toPlainText().strip()
        if not text:
            return

        if self.editing_index is not None:
            self.conversation_state[self.editing_index].update(
                {
                    "voice": voice,
                    "text": text,
                    "path": None,
                    "status": "⏳ PENDING",
                    "color": "#737373",
                }
            )
            self.reset_edit_mode()
        else:
            self.conversation_state.append(
                {
                    "voice": voice,
                    "text": text,
                    "path": None,
                    "status": "⏳ PENDING",
                    "color": "#737373",
                    "settings": self.global_settings.copy(),
                }
            )

        self.conv_text_input.clear()
        self.render_table()

    def reset_edit_mode(self):
        self.editing_index = None
        self.add_btn.setText("ADD LINE ➕")
        self.add_btn.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #000000; font-weight: 900; padding: 12px 20px; border-radius: 4px; border: none; } QPushButton:hover { background-color: #E5E5E5; }"
        )

    def generate_all(self):
        if not self.conversation_state or (
            hasattr(self, "worker") and self.worker.isRunning()
        ):
            return

        proj_name = self.proj_input.text().strip()
        if not proj_name:
            self.status_lbl.setText("ERROR: PROJECT FOLDER NAME REQUIRED")
            self.status_lbl.setStyleSheet(
                "color: #F1594F; font-size: 11px; font-weight: bold;"
            )
            return

        self.gen_all_btn.setEnabled(False)
        self.gen_all_btn.setText("PROCESSING...")
        self.status_lbl.setText("MIXING ENGINES ENGAGED...")
        self.status_lbl.setStyleSheet(
            "color: #F5A524; font-size: 11px; font-weight: bold;"
        )
        self.audio_player.set_audio(None)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.worker = ConversationWorker(
            self.conversation_state, proj_name, self.gap_spin.value()
        )
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_status(self, r, txt, col):
        self.conversation_state[r]["status"] = txt
        self.conversation_state[r]["color"] = col
        item = self.table.item(r, 3)
        if item:
            item.setText(txt)
            item.setForeground(QColor(col))
            self.table.scrollToItem(item)

        total_lines = len(self.conversation_state)
        completed = sum(
            1 for row in self.conversation_state if row.get("status") == "✅ DONE"
        )
        if total_lines > 0:
            self.progress_bar.setValue(int((completed / total_lines) * 100))

    def on_success(self, path):
        self.progress_bar.setValue(100)
        self.gen_all_btn.setEnabled(True)
        self.gen_all_btn.setText("SMART MIX & GENERATE")
        self.status_lbl.setText(f"SUCCESS: MIXED AUDIO READY IN PROJECT FOLDER")
        self.status_lbl.setStyleSheet(
            "color: #2ECC8F; font-size: 11px; font-weight: bold;"
        )
        self.audio_player.set_audio(path)
        QTimer.singleShot(1500, self.progress_bar.hide)

    def on_error(self, err):
        self.gen_all_btn.setEnabled(True)
        self.gen_all_btn.setText("TRY AGAIN")
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

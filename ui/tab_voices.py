import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
)
from PySide6.QtCore import Qt, QSize

from voice_manager import (
    save_voice,
    get_saved_voices,
    delete_voice,
    load_voice_audio,
    rename_voice,
    get_favorites,
    toggle_favorite,
)
from ui.components import CustomAudioPlayer

class VoiceManagerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.uploaded_path = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        header = QLabel("VOICE MANAGER STUDIO")
        header.setStyleSheet(
            "color: #FFFFFF; font-size: 16px; font-weight: 900; letter-spacing: 2px;"
        )
        main_layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        main_layout.addLayout(content_layout)

        add_frame = QFrame()
        add_frame.setStyleSheet(
            "QFrame { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; }"
        )
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(25, 25, 25, 25)
        add_layout.setSpacing(20)

        lbl1 = QLabel("CREATE NEW VOICE CLONE")
        lbl1.setStyleSheet(
            "color: #6C9BFF; font-size: 13px; font-weight: bold; letter-spacing: 1px;"
        )
        add_layout.addWidget(lbl1)

        name_lbl = QLabel("VOICE NAME")
        name_lbl.setStyleSheet("color: #737373; font-size: 11px; font-weight: bold;")
        add_layout.addWidget(name_lbl)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. narrator_01")
        self.name_input.setStyleSheet(
            "QLineEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 12px; border-radius: 4px; font-size: 13px; }"
        )
        add_layout.addWidget(self.name_input)

        upload_layout = QHBoxLayout()
        self.upload_btn = QPushButton("UPLOAD REFERENCE AUDIO")
        self.upload_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #E2E8F0; border: 1px solid #333333; border-radius: 4px; padding: 10px; font-size: 11px; font-weight: bold; } QPushButton:hover { background-color: #252525; }"
        )
        self.upload_btn.clicked.connect(self.browse_file)

        self.file_lbl = QLabel("No file selected")
        self.file_lbl.setStyleSheet("color: #737373; font-size: 11px;")

        upload_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(self.file_lbl, stretch=1)
        add_layout.addLayout(upload_layout)

        self.upload_player = CustomAudioPlayer()
        add_layout.addWidget(self.upload_player)

        add_layout.addStretch()

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_layout.addWidget(self.status_lbl)

        self.save_btn = QPushButton("💾 SAVE TO LIBRARY")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #2ECC8F; color: #0B1220; font-weight: 900; letter-spacing: 1px; padding: 15px; border-radius: 4px; border: none; font-size: 13px; } QPushButton:hover { background-color: #3BEDA9; }"
        )
        self.save_btn.clicked.connect(self.commit_save_voice)
        add_layout.addWidget(self.save_btn)

        content_layout.addWidget(add_frame, stretch=1)

        list_frame = QFrame()
        list_frame.setStyleSheet(
            "QFrame { background-color: #0E0E0E; border: 1px solid #2A2A2A; border-radius: 4px; }"
        )
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(25, 25, 25, 25)
        list_layout.setSpacing(15)

        lbl2 = QLabel("VOICE LIBRARY")
        lbl2.setStyleSheet(
            "color: #F5A524; font-size: 13px; font-weight: bold; letter-spacing: 1px;"
        )
        list_layout.addWidget(lbl2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search voices...")
        self.search_input.setStyleSheet(
            "QLineEdit { background-color: #050505; border: 1px solid #2A2A2A; color: #FFFFFF; padding: 10px; border-radius: 4px; font-size: 13px; }"
        )
        self.search_input.textChanged.connect(self.refresh_voices)
        list_layout.addWidget(self.search_input)

        self.voice_list = QListWidget()
        self.voice_list.setStyleSheet("""
            QListWidget { background-color: #050505; border: 1px solid #2A2A2A; border-radius: 4px; padding: 5px; outline: none; }
            QListWidget::item { border-bottom: 1px solid #1A1A1A; }
            QListWidget::item:selected { background-color: #1A1A1A; }
        """)
        self.voice_list.itemSelectionChanged.connect(self.on_voice_selected)
        list_layout.addWidget(self.voice_list)

        self.library_player = CustomAudioPlayer()
        list_layout.addWidget(self.library_player)

        actions_layout = QHBoxLayout()
        self.rename_btn = QPushButton("✏️ RENAME")
        self.rename_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #FFFFFF; border: 1px solid #333333; padding: 12px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #252525; }"
        )
        self.rename_btn.clicked.connect(self.rename_selected)

        self.del_btn = QPushButton("🗑️ DELETE")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #F1594F; border: 1px solid #331515; padding: 12px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #1A0A0A; }"
        )
        self.del_btn.clicked.connect(self.delete_selected)

        actions_layout.addWidget(self.rename_btn)
        actions_layout.addWidget(self.del_btn)
        list_layout.addLayout(actions_layout)

        content_layout.addWidget(list_frame, stretch=1)
        self.refresh_voices()

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Audio", "", "Audio (*.wav *.mp3 *.flac *.m4a *.ogg)"
        )
        if path:
            self.uploaded_path = path
            self.file_lbl.setText(os.path.basename(path)[:20] + "...")
            self.upload_player.set_audio(path)

    def commit_save_voice(self):
        name = self.name_input.text().strip()
        if not name:
            self.show_status("ERROR: VOICE NAME REQUIRED", "#F1594F")
            return
        if not self.uploaded_path:
            self.show_status("ERROR: NO AUDIO SELECTED", "#F1594F")
            return

        success, msg = save_voice(name, self.uploaded_path)
        if success:
            self.show_status(f"SUCCESS: VOICE '{name.upper()}' SAVED", "#2ECC8F")
            self.name_input.clear()
            self.uploaded_path = None
            self.file_lbl.setText("No file selected")
            self.upload_player.set_audio(None)
            self.refresh_voices()
            self.sync_all_tabs()
        else:
            self.show_status(f"ERROR: {msg}".upper(), "#F1594F")

    def on_voice_selected(self):
        items = self.voice_list.selectedItems()
        if items:
            name = items[0].data(Qt.ItemDataRole.UserRole)
            path = load_voice_audio(name)
            self.library_player.set_audio(path)
        else:
            self.library_player.set_audio(None)

    def rename_selected(self):
        items = self.voice_list.selectedItems()
        if not items:
            return
        old_name = items[0].data(Qt.ItemDataRole.UserRole)

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Voice",
            "Enter new voice name:",
            QLineEdit.EchoMode.Normal,
            old_name,
        )
        if ok and new_name and new_name != old_name:
            self.library_player.set_audio(None)

            success, msg = rename_voice(old_name, new_name)
            if success:
                self.show_status(f"RENAMED '{old_name}' TO '{new_name}'", "#6C9BFF")
                self.refresh_voices()
                self.sync_all_tabs()
            else:
                self.show_status(f"ERROR: {msg}".upper(), "#F1594F")
                self.on_voice_selected()

    def delete_selected(self):
        items = self.voice_list.selectedItems()
        if not items:
            return
        name = items[0].data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the voice '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.library_player.set_audio(None)

            if delete_voice(name):
                self.show_status(f"VOICE '{name}' DELETED", "#F5A524")
                self.refresh_voices()
                self.sync_all_tabs()
            else:
                self.show_status("ERROR: COULD NOT DELETE VOICE", "#F1594F")
                self.on_voice_selected()

    def sync_all_tabs(self):
        window = self.window()
        if hasattr(window, "tab_single"):
            window.tab_single.refresh_voices()
        if hasattr(window, "tab_conv"):
            window.tab_conv.refresh_voices()

    def show_status(self, msg, color):
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;"
        )

    def do_toggle_fav(self, name):

        toggle_favorite(name)
        self.refresh_voices()
        self.sync_all_tabs()

    def refresh_voices(self):

        self.voice_list.clear()
        query = self.search_input.text().strip().lower()
        all_voices = get_saved_voices()
        favs = get_favorites()

        for name in all_voices:
            if query and query not in name.lower():
                continue

            item = QListWidgetItem(self.voice_list)
            item.setSizeHint(QSize(0, 45))
            item.setData(
                Qt.ItemDataRole.UserRole, name
            )

            w = QWidget()
            w.setStyleSheet("background: transparent;")
            l = QHBoxLayout(w)
            l.setContentsMargins(15, 0, 15, 0)

            is_fav = name in favs
            name_color = "#6C9BFF" if is_fav else "#E2E8F0"

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(
                f"color: {name_color}; font-size: 13px; font-weight: bold;"
            )

            star_btn = QPushButton("⭐" if is_fav else "☆")
            star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            star_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    font-size: 16px;
                    color: {'#F5A524' if is_fav else '#737373'};
                    font-family: "Segoe UI Emoji", "Apple Color Emoji", sans-serif;
                }}
                QPushButton:hover {{ color: #F5A524; }}
            """)

            star_btn.clicked.connect(lambda checked, n=name: self.do_toggle_fav(n))

            l.addWidget(name_lbl)
            l.addStretch()
            l.addWidget(star_btn)

            self.voice_list.setItemWidget(item, w)

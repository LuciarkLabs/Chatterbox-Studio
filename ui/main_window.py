import os
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QStackedWidget,
    QDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

from config import OUTPUTS_DIR
from ui.tab_single import SingleGenerationUI
from ui.tab_conversation import ConversationUI
from ui.tab_voices import VoiceManagerUI
from ui.components import ConsoleInterceptor, HardwareMonitorWidget, LiveTerminal
from logger import qt_handler, get_logger

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Chatterbox Studio")
        self.setFixedSize(350, 250)
        self.setStyleSheet(
            "QDialog { background-color: #0B0E14; border: 1px solid #2A2A2A; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("C H A T T E R B O X")
        logo.setStyleSheet(
            "color: #FFFFFF; font-size: 20px; font-weight: 900; letter-spacing: 4px; margin-bottom: 5px;"
        )
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        ver = QLabel("STUDIO EDITION • VERSION 1.0.0")
        ver.setStyleSheet(
            "color: #6C9BFF; font-size: 10px; font-weight: bold; letter-spacing: 1px; margin-bottom: 20px;"
        )
        layout.addWidget(ver, alignment=Qt.AlignmentFlag.AlignCenter)

        dev = QLabel("Created by\nL U C I A R K   L A B S")
        dev.setStyleSheet(
            "color: #E2E8F0; font-size: 13px; font-weight: normal; line-height: 1.5;"
        )
        dev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dev, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        git_btn = QPushButton("GitHub • LuciarkLabs")
        git_btn.setStyleSheet(
            "QPushButton { background-color: #1A1A1A; color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 4px; border: none; font-size: 11px; } QPushButton:hover { background-color: #2A2A2A; }"
        )
        git_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        github_url = "https://github.com/LuciarkLabs/Chatterbox-Studio"
        git_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(github_url)))

        layout.addWidget(git_btn)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chatterbox Studio")
        self.resize(1150, 750)
        self.setStyleSheet("QMainWindow { background-color: #050505; }")

        self.console_interceptor = ConsoleInterceptor()
        self.console_interceptor.progress_updated.connect(self.update_progress)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(
            "QFrame { background-color: #080808; border-right: 1px solid #1A1A1A; }"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(15)

        logo = QLabel("C H A T T E R B O X")
        logo.setStyleSheet(
            "color: #FFFFFF; font-size: 15px; font-weight: 900; letter-spacing: 3px; border: none; margin-bottom: 20px;"
        )
        sidebar_layout.addWidget(logo)

        self.live_terminal = LiveTerminal(self)

        qt_handler.emitter.new_log.connect(self.live_terminal.append_log)

        logger = get_logger()
        logger.info("Chatterbox Studio Initialized Successfully.")
        logger.info("System Engine: Ready.")

        self.nav_btns = []

        def create_nav_btn(text, index):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 12px 15px; color: #737373; font-weight: bold; font-size: 12px; letter-spacing: 1px; border: none; border-radius: 4px; background: transparent; } QPushButton:hover { color: #FFFFFF; background-color: #111111; } QPushButton:checked { color: #FFFFFF; background-color: #1A1A1A; border-left: 3px solid #6C9BFF; border-radius: 0px; }"
            )
            btn.clicked.connect(lambda: self.switch_tab(index))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
            return btn

        self.btn_single = create_nav_btn("SINGLE GENERATION", 0)
        self.btn_conv = create_nav_btn("CONVERSATION STUDIO", 1)
        self.btn_voices = create_nav_btn("VOICE MANAGER", 2)

        self.btn_open_folder = QPushButton("📂 OPEN OUTPUTS")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.setStyleSheet(
            "QPushButton { text-align: left; padding: 12px 15px; color: #2ECC8F; font-weight: bold; font-size: 11px; letter-spacing: 1px; border: 1px solid #1A1A1A; border-radius: 4px; background-color: transparent; margin-top: 15px; } QPushButton:hover { background-color: #1A1A1A; }"
        )
        self.btn_open_folder.clicked.connect(lambda: os.startfile(OUTPUTS_DIR))
        sidebar_layout.addWidget(self.btn_open_folder)

        self.terminal_btn = QPushButton("🖥️ LIVE LOGS")
        self.terminal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.terminal_btn.setStyleSheet("""
            QPushButton { background-color: #1A1A1A; color: #FFFFFF; font-weight: bold; padding: 12px; border-radius: 4px; border: 1px solid #333333; text-align: left; padding-left: 15px; margin-top: 10px;}
            QPushButton:hover { background-color: #2A2A2A; border: 1px solid #6C9BFF; }
        """)
        self.terminal_btn.clicked.connect(self.live_terminal.show)
        sidebar_layout.addWidget(
            self.terminal_btn
        )

        sidebar_layout.addStretch()

        about_layout = QHBoxLayout()
        self.about_btn = QPushButton("ℹ️ ABOUT")
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.setStyleSheet(
            "QPushButton { color: #737373; font-weight: bold; font-size: 10px; background: transparent; border: none; text-align: left; } QPushButton:hover { color: #FFFFFF; }"
        )
        self.about_btn.clicked.connect(self.show_about)
        about_layout.addWidget(self.about_btn)
        about_layout.addStretch()
        sidebar_layout.addLayout(about_layout)

        self.hw_monitor = HardwareMonitorWidget()
        sidebar_layout.addWidget(self.hw_monitor)

        self.stacked_widget = QStackedWidget()
        self.tab_single = SingleGenerationUI()
        self.tab_conv = ConversationUI()
        self.tab_voices = VoiceManagerUI()

        self.stacked_widget.addWidget(self.tab_single)
        self.stacked_widget.addWidget(self.tab_conv)
        self.stacked_widget.addWidget(self.tab_voices)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stacked_widget)
        self.switch_tab(0)

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def update_progress(self, val):
        if self.stacked_widget.currentIndex() == 0:
            self.tab_single.progress_bar.setValue(val)

    def switch_tab(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        if index == 0:
            self.tab_single.refresh_voices()
        elif index == 1:
            self.tab_conv.refresh_voices()
        elif index == 2:
            self.tab_voices.refresh_voices()

    def closeEvent(self, event):

        if hasattr(self, "tab_conv") and len(self.tab_conv.conversation_state) > 0:

            msg = QMessageBox(self)
            msg.setWindowTitle("Unsaved Project")
            msg.setText(
                "You have an active project.\nDo you want to save it before exiting?"
            )
            msg.setStyleSheet("""
                QMessageBox { background-color: #0B0E14; }
                QLabel { color: #FFFFFF; font-size: 13px; font-weight: bold; }
                QPushButton {
                    background-color: #1A1A1A;
                    color: #FFFFFF;
                    padding: 8px 15px;
                    border-radius: 4px;
                    border: 1px solid #333333;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2A2A2A; }
            """)

            save_btn = msg.addButton("💾 Save", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = msg.addButton(
                "🗑 Don't Save", QMessageBox.ButtonRole.DestructiveRole
            )
            cancel_btn = msg.addButton("❌ Cancel", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            if msg.clickedButton() == save_btn:

                saved = self.tab_conv.save_project()
                if saved:
                    self.tab_conv.clear_autosave()
                    event.accept()
                else:
                    event.ignore()

            elif msg.clickedButton() == discard_btn:
                self.tab_conv.clear_autosave()
                event.accept()

            else:

                event.ignore()

        else:

            if hasattr(self, "tab_conv"):
                self.tab_conv.clear_autosave()
            event.accept()

import os
from PySide6.QtCore import QThread, Signal
from config import OUTPUTS_DIR
from generation import generate
from audio_core import mix_audio

class GenerationWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text, settings, project_name):
        super().__init__()
        self.text = text
        self.settings = settings
        self.project_name = project_name

    def run(self):
        try:
            res = generate(
                text=self.text,
                ref_audio=self.settings.get("ref_audio"),
                voice_name=self.settings.get("voice_name"),
                exaggeration=self.settings["exag"],
                cfg_weight=self.settings["cfg"],
                temperature=self.settings["temp"],
                speed=self.settings.get("speed", 1.0),
                min_p=self.settings.get("min_p", 0.05),
                top_p=self.settings.get("top_p", 1.0),
                repetition_penalty=self.settings.get("rep_pen", 1.2),
                seed=self.settings.get("seed", 0),
                proj_name_val=self.project_name,
            )
            if res[1] and os.path.exists(res[1]):
                self.finished.emit(res[1])
            else:
                self.error.emit(res[2])
        except Exception as e:
            self.error.emit(f"System Error: {str(e)}")

class ConversationWorker(QThread):

    progress = Signal(int, str, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, state, project_name, gap_ms=500):
        super().__init__()
        self.state = state
        self.project_name = project_name
        self.gap_ms = gap_ms

    def run(self):
        try:
            paths = []
            for i, row in enumerate(self.state):
                if row.get("path") and os.path.exists(row["path"]):
                    paths.append(row["path"])
                    self.progress.emit(i, "✅ DONE", "#2ECC8F")
                    continue

                self.progress.emit(i, "⏳ GENERATING...", "#6C9BFF")
                st = row["settings"]
                res = generate(
                    text=row["text"],
                    ref_audio=None,
                    voice_name=row["voice"],
                    exaggeration=st["exag"],
                    cfg_weight=st["cfg"],
                    temperature=st["temp"],
                    speed=st.get("speed", 1.0),
                    min_p=st.get("min_p", 0.05),
                    top_p=st.get("top_p", 1.0),
                    repetition_penalty=st.get("rep_pen", 1.2),
                    seed=st.get("seed", 0),
                    proj_name_val=self.project_name,
                )
                if res[1] and os.path.exists(res[1]):
                    self.state[i]["path"] = res[1]
                    paths.append(res[1])
                    self.progress.emit(i, "✅ DONE", "#2ECC8F")
                else:
                    self.progress.emit(i, "❌ ERROR", "#F1594F")
                    self.error.emit(f"Line {i+1}: {res[2]}")
                    return

            if paths:
                mix_folder = os.path.join(OUTPUTS_DIR, self.project_name)
                os.makedirs(mix_folder, exist_ok=True)

                mixed_path = mix_audio(paths, mix_folder, self.gap_ms / 1000.0)

                if mixed_path:
                    self.finished.emit(mixed_path)
                else:
                    self.error.emit("Failed to mix audio files.")
            else:
                self.error.emit("No lines to generate.")
        except Exception as e:
            self.error.emit(f"System Error: {str(e)}")

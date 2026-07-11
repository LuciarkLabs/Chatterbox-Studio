import os
import re
import json
import tempfile
import sys
import shutil
import subprocess

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR  = os.path.join(SCRIPT_DIR, "saved_voices")
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs")
PROJECTS_DIR = OUTPUTS_DIR
SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")

for d in [VOICES_DIR, OUTPUTS_DIR]:
    os.makedirs(d, exist_ok=True)

MAX_TEXT_LEN      = 500
EMPTY_CACHE_EVERY = 20
SUPPORTED_EXTS    = (".wav", ".mp3", ".flac", ".m4a")
TARGET_SR         = 24000

WIN_RESERVED  = re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)', re.IGNORECASE)
INVALID_CHARS = re.compile(r'[<>:"/\|?*\x00-\x1f]')

DEFAULT_SEED              = 0
DEFAULT_MIN_P             = 0.05
DEFAULT_TOP_P             = 1.0
DEFAULT_REPETITION_PENALTY = 1.2

def _atomic_json_dump(path: str, data: dict):
    dir_name = os.path.dirname(path)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def save_settings(data: dict):
    current = load_settings()
    current.update(data)
    _atomic_json_dump(SETTINGS_FILE, current)

def validate_safe_name(name, label="Name"):
    name = name.strip()
    if not name:
        return None, f"❌ {label} is empty."
    if INVALID_CHARS.search(name):
        return None, f"❌ {label} contains invalid characters."
    if WIN_RESERVED.match(name):
        return None, f"❌ '{name}' is a reserved Windows name."
    if name in (".", "..") or name.endswith("."):
        return None, f"❌ Invalid {label}."
    if len(name) > 100:
        return None, f"❌ {label} too long (max 100 chars)."
    return name, None

def project_dir(name: str) -> str:
    d = os.path.join(OUTPUTS_DIR, name)
    os.makedirs(d, exist_ok=True)
    return d

def open_outputs_folder():
    try:
        if sys.platform == "win32":
            os.startfile(OUTPUTS_DIR)
            return f"📂 Opened: {OUTPUTS_DIR}"
        elif sys.platform == "darwin":
            subprocess.Popen(["open", OUTPUTS_DIR])
            return f"📂 Opened: {OUTPUTS_DIR}"
        else:
            if shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", OUTPUTS_DIR])
                return f"📂 Opened: {OUTPUTS_DIR}"
            else:
                return f"📂 Open manually: {OUTPUTS_DIR}"
    except OSError as e:
        return f"❌ Could not open folder: {e}"

def _rel_path(p: str) -> str:
    if not p:
        return ""
    try:
        return os.path.relpath(p, OUTPUTS_DIR)
    except ValueError:
        return p

def _abs_path(rel: str) -> str:
    if not rel:
        return ""
    candidate = os.path.normpath(os.path.join(OUTPUTS_DIR, rel))
    outputs_real   = os.path.realpath(OUTPUTS_DIR)
    candidate_real = os.path.realpath(candidate)

    if candidate_real.startswith(outputs_real + os.sep) or candidate_real == outputs_real:
        if os.path.exists(candidate_real):
            return candidate_real
    return ""

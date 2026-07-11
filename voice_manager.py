import os
import shutil
import json

VOICES_DIR = os.path.join(os.getcwd(), "voices")
os.makedirs(VOICES_DIR, exist_ok=True)
META_FILE = os.path.join(VOICES_DIR, "favorites.json")

def _load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"favorites": []}

def _save_meta(data):
    try:
        with open(META_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def get_favorites():
    return _load_meta().get("favorites", [])

def toggle_favorite(name):

    meta = _load_meta()
    favs = meta.get("favorites", [])
    if name in favs:
        favs.remove(name)
    else:
        favs.append(name)
    meta["favorites"] = favs
    _save_meta(meta)

def get_saved_voices():

    voices = []
    if os.path.exists(VOICES_DIR):
        for file in os.listdir(VOICES_DIR):
            if file.lower().endswith(('.wav', '.mp3', '.flac', '.m4a', '.ogg')):
                name = os.path.splitext(file)[0]
                voices.append(name)

    voices.sort()
    favs = get_favorites()
    voices.sort(key=lambda x: 0 if x in favs else 1)

    return voices

def save_voice(name, source_path):
    if not name or not source_path or not os.path.exists(source_path):
        return False, "Invalid name or source file."

    safe_name = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    ext = os.path.splitext(source_path)[1]
    dest_path = os.path.join(VOICES_DIR, f"{safe_name}{ext}")

    try:
        shutil.copy(source_path, dest_path)
        return True, "Voice saved successfully!"
    except Exception as e:
        return False, str(e)

def delete_voice(name):
    if os.path.exists(VOICES_DIR):
        for file in os.listdir(VOICES_DIR):
            if os.path.splitext(file)[0] == name:
                try:
                    os.remove(os.path.join(VOICES_DIR, file))

                    meta = _load_meta()
                    favs = meta.get("favorites", [])
                    if name in favs:
                        favs.remove(name)
                        meta["favorites"] = favs
                        _save_meta(meta)
                    return True
                except:
                    pass
    return False

def load_voice_audio(name):
    if not name: return None
    if os.path.exists(VOICES_DIR):
        for file in os.listdir(VOICES_DIR):
            if os.path.splitext(file)[0] == name:
                return os.path.join(VOICES_DIR, file)
    return None

def rename_voice(old_name, new_name):
    if not old_name or not new_name: return False, "Invalid names"
    safe_new_name = "".join(c if c.isalnum() else "_" for c in new_name).strip("_")

    old_path = load_voice_audio(old_name)
    if not old_path: return False, "Voice not found"

    ext = os.path.splitext(old_path)[1]
    new_path = os.path.join(VOICES_DIR, f"{safe_new_name}{ext}")

    if os.path.exists(new_path):
        return False, "Name already exists"

    try:
        os.rename(old_path, new_path)

        meta = _load_meta()
        favs = meta.get("favorites", [])
        if old_name in favs:
            favs.remove(old_name)
            favs.append(safe_new_name)
            meta["favorites"] = favs
            _save_meta(meta)
        return True, "Renamed successfully"
    except Exception as e:
        return False, str(e)

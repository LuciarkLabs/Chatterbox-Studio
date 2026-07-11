import os
import json
import shutil
from config import (
    PROJECTS_DIR,
    OUTPUTS_DIR,
    validate_safe_name,
    _atomic_json_dump,
    project_dir,
    save_settings,
    load_settings,
    _abs_path,
    _rel_path,
    MAX_TEXT_LEN,
)
from voice_manager import get_saved_voices

def get_projects():
    ps = [
        f.replace(".json", "") for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")
    ]
    return sorted(ps) if ps else ["(no projects)"]

def _serialize_state(state: list) -> list:
    return [
        {
            "voice": r["voice"],
            "text": r["text"],
            "settings": r.get("settings", {}),
            "audio_path": _rel_path(r.get("path") or ""),
        }
        for r in state
    ]

def save_project(state, name):
    name, err = validate_safe_name(name, "Project name")
    if err:
        return err, get_projects()
    if not state:
        return "❌ Conversation is empty.", get_projects()

    data = _serialize_state(state)
    _atomic_json_dump(os.path.join(PROJECTS_DIR, f"{name}.json"), data)
    project_dir(name)
    save_settings({"last_project": name})
    return f"✅ '{name}' saved.", get_projects()

def load_project(name):
    name, err = validate_safe_name(name, "Project name")
    if err:
        return [], [], err
    path = os.path.join(PROJECTS_DIR, f"{name}.json")
    if not os.path.exists(path):
        return [], [], f"❌ '{name}' not found."

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return [], [], f"❌ Could not read project file: {e}"

    state = []
    for r in data:
        audio_path = _abs_path(r.get("audio_path", ""))
        state.append(
            {
                "voice": r["voice"],
                "text": r["text"],
                "settings": r.get("settings", {}),
                "path": audio_path or None,
            }
        )

    restored = sum(1 for r in state if r["path"])
    msg = f"✅ '{name}' loaded ({len(state)} lines, {restored} audio files restored)."
    return state, render_table(state), msg

def load_project_from_list(name):
    if not name or name == "(no projects)":
        return [], [], "", name or ""
    state, table, msg = load_project(name)
    return state, table, msg, name

def auto_save_project(state, proj_name):
    if not state or not proj_name or not proj_name.strip():
        return
    name, err = validate_safe_name(proj_name, "Project name")
    if err:
        return

    data = _serialize_state(state)
    try:
        _atomic_json_dump(os.path.join(PROJECTS_DIR, f"{name}.json"), data)
        save_settings({"last_project": name})
    except OSError as e:
        print(f"[WARNING] Auto-save failed: {e}")

def rename_project(old_name, new_name):
    old_name, err = validate_safe_name(old_name, "Current name")
    if err:
        return err, get_projects()
    new_name, err = validate_safe_name(new_name, "New name")
    if err:
        return err, get_projects()

    old_json = os.path.join(PROJECTS_DIR, f"{old_name}.json")
    new_json = os.path.join(PROJECTS_DIR, f"{new_name}.json")
    old_audio = os.path.join(OUTPUTS_DIR, old_name)
    new_audio = os.path.join(OUTPUTS_DIR, new_name)

    if not os.path.exists(old_json):
        return f"❌ '{old_name}' not found.", get_projects()
    if os.path.exists(new_json):
        return f"❌ Project '{new_name}' already exists.", get_projects()
    if os.path.isdir(old_audio) and os.path.exists(new_audio):
        return (
            f"❌ Audio folder '{new_name}' already exists in outputs.",
            get_projects(),
        )

    os.rename(old_json, new_json)
    if os.path.isdir(old_audio):
        try:
            shutil.move(old_audio, new_audio)
        except OSError as e:
            try:
                os.rename(new_json, old_json)
            except OSError as rb_err:
                print(f"[ERROR] rename_project rollback failed: {rb_err}")
            return (
                f"❌ Could not move audio folder (JSON rename rolled back): {e}",
                get_projects(),
            )

    settings = load_settings()
    if settings.get("last_project") == old_name:
        save_settings({"last_project": new_name})

    choices = get_projects()
    return f"✅ '{old_name}' → '{new_name}'.", choices

def delete_project(name, confirmed):
    if not confirmed:
        return "⚠️ Check 'Confirm delete'.", get_projects()
    name, err = validate_safe_name(name, "Project name")
    if err:
        return err, get_projects()

    json_path = os.path.join(PROJECTS_DIR, f"{name}.json")
    if not os.path.exists(json_path):
        return f"❌ '{name}' not found.", get_projects()

    audio_dir = os.path.join(OUTPUTS_DIR, name)
    if os.path.isdir(audio_dir):
        try:
            shutil.rmtree(audio_dir)
        except OSError as e:
            return (
                f"❌ Could not remove audio folder (project unchanged): {e}",
                get_projects(),
            )

    try:
        os.remove(json_path)
    except OSError as e:
        return f"⚠️ Audio folder removed but JSON deletion failed: {e}", get_projects()

    settings = load_settings()
    if settings.get("last_project") == name:
        save_settings({"last_project": ""})

    choices = get_projects()
    return f"✅ '{name}' deleted.", choices

def parse_script(script_text, voice_map_text):
    if not script_text.strip():
        return [], [], "❌ Script is empty."

    try:
        voice_map = json.loads(voice_map_text) if voice_map_text.strip() else {}
    except json.JSONDecodeError:
        return [], [], "❌ Voice map is not valid JSON."

    available = set(get_saved_voices())
    state, errors, warnings = [], [], []

    for i, line in enumerate(script_text.strip().splitlines(), 1):
        line = line.strip()
        if not line:
            continue

        if ":" not in line:
            errors.append(f"Line {i}: no ':' — skipped.")
            continue

        speaker, text = line.split(":", 1)
        speaker, text = speaker.strip(), text.strip()

        if not text:
            errors.append(f"Line {i}: empty text — skipped.")
            continue

        if len(text) > MAX_TEXT_LEN:
            warnings.append(f"Line {i}: truncated to {MAX_TEXT_LEN} chars.")
            text = text[:MAX_TEXT_LEN]

        voice = voice_map.get(speaker, "")
        if not voice or voice not in available:
            warnings.append(f"Line {i} ({speaker}): no voice → assign manually.")
            voice = "(no saved voices)"

        state.append({"voice": voice, "text": text, "path": None, "settings": {}})

    if not state:
        return [], [], "❌ No valid lines.\n" + "\n".join(errors)

    msg = f"✅ Imported {len(state)} lines."
    if warnings:
        msg += "\n⚠️ " + "\n".join(warnings)
    if errors:
        msg += "\n❌ " + "\n".join(errors)

    return state, render_table(state), msg

def render_table(state):
    rows = []
    for i, r in enumerate(state):
        preview = r["text"][:80] + ("…" if len(r["text"]) > 80 else "")
        rows.append([i + 1, r["voice"], preview, "✅" if r["path"] else "⏳"])
    return rows

def filter_table(state, query):
    if not query or not query.strip():
        return render_table(state)
    q = query.strip().lower()
    rows = []
    for i, r in enumerate(state):
        if q in r.get("voice", "").lower() or q in r.get("text", "").lower():
            preview = r["text"][:80] + ("…" if len(r["text"]) > 80 else "")
            rows.append([i + 1, r["voice"], preview, "✅" if r["path"] else "⏳"])
    return rows

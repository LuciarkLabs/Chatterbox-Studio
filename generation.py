import os
import time
from config import (
    MAX_TEXT_LEN,
    validate_safe_name,
    DEFAULT_SEED,
    DEFAULT_MIN_P,
    DEFAULT_TOP_P,
    DEFAULT_REPETITION_PENALTY,
)
from audio_core import (
    _set_seed,
    model,
    change_speed,
    maybe_empty_cache,
    save_wav,
    mix_audio,
)
from voice_manager import load_voice_audio
from project_manager import project_dir, auto_save_project, render_table
from hardware_monitor import get_hw_stats

def _build_kwargs(
    row, exaggeration, cfg_weight, temperature, min_p, top_p, repetition_penalty
):
    s = row.get("settings", {})
    return dict(
        exaggeration=s.get("exaggeration", exaggeration),
        cfg_weight=s.get("cfg_weight", cfg_weight),
        temperature=s.get("temperature", temperature),
        min_p=s.get("min_p", min_p),
        top_p=s.get("top_p", top_p),
        repetition_penalty=s.get("repetition_penalty", repetition_penalty),
    )

def _get_row_seed(row, default_seed):
    return row.get("settings", {}).get("seed", default_seed)

def _delete_wav(path: str):
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError as e:
            print(f"[WARNING] _delete_wav: could not remove '{path}': {e}")

def generate(
    text,
    ref_audio,
    exaggeration,
    cfg_weight,
    temperature,
    speed,
    min_p,
    top_p,
    repetition_penalty,
    seed,
    voice_name,
    proj_name_val,
):
    proj_name_val = proj_name_val.strip() if proj_name_val else ""
    if not proj_name_val:
        return True, None, "❌ Enter a project name first.", get_hw_stats()
    name, err = validate_safe_name(proj_name_val, "Project name")
    if err:
        return True, None, err, get_hw_stats()
    if not text.strip():
        return True, None, "❌ Enter text.", get_hw_stats()
    if len(text) > MAX_TEXT_LEN:
        return True, None, f"❌ Too long ({len(text)}/{MAX_TEXT_LEN}).", get_hw_stats()

    audio_path = ref_audio
    if voice_name and voice_name != "(no saved voices)":
        saved = load_voice_audio(voice_name)
        if saved:
            audio_path = saved

    try:
        _set_seed(int(seed) if seed else 0)
        kwargs = dict(
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            min_p=min_p,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
        )
        wav = (
            model.generate(text, audio_prompt_path=audio_path, **kwargs)
            if audio_path
            else model.generate(text, **kwargs)
        )
        wav = change_speed(wav, model.sr, speed)
        maybe_empty_cache()
        return (
            True,
            save_wav(wav, model.sr, project_dir(name)),
            "✅ Done!",
            get_hw_stats(),
        )
    except (RuntimeError, OSError) as e:
        return True, None, f"❌ {e}", get_hw_stats()

def add_line(state, voice, text, exag, cfg, temp, seed, min_p, top_p, rep_pen):
    if not text.strip():
        return state, render_table(state), "❌ Text is empty."
    if len(text) > MAX_TEXT_LEN:
        return state, render_table(state), f"❌ Too long ({len(text)}/{MAX_TEXT_LEN})."
    if not voice or voice == "(no saved voices)":
        return state, render_table(state), "❌ Select a voice."

    new_state = state + [
        {
            "voice": voice,
            "text": text,
            "path": None,
            "settings": {
                "exaggeration": exag,
                "cfg_weight": cfg,
                "temperature": temp,
                "seed": int(seed) if seed else 0,
                "min_p": min_p,
                "top_p": top_p,
                "repetition_penalty": rep_pen,
            },
        }
    ]
    return new_state, render_table(new_state), f"✅ Line {len(new_state)} added."

def remove_line(state, index_str):
    try:
        idx = int(index_str) - 1
        if not (0 <= idx < len(state)):
            return state, render_table(state), "❌ Invalid line number."
        _delete_wav(state[idx].get("path"))
        ns = [r for i, r in enumerate(state) if i != idx]
        return ns, render_table(ns), "✅ Removed."
    except (ValueError, TypeError):
        return state, render_table(state), "❌ Enter a valid number."

def edit_line_load(state, index_str):
    try:
        idx = int(index_str) - 1
    except (ValueError, TypeError):
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "❌ Invalid number.",
        )

    if not (0 <= idx < len(state)):
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "❌ Line not found.",
        )

    row = state[idx]
    s = row.get("settings", {})
    return (
        row["voice"],
        row["text"],
        s.get("exaggeration", 0.5),
        s.get("cfg_weight", 0.5),
        s.get("temperature", 0.8),
        s.get("seed", DEFAULT_SEED),
        s.get("min_p", DEFAULT_MIN_P),
        s.get("top_p", DEFAULT_TOP_P),
        s.get("repetition_penalty", DEFAULT_REPETITION_PENALTY),
        f"✅ Line {idx+1} loaded for editing.",
    )

def edit_line_save(
    state, index_str, new_voice, new_text, exag, cfg, temp, seed, min_p, top_p, rep_pen
):
    try:
        idx = int(index_str) - 1
    except (ValueError, TypeError):
        return state, render_table(state), "❌ Invalid number."

    if not (0 <= idx < len(state)):
        return state, render_table(state), "❌ Line not found."
    if not new_text.strip():
        return state, render_table(state), "❌ Text cannot be empty."
    if len(new_text) > MAX_TEXT_LEN:
        return (
            state,
            render_table(state),
            f"❌ Too long ({len(new_text)}/{MAX_TEXT_LEN}).",
        )
    if not new_voice or new_voice == "(no saved voices)":
        return state, render_table(state), "❌ Select a voice."

    new_state = [dict(r) for r in state]
    old = new_state[idx]
    new_settings = {
        "exaggeration": exag,
        "cfg_weight": cfg,
        "temperature": temp,
        "seed": int(seed) if seed else 0,
        "min_p": min_p,
        "top_p": top_p,
        "repetition_penalty": rep_pen,
    }

    if (
        old["voice"] != new_voice
        or old["text"] != new_text
        or old.get("settings", {}) != new_settings
    ):
        _delete_wav(old.get("path"))
        new_state[idx]["path"] = None

    new_state[idx]["voice"] = new_voice
    new_state[idx]["text"] = new_text
    new_state[idx]["settings"] = new_settings
    return (
        new_state,
        render_table(new_state),
        f"✅ Line {idx+1} updated (audio cleared — regenerate).",
    )

def _gen_one_row(row, exag, cfg, temp, speed, min_p, top_p, rep_pen, seed, folder):
    audio_path = load_voice_audio(row["voice"])
    kwargs = _build_kwargs(row, exag, cfg, temp, min_p, top_p, rep_pen)
    row_seed = _get_row_seed(row, seed)
    _set_seed(int(row_seed) if row_seed else 0)

    wav = (
        model.generate(row["text"], audio_prompt_path=audio_path, **kwargs)
        if audio_path
        else model.generate(row["text"], **kwargs)
    )
    return save_wav(change_speed(wav, model.sr, speed), model.sr, folder)

def _require_project(proj_name):
    pn = proj_name.strip() if proj_name else ""
    if not pn:
        return None, None, "❌ Enter a project name first."
    name, err = validate_safe_name(pn, "Project name")
    if err:
        return None, None, err
    return name, project_dir(name), None

def generate_line(
    state, index_str, exag, cfg, temp, speed, min_p, top_p, rep_pen, seed, proj_name
):
    name, folder, err = _require_project(proj_name)
    if err:
        return True, state, render_table(state), None, err, get_hw_stats()

    try:
        idx = int(index_str) - 1
    except (ValueError, TypeError):
        return (
            True,
            state,
            render_table(state),
            None,
            "❌ Invalid number.",
            get_hw_stats(),
        )

    if not (0 <= idx < len(state)):
        return (
            True,
            state,
            render_table(state),
            None,
            "❌ Line not found.",
            get_hw_stats(),
        )

    existing_path = state[idx].get("path")
    if existing_path and os.path.exists(existing_path):
        return (
            True,
            state,
            render_table(state),
            existing_path,
            "⚠️ This line has already been generated. Use 'Regenerate Line' to replace the existing audio.",
            get_hw_stats(),
        )

    old_path = state[idx].get("path")
    try:
        path = _gen_one_row(
            state[idx], exag, cfg, temp, speed, min_p, top_p, rep_pen, seed, folder
        )
        _delete_wav(old_path)
        new_state = [dict(r) for r in state]
        new_state[idx]["path"] = path
        maybe_empty_cache()
        auto_save_project(new_state, proj_name)
        return (
            True,
            new_state,
            render_table(new_state),
            path,
            f"✅ Line {idx+1} done.",
            get_hw_stats(),
        )
    except (RuntimeError, OSError) as e:
        return True, state, render_table(state), None, f"❌ {e}", get_hw_stats()

def regenerate_line(
    state, index_str, exag, cfg, temp, speed, min_p, top_p, rep_pen, seed, proj_name
):
    try:
        idx = int(index_str) - 1
    except (ValueError, TypeError):
        return (
            True,
            state,
            render_table(state),
            None,
            "❌ Invalid number.",
            get_hw_stats(),
        )

    if not (0 <= idx < len(state)):
        return (
            True,
            state,
            render_table(state),
            None,
            "❌ Line not found.",
            get_hw_stats(),
        )

    new_state = [dict(r) for r in state]
    _delete_wav(new_state[idx].get("path"))
    new_state[idx]["path"] = None
    return generate_line(
        new_state,
        index_str,
        exag,
        cfg,
        temp,
        speed,
        min_p,
        top_p,
        rep_pen,
        seed,
        proj_name,
    )

def generate_all(
    state, exag, cfg, temp, speed, silence_dur, min_p, top_p, rep_pen, seed, proj_name
):
    name, folder, err = _require_project(proj_name)
    if err:
        return True, state, render_table(state), None, err, get_hw_stats()
    if not state:
        return True, state, render_table(state), None, "❌ No lines.", get_hw_stats()

    new_state = [dict(r) for r in state]
    times, errs = [], []

    for i, row in enumerate(new_state):
        eta = f" — ETA {sum(times)/len(times)*(len(new_state)-i):.0f}s" if times else ""
        print(
            f"Line {i+1}/{len(new_state)} — {row['voice']}{eta}"
        )
        if row["path"] and os.path.exists(row["path"]):
            continue

        t0 = time.time()
        try:
            path = _gen_one_row(
                row, exag, cfg, temp, speed, min_p, top_p, rep_pen, seed, folder
            )
            new_state[i]["path"] = path
            times.append(time.time() - t0)
            maybe_empty_cache()
        except (RuntimeError, OSError) as e:
            errs.append(f"Line {i+1}: {e}")
            continue

    print("Mixing…")
    paths = [r["path"] for r in new_state if r["path"]]
    mixed = mix_audio(paths, folder, silence_duration=float(silence_dur))
    auto_save_project(new_state, proj_name)

    done = len(paths)
    msg = f"✅ {done}/{len(new_state)} lines done."
    if errs:
        msg += "\n⚠️ " + "\n".join(errs)
    return True, new_state, render_table(new_state), mixed, msg, get_hw_stats()

def remix_all(state, silence_dur, proj_name):
    name, folder, err = _require_project(proj_name)
    if err:
        return None, err, get_hw_stats()

    paths = [r["path"] for r in state if r["path"]]
    if not paths:
        return None, "❌ No generated lines.", get_hw_stats()

    return (
        mix_audio(paths, folder, float(silence_dur)),
        f"✅ Mixed {len(paths)} lines.",
        get_hw_stats(),
    )

def clear_conversation(state):
    for row in state:
        _delete_wav(row.get("path"))
    return [], [], "✅ Cleared.", get_hw_stats()

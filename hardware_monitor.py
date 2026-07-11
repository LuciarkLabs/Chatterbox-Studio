import os
import threading
import atexit
import torch
from datetime import datetime
from config import VOICES_DIR, PROJECTS_DIR, OUTPUTS_DIR

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_PYNVML = True
    atexit.register(pynvml.nvmlShutdown)
except Exception:
    HAS_PYNVML = False

def _icon(paths: str, viewbox: str = "0 0 24 24") -> str:
    return (
        f'<svg class="hw-icon" viewBox="{viewbox}" width="16" height="16" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )

_ICON_GPU = _icon('<rect x="2" y="4" width="20" height="14" rx="2"/> <path d="M8 21h8M12 17v4"/>')
_ICON_CPU = _icon('<rect x="6" y="6" width="12" height="12" rx="1.5"/> <path d="M6 2v3M12 2v3M18 2v3M6 19v3M12 19v3M18 19v3M2 6h3M2 12h3M2 18h3M19 6h3M19 12h3M19 18h3"/>')
_ICON_RAM = _icon('<rect x="3" y="8" width="18" height="8" rx="1.5"/> <path d="M7 8V5M11 8V5M15 8V5M17 8V5"/>')
_ICON_MIC = _icon('<path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/> <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8"/>')
_ICON_FOLDER = _icon('<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z"/>')
_ICON_VOICE = _icon('<path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/> <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>')
_ICON_PROJECT = _ICON_FOLDER
_ICON_FILES = _icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/> <path d="M14 2v6h6"/>')

_hw_lock       = threading.Lock()
_hw_cache_html = '<div id="gpu_bar">Loading…</div>'
_hw_stop_event = threading.Event()
_hw_monitor_thread = None

def _build_stats_html():
    try: n_voices = len([f for f in os.listdir(VOICES_DIR) if os.path.isfile(os.path.join(VOICES_DIR, f))])
    except Exception: n_voices = 0
    try: n_projects = len([f for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")])
    except Exception: n_projects = 0
    try: n_files = sum(len(files) for _, _, files in os.walk(OUTPUTS_DIR))
    except Exception: n_files = 0

    device_str = "CUDA" if torch.cuda.is_available() else "CPU"
    cards = [
        (_ICON_VOICE,   str(n_voices),   "Voices"),
        (_ICON_PROJECT, str(n_projects), "Projects"),
        (_ICON_FILES,   str(n_files),    "Generated Files"),
        (_ICON_GPU,     device_str,      "Device"),
    ]
    inner = "".join(
        f'<div class="stat-card">{icon}<div class="stat-text">'
        f'<div class="stat-value">{value}</div><div class="stat-label">{label}</div>'
        f'</div></div>' for icon, value, label in cards
    )
    return f'<div id="stats_row">{inner}</div>'

def _decode_nvml_str(val):
    return val.decode("utf-8", errors="replace") if isinstance(val, bytes) else str(val)

def _build_hw_html():
    segments = []
    if HAS_PYNVML:
        try:
            handle   = pynvml.nvmlDeviceGetHandleByIndex(0)
            name     = _decode_nvml_str(pynvml.nvmlDeviceGetName(handle))
            mem      = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util     = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp     = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            used_gb   = mem.used / 1024**3
            res_gb   = torch.cuda.memory_reserved() / 1024**3
            total_gb = mem.total / 1024**3
            segments.append(
                '<div class="hw-seg">'
                f'{_ICON_GPU} <div class="hw-seg-text">'
                f'<div class="hw-seg-title">{name}</div>'
                f'<div class="hw-seg-sub">VRAM <b>{used_gb:.1f}</b>/{total_gb:.1f} GB '
                f'(reserved {res_gb:.1f} GB)  ·  '
                f'GPU <b>{util.gpu}%</b>  ·  {temp}°C</div>'
                '</div></div>'
            )
        except Exception as e:
            segments.append(f'<div class="hw-seg">{_ICON_GPU} <div class="hw-seg-text"> <div class="hw-seg-title">GPU error</div> <div class="hw-seg-sub">{e}</div> </div> </div>')
    elif torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated() / 1024**3
        res   = torch.cuda.memory_reserved()  / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        segments.append(
            '<div class="hw-seg">'
            f'{_ICON_GPU} <div class="hw-seg-text">'
            f'<div class="hw-seg-title">{torch.cuda.get_device_name(0)}</div>'
            f'<div class="hw-seg-sub">VRAM alloc <b>{alloc:.1f}</b> reserved <b>{res:.1f}</b>/{total:.1f} GB</div>'
            '</div></div>'
        )
    else:
        segments.append(f'<div class="hw-seg">{_ICON_GPU} <div class="hw-seg-text"> <div class="hw-seg-title">GPU</div> <div class="hw-seg-sub">Not available</div> </div> </div>')

    if HAS_PSUTIL:
        try:
            cpu_pct      = psutil.cpu_percent(interval=None)
            cpu_temp_str = ""
            try:
                temps = psutil.sensors_temperatures() or {}
                for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    if key in temps and temps[key]:
                        cpu_temp_str = f" &nbsp;·&nbsp; {temps[key][0].current:.0f}°C"
                        break
            except (AttributeError, KeyError):
                pass
            segments.append(
                '<div class="hw-seg">'
                f'{_ICON_CPU}<div class="hw-seg-text">'
                f'<div class="hw-seg-title">CPU <b>{cpu_pct:.0f}%</b>{cpu_temp_str}</div>'
                f'<div class="hw-seg-sub">&nbsp;</div>'
                '</div></div>'
            )
        except Exception as e:
            print(f"[WARNING] CPU stats error: {e}")
            segments.append(f'<div class="hw-seg">{_ICON_CPU}<div class="hw-seg-text"><div class="hw-seg-title">CPU error</div><div class="hw-seg-sub">{e}</div></div></div>')

        try:
            ram = psutil.virtual_memory()
            segments.append(
                '<div class="hw-seg">'
                f'{_ICON_RAM}<div class="hw-seg-text">'
                f'<div class="hw-seg-title">RAM</div>'
                f'<div class="hw-seg-sub"><b>{ram.used/1024**3:.1f}</b>/{ram.total/1024**3:.1f} GB</div>'
                '</div></div>'
            )
        except Exception as e:
            print(f"[WARNING] RAM stats error: {e}")
            segments.append(f'<div class="hw-seg">{_ICON_RAM}<div class="hw-seg-text"><div class="hw-seg-title">RAM error</div><div class="hw-seg-sub">{e}</div></div></div>')

    ts = datetime.now().strftime("%H:%M:%S")
    inner = "".join(segments)
    return f'<div id="gpu_bar">{inner}<div class="hw-seg hw-seg-time">{ts}</div></div>'

def _hw_updater():
    global _hw_cache_html
    while not _hw_stop_event.is_set():
        try:
            html = _build_hw_html()
            with _hw_lock:
                _hw_cache_html = html
        except Exception as e:
            print(f"[WARNING] _hw_updater error: {e}")
        _hw_stop_event.wait(timeout=2)

def _stop_hw_updater():
    _hw_stop_event.set()

atexit.register(_stop_hw_updater)

def _start_hw_updater():
    global _hw_monitor_thread
    if _hw_monitor_thread is not None and _hw_monitor_thread.is_alive():
        return
    _hw_stop_event.clear()
    _hw_monitor_thread = threading.Thread(target=_hw_updater, daemon=True, name="hw-monitor")
    _hw_monitor_thread.start()

_start_hw_updater()

def get_hw_stats():
    with _hw_lock:
        return _hw_cache_html

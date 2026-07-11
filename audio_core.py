import torch
import torchaudio
import torchaudio.transforms as T
import os
import random as _random
from datetime import datetime
from chatterbox.tts import ChatterboxTTS
from config import TARGET_SR, EMPTY_CACHE_EVERY

print("Loading Chatterbox model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = ChatterboxTTS.from_pretrained(device=device)
print(f"Model loaded on {device}")

_gen_counter = 0

def _set_seed(seed: int):
    if seed and int(seed) > 0:
        s = int(seed)
        _random.seed(s)
        try:
            import numpy as np
            np.random.seed(s)
        except ImportError:
            pass
        torch.manual_seed(s)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(s)
    else:
        _random.seed(int.from_bytes(os.urandom(8), "little"))
        try:
            import numpy as np
            np.random.seed(int.from_bytes(os.urandom(4), "little"))
        except ImportError:
            pass
        torch.manual_seed(int.from_bytes(os.urandom(8), "little"))
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(int.from_bytes(os.urandom(8), "little"))

def maybe_empty_cache():
    global _gen_counter
    _gen_counter += 1
    if _gen_counter % EMPTY_CACHE_EVERY == 0 and torch.cuda.is_available():
        torch.cuda.empty_cache()

def convert_to_wav(src_path: str, dest_path: str):
    try:
        wav, sr = torchaudio.load(src_path)
    except (RuntimeError, OSError) as e:
        raise ValueError(f"Cannot load '{os.path.basename(src_path)}': {e}")

    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != TARGET_SR:
        wav = T.Resample(sr, TARGET_SR)(wav)
    torchaudio.save(dest_path, wav, TARGET_SR)

def change_speed(wav: torch.Tensor, sr: int, speed: float) -> torch.Tensor:
    if abs(speed - 1.0) < 0.01:
        return wav
    wav_cpu = wav.detach().cpu().float()
    try:
        import librosa
        import numpy as np
        audio_np  = wav_cpu.squeeze(0).numpy()
        stretched = librosa.effects.time_stretch(audio_np, rate=speed)
        return torch.from_numpy(stretched).unsqueeze(0)
    except ImportError:
        pass
    except Exception as e:
        print(f"[WARNING] change_speed: librosa failed ({e}) — falling back to sox.")

    try:
        effects = [["tempo", str(speed)]]
        wav_out, _ = torchaudio.sox_effects.apply_effects_tensor(wav_cpu, sr, effects)
        return wav_out
    except Exception:
        pass

    print("[WARNING] change_speed: librosa and sox unavailable — speed change skipped.")
    return wav_cpu

def safe_resample(wav: torch.Tensor, src_sr: int, tgt_sr: int) -> torch.Tensor:
    if src_sr == tgt_sr:
        return wav
    return T.Resample(src_sr, tgt_sr)(wav)

def silence_tensor(sr: int, duration: float) -> torch.Tensor:
    return torch.zeros(1, int(sr * duration))

def save_wav(wav: torch.Tensor, sr: int, folder: str, prefix: str = "tts") -> str:
    wav = wav.detach().cpu()
    fn  = f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S_%f')}.wav"
    out = os.path.join(folder, fn)
    torchaudio.save(out, wav, sr)
    return out

def purge_old_conversations(folder: str):
    try:
        for fn in os.listdir(folder):
            if fn.startswith("conversation") and fn.endswith(".wav"):
                try:
                    os.remove(os.path.join(folder, fn))
                except OSError as e:
                    print(f"[WARNING] _purge_old_conversations: could not remove '{fn}': {e}")
    except OSError as e:
        print(f"[WARNING] _purge_old_conversations: cannot list folder '{folder}': {e}")

def mix_audio(paths: list, folder: str, silence_duration: float = 0.4):
    valid_paths = [p for p in paths if p and os.path.exists(p)]
    if not valid_paths:
        return None

    wavs, sr = [], None
    for p in valid_paths:
        try:
            w, s = torchaudio.load(p)
            if w.shape[0] > 1:
                w = w.mean(dim=0, keepdim=True)
            if sr is None:
                sr = s
            if s != sr:
                w = safe_resample(w, s, sr)
            if wavs:
                wavs.append(silence_tensor(sr, silence_duration))
            wavs.append(w)
        except (RuntimeError, OSError):
            continue

    if not wavs:
        return None

    purge_old_conversations(folder)
    return save_wav(torch.cat(wavs, dim=1), sr, folder, prefix="conversation")

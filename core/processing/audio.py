import subprocess
from pathlib import Path
import wave
import numpy as np

def to_wav(input_path: str, out_dir: str) -> str:
    in_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (in_path.stem + ".wav")

    
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(in_path), "-ac", "1", "-ar", "16000", str(out_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(out_path)

def read_wav_mono(path: str):
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        audio = wf.readframes(n)
        sampwidth = wf.getsampwidth()

    if sampwidth == 2:
        x = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        
        x = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

    return x, sr

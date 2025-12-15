from __future__ import annotations

from pathlib import Path
import subprocess

from django.conf import settings

from .models import AudioChunk, Microphone


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """
    Запускає команду і повертає CompletedProcess (без підняття виключення).
    """
    return subprocess.run(cmd, capture_output=True, text=True)


def convert_chunk_to_wav(src: Path, dst: Path) -> bool:
    """
    Пробує декодувати один chunk (webm/opus) у PCM WAV.
    Повертає True, якщо конвертація вдалась і файл не порожній.
    """
    if not src.exists() or src.stat().st_size == 0:
        return False

    cmd = [
        "ffmpeg", "-y",
        "-hide_banner",
        "-loglevel", "error",  # щоб не спамило (можеш прибрати для дебагу)
        "-i", str(src),
        "-ac", "1",            # mono
        "-ar", "48000",        # 48kHz
        "-c:a", "pcm_s16le",   # PCM 16-bit
        str(dst),
    ]
    res = _run(cmd)
    return res.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def assemble_microphone_audio(microphone: Microphone) -> Path:
    """
    Надійна збірка:
      1) кожен chunk -> декодуємо в WAV (PCM)
      2) склеюємо WAV через ffmpeg concat (copy)
    Повертає шлях до mic_<id>_full.wav
    """

    chunks = (
        AudioChunk.objects
        .filter(microphone=microphone)
        .order_by("sequence")
    )

    if not chunks.exists():
        raise ValueError(f"No chunks found for microphone {microphone.id}")

    session_code = microphone.session.code

    mic_dir = (
        Path(settings.MEDIA_ROOT)
        / "audio_sessions"
        / session_code
        / f"mic_{microphone.id}"
    )
    mic_dir.mkdir(parents=True, exist_ok=True)

    # Тимчасова папка для декодованих wav-кусочків
    tmp_dir = mic_dir / "_tmp_wav"
    tmp_dir.mkdir(exist_ok=True)

    wav_list_file = mic_dir / "concat_wav_list.txt"
    output_path = mic_dir / f"mic_{microphone.id}_full.wav"

    valid_wavs: list[Path] = []

    # 1) декодуємо кожен chunk в wav (якщо вдається)
    for chunk in chunks:
        src = Path(chunk.audio_file.path)
        dst = tmp_dir / f"{chunk.sequence:06d}.wav"

        ok = convert_chunk_to_wav(src, dst)
        if ok:
            valid_wavs.append(dst)

    if not valid_wavs:
        raise ValueError(
            f"No chunks could be decoded to wav for microphone {microphone.id} "
            f"(all chunks corrupted or unreadable)"
        )

    # 2) пишемо concat список для wav
    with open(wav_list_file, "w", encoding="utf-8") as f:
        for wav in valid_wavs:
            f.write(f"file '{wav.as_posix()}'\n")

    # 3) склеюємо wav (PCM однаковий, тому можна -c copy)
    cmd_concat = [
        "ffmpeg", "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", str(wav_list_file),
        "-c", "copy",
        str(output_path),
    ]
    res = _run(cmd_concat)

    if res.returncode != 0 or not output_path.exists() or output_path.stat().st_size < 2000:
        # на випадок, якщо склейка не вдалась — покажемо stderr
        raise RuntimeError(
            "Failed to assemble wav.\n"
            f"STDERR:\n{res.stderr}\n"
        )

    return output_path

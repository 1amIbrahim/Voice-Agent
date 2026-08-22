"""Local text-to-speech synthesis and playback."""

from enum import Enum
from pathlib import Path
import re
from typing import Callable, Optional, Protocol, Sequence
import wave


WavPlayer = Callable[..., None]


class SpokenDetail(str, Enum):
    BRIEF = "brief"
    NORMAL = "normal"
    FULL = "full"


def spoken_summary(text: str, detail: SpokenDetail = SpokenDetail.BRIEF) -> str:
    plain = _plain_text(text)
    if detail is SpokenDetail.FULL:
        return plain

    sentence_limit, character_limit = (
        (3, 420) if detail is SpokenDetail.BRIEF else (6, 900)
    )
    sentences = re.split(r"(?<=[.!?])\s+", plain)
    selected = []
    total = 0
    for sentence in sentences:
        if not sentence:
            continue
        next_total = total + len(sentence) + (1 if selected else 0)
        if selected and next_total > character_limit:
            break
        selected.append(sentence)
        total = next_total
        if len(selected) == sentence_limit:
            break

    summary = " ".join(selected)
    if not summary:
        return ""
    if len(summary) < len(plain):
        return f"{summary} I can give you more detail if you like."
    return summary


def _plain_text(text: str) -> str:
    without_code = re.sub(r"```[\s\S]*?```", "", text)
    without_links = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", without_code)
    without_markdown = re.sub(r"[`*_>#]", "", without_links)
    without_lists = re.sub(r"(?m)^\s*[-+]\s+", "", without_markdown)
    return re.sub(r"\s+", " ", without_lists).strip()


def play_wav(
    path: Path,
    on_playback_started: Optional[Callable[[], None]] = None,
) -> None:
    """Play a PCM16 WAV file through the default audio output."""
    source = Path(path)
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("WAV playback requires the optional 'sounddevice' and 'numpy' packages") from exc

    try:
        with wave.open(str(source), "rb") as wav:
            if wav.getsampwidth() != 2:
                raise RuntimeError("WAV playback requires 16-bit PCM audio")
            frames = wav.readframes(wav.getnframes())
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
    except (OSError, wave.Error) as exc:
        raise RuntimeError(f"Could not read synthesized audio: {source}") from exc

    samples = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels)
    try:
        sd.play(samples, sample_rate)
        if on_playback_started is not None:
            on_playback_started()
        sd.wait()
    except Exception as exc:
        raise RuntimeError("Could not play synthesized audio through the default output device") from exc


def speak_responses(
    responses: Sequence[str],
    engine: "TTSEngine",
    output_path: Path,
    detail: SpokenDetail = SpokenDetail.BRIEF,
    player: WavPlayer = play_wav,
    follow_up: Optional[str] = None,
    on_playback_started: Optional[Callable[[], None]] = None,
) -> Optional[Path]:
    text = "\n\n".join(response.strip() for response in responses if response.strip())
    spoken_text = spoken_summary(text, detail)
    if follow_up and spoken_text:
        spoken_text = f"{spoken_text} {follow_up.strip()}"
    if not spoken_text:
        return None
    audio_path = engine.synthesize(spoken_text, output_path)
    if player is play_wav:
        player(audio_path, on_playback_started)
    else:
        if on_playback_started is not None:
            on_playback_started()
        player(audio_path)
    return audio_path


class TTSEngine(Protocol):
    def synthesize(self, text: str, output_path: Path) -> Path:
        ...


class PiperTTS:
    """Optional Piper command-line adapter."""

    def __init__(self, executable: str = "piper", model: Optional[Path] = None) -> None:
        if not executable:
            raise ValueError("executable must not be empty")
        self.executable = executable
        self.model = Path(model) if model else None

    def synthesize(self, text: str, output_path: Path) -> Path:
        if not text or not text.strip():
            raise ValueError("text must not be empty")
        if self.model is None:
            raise RuntimeError("Piper TTS requires a model path")

        import subprocess

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [self.executable, "--model", str(self.model), "--output_file", str(destination)],
            input=text,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Piper synthesis failed")
        return destination

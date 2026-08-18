"""Audio capture and WAV persistence primitives."""

import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


InputDevice = Union[int, str]




@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2

    def validate(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.channels <= 0:
            raise ValueError("channels must be positive")
        if self.sample_width not in (1, 2, 3, 4):
            raise ValueError("sample_width must be between 1 and 4 bytes")


class AudioRecorder:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or AudioConfig()
        self.config.validate()

    def save_wav(self, path: Path, audio: bytes) -> Path:
        """Save raw PCM bytes using the recorder's audio configuration."""
        if not isinstance(audio, bytes):
            raise TypeError("audio must be raw PCM bytes")

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination), "wb") as wav_file:
            wav_file.setnchannels(self.config.channels)
            wav_file.setsampwidth(self.config.sample_width)
            wav_file.setframerate(self.config.sample_rate)
            wav_file.writeframes(audio)
        return destination

    def load_wav(self, path: Path) -> bytes:
        """Load a WAV file and verify it matches the configured audio format."""
        with wave.open(str(path), "rb") as wav_file:
            actual = AudioConfig(
                sample_rate=wav_file.getframerate(),
                channels=wav_file.getnchannels(),
                sample_width=wav_file.getsampwidth(),
            )
            if actual != self.config:
                raise ValueError(
                    "WAV format does not match configuration: "
                    f"expected {self.config}, got {actual}"
                )
            return wav_file.readframes(wav_file.getnframes())

    def record(
        self,
        duration_seconds: float,
        device: Optional[InputDevice] = None,
    ) -> bytes:
        """Record from an input device using sounddevice."""
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Live recording requires the optional 'sounddevice' package"
            ) from exc

        frames = int(duration_seconds * self.config.sample_rate)
        try:
            recording = sd.rec(
                frames,
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                device=device,
            )
            sd.wait()
        except ImportError as exc:
            raise RuntimeError(
                "Live recording also requires the 'numpy' package"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                "Could not access the default microphone. "
                "Check Windows microphone permissions and the default input device."
            ) from exc
        return recording.tobytes()

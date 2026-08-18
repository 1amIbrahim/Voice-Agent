"""Audio capture and WAV persistence primitives."""

import array
import math
import queue
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union


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

    def record_until_silence(
        self,
        max_duration_seconds: float,
        silence_duration_seconds: float = 3.0,
        speech_threshold: float = 0.003,
        chunk_duration_ms: int = 100,
        device: Optional[InputDevice] = None,
        on_chunk: Optional[Callable[[bytes], None]] = None,
    ) -> bytes:
        """Capture chunks until speech is followed by configured silence."""
        if max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive")
        if silence_duration_seconds <= 0:
            raise ValueError("silence_duration_seconds must be positive")
        if not 0 < speech_threshold <= 1:
            raise ValueError("speech_threshold must be greater than 0 and at most 1")
        if chunk_duration_ms <= 0:
            raise ValueError("chunk_duration_ms must be positive")
        if self.config.channels != 1 or self.config.sample_width != 2:
            raise ValueError("record_until_silence requires mono PCM16 audio")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError(
                "Live recording requires the optional 'sounddevice' package"
            ) from exc

        chunk_frames = max(1, round(self.config.sample_rate * chunk_duration_ms / 1000))
        chunks: queue.Queue[bytes] = queue.Queue()

        def callback(indata: object, frames: int, time_info: object, status: object) -> None:
            chunks.put(indata.tobytes())

        captured = bytearray()
        speech_started = False
        silent_seconds = 0.0
        started_at = time.monotonic()
        try:
            stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="int16",
                blocksize=chunk_frames,
                device=device,
                callback=callback,
            )
            with stream:
                while time.monotonic() - started_at < max_duration_seconds:
                    try:
                        chunk = chunks.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    captured.extend(chunk)
                    samples = array.array("h")
                    samples.frombytes(chunk)
                    rms = (
                        math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768
                        if samples
                        else 0.0
                    )
                    chunk_seconds = len(samples) / (
                        self.config.sample_rate * self.config.channels
                    )
                    should_stop = False
                    if rms >= speech_threshold:
                        speech_started = True
                        silent_seconds = 0.0
                    elif speech_started:
                        silent_seconds += chunk_seconds
                        should_stop = silent_seconds >= silence_duration_seconds
                    if on_chunk is not None:
                        try:
                            on_chunk(chunk)
                        except RuntimeError:
                            raise
                        except Exception as exc:
                            raise RuntimeError(
                                "Streaming transcription failed while processing an audio chunk: "
                                f"{exc}"
                            ) from exc
                    if should_stop:
                        break
        except ImportError as exc:
            raise RuntimeError(
                "Live recording also requires the 'numpy' package"
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                "Could not access the microphone input stream. "
                "Check Windows microphone permissions and the default input device. "
                f"Underlying error: {exc}"
            ) from exc
        return bytes(captured)

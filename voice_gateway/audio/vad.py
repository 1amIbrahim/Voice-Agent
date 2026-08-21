"""Voice activity detection implementations."""

import array
import math
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol


@dataclass(frozen=True)
class SpeechSegment:
    start_frame: int
    end_frame: int
    sample_rate: int

    @property
    def start_time(self) -> float:
        return self.start_frame / self.sample_rate

    @property
    def end_time(self) -> float:
        return self.end_frame / self.sample_rate

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class VoiceActivityDetector(Protocol):
    def detect(self, audio: bytes, sample_rate: int = 16000) -> List[SpeechSegment]:
        ...


class LiveSpeechDetector(Protocol):
    def reset(self) -> None:
        ...

    def process(self, audio: bytes, sample_rate: int = 16000) -> bool:
        ...


@dataclass(frozen=True)
class EnergyVADConfig:
    frame_duration_ms: int = 30
    speech_threshold: float = 0.005
    min_speech_duration_ms: int = 120
    min_silence_duration_ms: int = 240

    def validate(self) -> None:
        if self.frame_duration_ms <= 0:
            raise ValueError("frame_duration_ms must be positive")
        if not 0 < self.speech_threshold <= 1:
            raise ValueError("speech_threshold must be greater than 0 and at most 1")
        if self.min_speech_duration_ms <= 0:
            raise ValueError("min_speech_duration_ms must be positive")
        if self.min_silence_duration_ms <= 0:
            raise ValueError("min_silence_duration_ms must be positive")


class EnergyVAD:
    """Dependency-free RMS energy detector for PCM16 mono audio."""

    def __init__(self, config: Optional[EnergyVADConfig] = None) -> None:
        self.config = config or EnergyVADConfig()
        self.config.validate()

    def detect(self, audio: bytes, sample_rate: int = 16000) -> List[SpeechSegment]:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if len(audio) % 2:
            raise ValueError("PCM16 audio must contain an even number of bytes")

        samples = array.array("h")
        samples.frombytes(audio)
        if not samples:
            return []

        if samples.itemsize != 2:
            raise RuntimeError("platform does not support 16-bit audio samples")

        frame_size = max(1, round(sample_rate * self.config.frame_duration_ms / 1000))
        speech_flags = []
        for start in range(0, len(samples), frame_size):
            frame = samples[start : start + frame_size]
            rms = math.sqrt(sum(sample * sample for sample in frame) / len(frame)) / 32768
            speech_flags.append((start, min(start + len(frame), len(samples)), rms >= self.config.speech_threshold))

        min_speech_frames = max(
            1, math.ceil(self.config.min_speech_duration_ms / self.config.frame_duration_ms)
        )
        min_silence_frames = max(
            1, math.ceil(self.config.min_silence_duration_ms / self.config.frame_duration_ms)
        )

        segments: List[SpeechSegment] = []
        speech_start: Optional[int] = None
        last_speech_end: Optional[int] = None
        silence_frames = 0

        for start, end, is_speech in speech_flags:
            if is_speech:
                if speech_start is None:
                    speech_start = start
                last_speech_end = end
                silence_frames = 0
                continue

            if speech_start is None:
                continue

            silence_frames += 1
            if silence_frames < min_silence_frames:
                continue

            if last_speech_end is not None and self._frame_count(speech_start, last_speech_end, frame_size) >= min_speech_frames:
                segments.append(SpeechSegment(speech_start, last_speech_end, sample_rate))
            speech_start = None
            last_speech_end = None
            silence_frames = 0

        if speech_start is not None and last_speech_end is not None:
            if self._frame_count(speech_start, last_speech_end, frame_size) >= min_speech_frames:
                segments.append(SpeechSegment(speech_start, last_speech_end, sample_rate))

        return segments

    @staticmethod
    def _frame_count(start: int, end: int, frame_size: int) -> int:
        return max(1, math.ceil((end - start) / frame_size))


class EnergySpeechDetector:
    """Stateful RMS detector used by the live silence endpoint."""

    def __init__(self, threshold: float = 0.005) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be greater than 0 and at most 1")
        self.threshold = threshold

    def reset(self) -> None:
        return None

    def process(self, audio: bytes, sample_rate: int = 16000) -> bool:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if len(audio) % 2:
            raise ValueError("PCM16 audio must contain an even number of bytes")
        samples = array.array("h")
        samples.frombytes(audio)
        if not samples:
            return False
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768
        return rms >= self.threshold


class SileroSpeechDetector:
    """Stateful Silero detector for 16 kHz PCM16 microphone chunks."""

    FRAME_SAMPLES = 512

    def __init__(self, threshold: float = 0.5) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be greater than 0 and at most 1")
        self.threshold = threshold
        self._torch: Optional[Any] = None
        self._iterator: Optional[Any] = None
        self._pending = bytearray()
        self._speaking = False

    def warm_up(self) -> None:
        self._load()
        self.reset()

    def reset(self) -> None:
        self._pending.clear()
        self._speaking = False
        if self._iterator is not None:
            self._iterator.reset_states()

    def process(self, audio: bytes, sample_rate: int = 16000) -> bool:
        if sample_rate != 16000:
            raise ValueError("Silero live VAD requires a 16000 Hz sample rate")
        if len(audio) % 2:
            raise ValueError("PCM16 audio must contain an even number of bytes")
        self._load()
        self._pending.extend(audio)
        frame_bytes = self.FRAME_SAMPLES * 2
        detected_speech = False
        while len(self._pending) >= frame_bytes:
            frame = bytes(self._pending[:frame_bytes])
            del self._pending[:frame_bytes]
            samples = array.array("h")
            samples.frombytes(frame)
            waveform = self._torch.tensor(samples, dtype=self._torch.float32) / 32768
            event = self._iterator(waveform)
            if event and "start" in event:
                self._speaking = True
            elif event and "end" in event:
                self._speaking = False
            detected_speech = detected_speech or self._speaking
        return detected_speech

    def _load(self) -> None:
        if self._iterator is not None:
            return
        try:
            import torch
            from silero_vad import VADIterator, load_silero_vad
        except ImportError as exc:
            raise RuntimeError(
                "Silero live VAD requires the optional 'silero-vad' and 'torchaudio' packages"
            ) from exc
        self._torch = torch
        self._iterator = VADIterator(
            load_silero_vad(),
            threshold=self.threshold,
            sampling_rate=16000,
        )


class SileroVAD:
    """Optional Silero VAD adapter loaded only when used."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 100,
        min_silence_duration_ms: int = 100,
    ) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be greater than 0 and at most 1")
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms

    def detect(self, audio: bytes, sample_rate: int = 16000) -> List[SpeechSegment]:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if len(audio) % 2:
            raise ValueError("PCM16 audio must contain an even number of bytes")

        try:
            import torch
            from silero_vad import get_speech_timestamps, load_silero_vad
        except ImportError as exc:
            raise RuntimeError(
                "Silero VAD requires the optional 'torch' and 'silero-vad' packages"
            ) from exc

        samples = array.array("h")
        samples.frombytes(audio)
        waveform = torch.tensor(samples, dtype=torch.float32) / 32768
        model = load_silero_vad()
        timestamps = get_speech_timestamps(
            waveform,
            model,
            sampling_rate=sample_rate,
            threshold=self.threshold,
            min_speech_duration_ms=self.min_speech_duration_ms,
            min_silence_duration_ms=self.min_silence_duration_ms,
        )
        return [
            SpeechSegment(item["start"], item["end"], sample_rate)
            for item in timestamps
        ]

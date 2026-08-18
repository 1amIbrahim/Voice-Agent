"""Provider-neutral automatic speech recognition interfaces."""

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Protocol, Union


@dataclass(frozen=True)
class Transcript:
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ASREngine(Protocol):
    def transcribe(self, audio: Union[bytes, Path], sample_rate: int = 16000) -> Transcript:
        ...


class OpenAIWhisperASR:
    """Lazy-loaded adapter for the OpenAI Whisper Python package."""

    def __init__(
        self,
        model_size: str = "small.en",
        device: str = "auto",
        language: Optional[str] = "en",
    ) -> None:
        if not model_size:
            raise ValueError("model_size must not be empty")
        self.model_size = model_size
        self.device = device
        self.language = language
        self._model: Any = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            import whisper
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI Whisper ASR requires the optional 'openai-whisper' package"
            ) from exc

        device = None if self.device == "auto" else self.device
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self._model = whisper.load_model(self.model_size, device=device)
        return self._model

    @property
    def runtime_device(self) -> str:
        if self._model is None:
            raise RuntimeError("ASR model must be loaded before checking its runtime device")
        return str(next(self._model.parameters()).device)

    def warm_up(self) -> None:
        self._load_model()

    def cuda_available(self) -> bool:
        try:
            import torch
        except ImportError:
            return False
        return bool(torch.cuda.is_available())

    def transcribe(self, audio: Union[bytes, Path], sample_rate: int = 16000) -> Transcript:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if isinstance(audio, bytes):
            raise RuntimeError(
                "OpenAIWhisperASR currently accepts a WAV path; save raw audio first"
            )
        path = Path(audio)
        if not path.exists():
            raise FileNotFoundError(path)

        model = self._load_model()
        result = model.transcribe(
            str(path),
            language=self.language,
            fp16=self.runtime_device.startswith("cuda"),
        )
        segments = result.get("segments", [])
        text = result.get("text", "").strip()
        start_time = segments[0].get("start") if segments else None
        end_time = segments[-1].get("end") if segments else None
        confidence = self._confidence(segments)
        return Transcript(
            text=text,
            language=result.get("language", self.language),
            confidence=confidence,
            start_time=start_time,
            end_time=end_time,
        )

    @staticmethod
    def _confidence(segments: List[Any]) -> Optional[float]:
        probabilities = [
            segment.get("avg_logprob")
            for segment in segments
            if segment.get("avg_logprob") is not None
        ]
        if not probabilities:
            return None
        return sum(probabilities) / len(probabilities)


__all__ = ["ASREngine", "OpenAIWhisperASR", "Transcript"]
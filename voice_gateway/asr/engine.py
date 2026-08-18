"""Provider-neutral automatic speech recognition interfaces."""

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


class FasterWhisperASR:
    """Lazy-loaded faster-whisper adapter for local transcription."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "auto",
        compute_type: str = "auto",
        language: Optional[str] = "en",
    ) -> None:
        if not model_size:
            raise ValueError("model_size must not be empty")
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Any = None

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Faster-whisper ASR requires the optional 'faster-whisper' package"
            ) from exc

        device = self.device
        compute_type = self.compute_type
        if device == "auto":
            device = "cuda"
            compute_type = "float16"
        self._model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
        )
        return self._model

    def transcribe(self, audio: Union[bytes, Path], sample_rate: int = 16000) -> Transcript:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if isinstance(audio, bytes):
            raise RuntimeError(
                "FasterWhisperASR currently accepts a WAV path; save raw audio first"
            )
        path = Path(audio)
        if not path.exists():
            raise FileNotFoundError(path)

        model = self._load_model()
        segments, info = model.transcribe(
            str(path),
            language=self.language,
            vad_filter=False,
        )
        segment_list: List[Any] = list(segments)
        text = " ".join(segment.text.strip() for segment in segment_list).strip()
        start_time = segment_list[0].start if segment_list else None
        end_time = segment_list[-1].end if segment_list else None
        confidence = self._confidence(segment_list)
        return Transcript(
            text=text,
            language=getattr(info, "language", self.language),
            confidence=confidence,
            start_time=start_time,
            end_time=end_time,
        )

    @staticmethod
    def _confidence(segments: List[Any]) -> Optional[float]:
        probabilities = [
            getattr(segment, "avg_logprob", None)
            for segment in segments
            if getattr(segment, "avg_logprob", None) is not None
        ]
        if not probabilities:
            return None
        return sum(probabilities) / len(probabilities)

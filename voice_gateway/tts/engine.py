"""Provider-neutral text-to-speech interfaces."""

from pathlib import Path
from typing import Any, Optional, Protocol


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
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Piper synthesis failed")
        return destination

from pathlib import Path

import pytest

from voice_gateway.asr import OpenAIWhisperASR, Transcript


class FakeWhisperModel:
    class _Parameter:
        device = "cpu"

    def parameters(self):
        return iter([self._Parameter()])

    def transcribe(self, path, **kwargs):
        assert kwargs["fp16"] is False
        return {
            "text": "tell Claude to check the folder",
            "language": "en",
            "segments": [
                {"start": 1.2, "end": 3.4, "avg_logprob": -0.2},
            ],
        }


def test_openai_whisper_transcribes_wav_with_metadata(tmp_path):
    path = tmp_path / "sample.wav"
    path.write_bytes(b"wav")
    asr = OpenAIWhisperASR(device="cpu")
    asr._model = FakeWhisperModel()

    transcript = asr.transcribe(path)

    assert transcript.text == "tell Claude to check the folder"
    assert transcript.language == "en"
    assert transcript.confidence == pytest.approx(-0.2)
    assert transcript.start_time == pytest.approx(1.2)
    assert transcript.end_time == pytest.approx(3.4)


def test_openai_whisper_defaults_to_small_en_model():
    assert OpenAIWhisperASR().model_size == "small.en"


def test_runtime_device_requires_loaded_model():
    with pytest.raises(RuntimeError, match="must be loaded"):
        OpenAIWhisperASR().runtime_device


def test_runtime_device_reads_loaded_model():
    class FakeParameter:
        device = "cpu"

    class FakeModel:
        def parameters(self):
            return iter([FakeParameter()])

    asr = OpenAIWhisperASR()
    asr._model = FakeModel()

    assert asr.runtime_device == "cpu"


def test_openai_whisper_rejects_raw_bytes():
    with pytest.raises(RuntimeError, match="WAV path"):
        OpenAIWhisperASR().transcribe(b"\x00\x00")


def test_cuda_available_reports_torch_status(monkeypatch):
    import types

    monkeypatch.setitem(__import__("sys").modules, "torch", types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True)))
    assert OpenAIWhisperASR().cuda_available() is True


def test_openai_whisper_reports_missing_package(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def reject_whisper(name, *args, **kwargs):
        if name == "whisper":
            raise ImportError("missing whisper")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_whisper)
    with pytest.raises(RuntimeError, match="openai-whisper"):
        OpenAIWhisperASR()._load_model()


def test_transcript_contains_voice_metadata():
    transcript = Transcript(
        text="tell Claude to check the folder",
        language="en",
        confidence=0.96,
        start_time=1.2,
        end_time=3.4,
    )

    assert transcript.text.startswith("tell Claude")
    assert transcript.language == "en"
    assert transcript.end_time - transcript.start_time == pytest.approx(2.2)


def test_asr_rejects_invalid_sample_rate():
    with pytest.raises(ValueError, match="sample_rate"):
        OpenAIWhisperASR().transcribe(Path("missing.wav"), sample_rate=0)


def test_asr_reports_missing_audio_file():
    with pytest.raises(FileNotFoundError):
        OpenAIWhisperASR().transcribe(Path("missing.wav"))

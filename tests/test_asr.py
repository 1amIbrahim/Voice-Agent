from pathlib import Path

import pytest

from voice_gateway.asr import FasterWhisperASR, Transcript


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
        FasterWhisperASR().transcribe(Path("missing.wav"), sample_rate=0)


def test_asr_reports_missing_audio_file():
    with pytest.raises(FileNotFoundError):
        FasterWhisperASR().transcribe(Path("missing.wav"))


def test_asr_requires_wav_path_for_raw_bytes():
    with pytest.raises(RuntimeError, match="WAV path"):
        FasterWhisperASR().transcribe(b"\x00\x00")

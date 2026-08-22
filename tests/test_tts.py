from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch

from voice_gateway.tts import PiperTTS, SpokenDetail, speak_responses, spoken_summary


class FakeTTS:
    def __init__(self) -> None:
        self.calls = []

    def synthesize(self, text: str, output_path: Path) -> Path:
        self.calls.append((text, output_path))
        return output_path


def test_brief_spoken_summary_strips_markdown_and_limits_sentences():
    response = "# Result\n\nThe task completed successfully. It updated `main.py`. Details follow. More detail."

    summary = spoken_summary(response)

    assert summary == (
        "Result The task completed successfully. It updated main.py. Details follow. "
        "I can give you more detail if you like."
    )


def test_full_spoken_summary_preserves_all_plain_text():
    response = "# Result\n\nThe task completed successfully."

    assert spoken_summary(response, SpokenDetail.FULL) == "Result The task completed successfully."


def test_piper_sends_unicode_input_as_utf8(tmp_path):
    model = tmp_path / "voice.onnx"
    model.touch()
    output = tmp_path / "response.wav"
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    with patch("subprocess.run", return_value=completed) as run:
        PiperTTS(executable="piper", model=model).synthesize("Ready → complete", output)

    assert run.call_args.kwargs["input"] == "Ready → complete"
    assert run.call_args.kwargs["encoding"] == "utf-8"
    assert run.call_args.kwargs["errors"] == "strict"


def test_speak_responses_synthesizes_and_plays_combined_text(tmp_path):
    engine = FakeTTS()
    played = []
    output = tmp_path / "response.wav"

    result = speak_responses(
        ["First response", "Second response"],
        engine,
        output,
        player=played.append,
    )

    assert result == output
    assert engine.calls == [("First response Second response", output)]
    assert played == [output]


def test_play_wav_marks_playback_after_audio_starts(tmp_path):
    import sys
    import wave

    output = tmp_path / "response.wav"
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 160)

    events = []
    sounddevice = MagicMock()
    sounddevice.play.side_effect = lambda *args: events.append("play")
    sounddevice.wait.side_effect = lambda: events.append("wait")

    with patch.dict(sys.modules, {"sounddevice": sounddevice}):
        from voice_gateway.tts.engine import play_wav

        play_wav(output, on_playback_started=lambda: events.append("playback-started"))

    assert events == ["play", "playback-started", "wait"]


def test_speak_responses_marks_playback_after_synthesis(tmp_path):
    events = []
    output = tmp_path / "response.wav"

    class OrderedTTS:
        def synthesize(self, text, output_path):
            events.append("synthesize")
            return output_path

    speak_responses(
        ["Ready."],
        OrderedTTS(),
        output,
        on_playback_started=lambda: events.append("playback-started"),
        player=lambda path: events.append("play"),
    )

    assert events == ["synthesize", "playback-started", "play"]


def test_speak_responses_appends_follow_up_prompt(tmp_path):
    engine = FakeTTS()
    output = tmp_path / "response.wav"

    speak_responses(
        ["Task completed."],
        engine,
        output,
        follow_up="What would you like to do next?",
        player=lambda path: None,
    )

    assert engine.calls == [("Task completed. What would you like to do next?", output)]


def test_speak_responses_skips_empty_responses(tmp_path):
    engine = FakeTTS()
    playback_started = []

    result = speak_responses(
        ["", "  "],
        engine,
        tmp_path / "response.wav",
        on_playback_started=lambda: playback_started.append(True),
    )

    assert result is None
    assert engine.calls == []
    assert playback_started == []

import asyncio
from pathlib import Path

import pytest

from voice_gateway.main import (
    build_live_vad,
    build_parser,
    build_understanding,
    main,
    pipeline_for,
    run_stream,
    run_text,
    speak_pipeline_responses,
)
from voice_gateway.audio import EnergySpeechDetector, SileroSpeechDetector
from voice_gateway.routing import ClaudeCodeAgentPlatform, FakeAgentPlatform
from voice_gateway.understanding import OllamaUnderstanding, RuleBasedUnderstanding


class FailingStreamSession:
    async def record_until_silence_and_process(self, **kwargs):
        raise RuntimeError("Ollama understanding requires the optional 'ollama' package")


@pytest.mark.asyncio
async def test_stream_returns_clean_failure_for_runtime_error(monkeypatch, capsys, tmp_path):
    import voice_gateway.main as main_module

    monkeypatch.setattr(main_module, "PushToTalkSession", lambda **kwargs: FailingStreamSession())
    args = build_parser().parse_args(["--stream", "--output", str(tmp_path / "out.wav")])

    assert await run_stream(args) == 1
    assert "streaming recording failed" in capsys.readouterr().err


def test_main_returns_clean_failure_for_runtime_error(monkeypatch, capsys):
    import voice_gateway.main as main_module

    async def fail(text, args):
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "run_text", fail)

    assert main(["--text", "test"]) == 1
    captured = capsys.readouterr()
    assert "[voice-gateway] error: boom" in captured.err
    assert "Error in sys.excepthook" not in captured.err


def test_parser_defaults_to_rule_understanding_and_small_en_asr():
    args = build_parser().parse_args(["--text", "check the folder"])

    assert args.understanding == "rule"
    assert args.understanding_model == "qwen2.5:3b"
    assert args.silence_duration == 3.0
    assert args.model_size == "small.en"
    assert isinstance(build_understanding(args), RuleBasedUnderstanding)


def test_parser_defaults_to_no_tts_with_jarvis_model_path():
    args = build_parser().parse_args(["--stream"])

    assert args.tts == "none"
    assert args.tts_model == Path("models/piper/jarvis-medium.onnx")
    assert args.tts_output.name == "response.wav"
    assert args.spoken_detail == "brief"


def test_speak_pipeline_responses_requires_existing_piper_model(tmp_path):
    args = build_parser().parse_args(
        ["--text", "check", "--tts", "piper", "--tts-model", str(tmp_path / "missing.onnx")]
    )

    with pytest.raises(ValueError, match="voice model was not found"):
        speak_pipeline_responses(["response"], args)


def test_parser_selects_energy_live_vad_by_default():
    args = build_parser().parse_args(["--stream"])

    detector = build_live_vad(args)

    assert isinstance(detector, EnergySpeechDetector)
    assert detector.threshold == 0.005


def test_parser_selects_silero_live_vad():
    args = build_parser().parse_args(
        ["--stream", "--vad", "silero", "--silero-threshold", "0.6"]
    )

    detector = build_live_vad(args)

    assert isinstance(detector, SileroSpeechDetector)
    assert detector.threshold == 0.6


def test_parser_can_select_ollama_understanding():
    args = build_parser().parse_args(
        [
            "--text",
            "check the folder",
            "--understanding",
            "ollama",
            "--understanding-model",
            "qwen2.5:7b",
        ]
    )

    understanding = build_understanding(args)

    assert isinstance(understanding, OllamaUnderstanding)
    assert understanding.model == "qwen2.5:7b"


def test_pipeline_uses_selected_understanding_provider():
    args = build_parser().parse_args(
        ["--text", "check the folder", "--understanding", "ollama"]
    )

    assert isinstance(pipeline_for(args).understanding, OllamaUnderstanding)


def test_pipeline_defaults_to_fake_agent_platform():
    args = build_parser().parse_args(["--text", "check the folder"])

    assert isinstance(pipeline_for(args).agent_platform, FakeAgentPlatform)


def test_pipeline_configures_plan_mode_claude_code_platform(tmp_path):
    args = build_parser().parse_args(
        [
            "--text",
            "check the folder",
            "--agent-platform",
            "claude-code",
            "--agent-workdir",
            str(tmp_path),
        ]
    )

    platform = pipeline_for(args).agent_platform

    assert isinstance(platform, ClaudeCodeAgentPlatform)
    assert platform.workspace == tmp_path
    assert platform.model == "sonnet"
    assert platform.timeout_seconds == 120.0


def test_claude_code_platform_requires_explicit_workspace():
    args = build_parser().parse_args(
        ["--text", "check the folder", "--agent-platform", "claude-code"]
    )

    with pytest.raises(ValueError, match="agent-workdir"):
        pipeline_for(args)


def test_text_mode_accepts_parser_namespace(capsys):
    args = build_parser().parse_args(["--text", "Tell Claude to check the folder"])

    assert asyncio.run(run_text(args.text, args)) == 0
    output = capsys.readouterr().out
    assert '"intent": "delegate_task"' in output

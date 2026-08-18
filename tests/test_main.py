import asyncio

import pytest

from voice_gateway.main import (
    build_parser,
    build_understanding,
    main,
    pipeline_for,
    run_stream,
    run_text,
)
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


def test_text_mode_accepts_parser_namespace(capsys):
    args = build_parser().parse_args(["--text", "Tell Claude to check the folder"])

    assert asyncio.run(run_text(args.text, args)) == 0
    output = capsys.readouterr().out
    assert '"intent": "delegate_task"' in output

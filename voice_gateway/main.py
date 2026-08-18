"""Command-line entry point for local voice gateway experiments."""

import argparse
import array
import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any, List, Optional


InputDevice = Any



def audio_signal(audio: bytes) -> tuple[int, float]:
    samples = array.array("h")
    samples.frombytes(audio)
    if not samples:
        return 0, 0.0
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return peak, rms



def resolve_input_device(value: Optional[str]) -> InputDevice:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass

    import sounddevice as sd

    needle = value.casefold()
    matches = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] <= 0:
            continue
        if needle in device["name"].casefold():
            hostapi = sd.query_hostapis(device["hostapi"])["name"]
            matches.append((index, device["name"], hostapi))

    if not matches:
        raise ValueError(f"no input device matches {value!r}")
    if len(matches) > 1:
        mme_matches = [match for match in matches if match[2] == "MME"]
        if mme_matches:
            matches = mme_matches
        log(
            "multiple matching input devices; using "
            f"{matches[0][0]} ({matches[0][1]}, {matches[0][2]})"
        )
    return matches[0][0]



def log(message: str) -> None:
    formatted = f"[voice-gateway] {message}"
    for stream in (sys.stderr, sys.stdout):
        try:
            print(formatted, file=stream, flush=True)
            return
        except (OSError, ValueError):
            continue



def log_error(message: str) -> None:
    log(f"error: {message}")



def format_optional(value: Optional[float]) -> str:
    return "unknown" if value is None else f"{value:.3f}"


from voice_gateway.asr import OpenAIWhisperASR
from voice_gateway.audio import AudioRecorder
from voice_gateway.pipeline import PushToTalkSession, VoicePipeline
from voice_gateway.understanding import OllamaUnderstanding, RuleBasedUnderstanding



def build_understanding(args: argparse.Namespace) -> Any:
    if args.understanding == "ollama":
        return OllamaUnderstanding(model=args.understanding_model)
    return RuleBasedUnderstanding()



def pipeline_for(args: argparse.Namespace) -> VoicePipeline:
    return VoicePipeline(understanding=build_understanding(args))



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local voice gateway experiments")
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--text", help="process a transcript without microphone or model dependencies")
    mode.add_argument("--record", action="store_true", help="record one push-to-talk utterance")
    mode.add_argument("--stream", action="store_true", help="transcribe while listening and stop after silence")
    parser.add_argument("--list-devices", action="store_true", help="list available microphone devices")
    parser.add_argument("--duration", type=float, default=5.0, help="recording duration in seconds")
    parser.add_argument("--silence-duration", type=float, default=3.0, help="seconds of silence that end streaming capture")
    parser.add_argument("--output", type=Path, default=Path("recordings/utterance.wav"))
    parser.add_argument("--device", help="microphone device index or name fragment")
    parser.add_argument("--model-size", default="small.en")
    parser.add_argument(
        "--understanding",
        choices=("rule", "ollama"),
        default="rule",
        help="intent understanding provider",
    )
    parser.add_argument(
        "--understanding-model",
        default="qwen2.5:3b",
        help="local Ollama model used when --understanding ollama is selected",
    )
    parser.add_argument("--vad", choices=("energy", "silero"), default="energy")
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.005,
        help="Energy VAD RMS threshold; lower values detect quieter speech",
    )
    return parser


async def run_text(text: str, args: argparse.Namespace) -> int:
    log("processing text input")
    log(f"transcript: {text!r}")
    result = await pipeline_for(args).process_transcript(text)
    log(f"string sent to agent: {result.command.content.get('instruction', '')!r}")
    log("intent and agent pipeline complete")
    print(json.dumps({"command": result.command.model_dump(mode="json"), "responses": result.responses}))
    return 0


async def run_record(args: argparse.Namespace) -> int:
    log(f"recording for {args.duration:.1f} seconds")
    log("VAD: disabled")
    log(f"ASR model: {args.model_size}")
    log(f"output: {args.output}")

    recorder = AudioRecorder()
    vad = None
    log("VAD: disabled; processing the full recording")
    asr = OpenAIWhisperASR(model_size=args.model_size)
    log("loading ASR model")
    asr.warm_up()
    log("ASR model loaded")
    log(f"CUDA available: {'yes' if asr.cuda_available() else 'no'}")
    log(f"ASR runtime device: {asr.runtime_device}")
    session = PushToTalkSession(
        recorder=recorder,
        vad=vad,
        asr=asr,
        voice_pipeline=pipeline_for(args),
    )

    device = resolve_input_device(args.device)
    if device is not None:
        log(f"microphone device: {device}")

    log("starting microphone recording")
    try:
        result = await session.record_and_process(
            args.duration,
            args.output,
            device=device,
        )
    except KeyboardInterrupt:
        log("recording interrupted before completion")
        return 130
    except RuntimeError as exc:
        log_error(f"recording failed: {exc}")
        return 1
    except ValueError as exc:
        if str(exc) == "no speech detected":
            log("no speech detected; the selected input is silent or below the configured Energy VAD threshold")
        else:
            log_error(str(exc))
        return 1

    log("recording and pipeline processing complete")
    audio = recorder.load_wav(result.audio_path)
    peak, rms = audio_signal(audio)
    log(f"utterance signal: peak={peak}, rms={rms:.1f}, normalized_rms={rms / 32768:.5f}")

    log("push-to-talk processing complete")
    log(f"speech segment: {result.segment.start_time:.2f}s - {result.segment.end_time:.2f}s")
    log(f"audio saved: {result.audio_path}")
    log(f"transcript: {result.transcript.text!r}")
    log(f"string sent to agent: {result.pipeline.command.content.get('instruction', '')!r}")
    log(f"language: {result.transcript.language or 'unknown'}")
    log(f"confidence: {format_optional(result.transcript.confidence)}")
    log(f"responses: {result.pipeline.responses or 'none'}")

    print(
        json.dumps(
            {
                "audio_path": str(result.audio_path),
                "transcript": result.transcript.__dict__,
                "responses": result.pipeline.responses,
            }
        )
    )
    return 0


async def run_stream(args: argparse.Namespace) -> int:
    log("streaming capture started")
    log(f"silence endpoint: {args.silence_duration:.1f} seconds")
    log(f"ASR model: {args.model_size}")
    log(f"output: {args.output}")

    recorder = AudioRecorder()
    asr = OpenAIWhisperASR(model_size=args.model_size)
    log("loading ASR model")
    asr.warm_up()
    log("ASR model loaded")
    log(f"CUDA available: {'yes' if asr.cuda_available() else 'no'}")
    log(f"ASR runtime device: {asr.runtime_device}")
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=asr,
        voice_pipeline=pipeline_for(args),
    )
    device = resolve_input_device(args.device)
    if device is not None:
        log(f"microphone device: {device}")

    log("recording started; speak now")

    try:
        result = await session.record_until_silence_and_process(
            max_duration_seconds=args.duration,
            output_path=args.output,
            silence_duration_seconds=args.silence_duration,
            speech_threshold=args.vad_threshold,
            device=device,
        )
    except KeyboardInterrupt:
        log("streaming recording interrupted before completion")
        return 130
    except RuntimeError as exc:
        log_error(f"streaming recording failed: {exc}")
        return 1
    except ValueError as exc:
        log_error(str(exc))
        return 1

    log("silence endpoint detected")
    log("intent and agent processing complete")
    log(f"audio saved: {result.audio_path}")
    log(f"final transcript: {result.transcript.text!r}")
    log(f"string sent to agent: {result.pipeline.command.content.get('instruction', '')!r}")
    log(f"responses: {result.pipeline.responses or 'none'}")
    print(
        json.dumps(
            {
                "audio_path": str(result.audio_path),
                "transcript": result.transcript.__dict__,
                "responses": result.pipeline.responses,
            }
        )
    )
    return 0



def list_input_devices() -> int:
    import sounddevice as sd

    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            hostapi = sd.query_hostapis(device["hostapi"])["name"]
            print(
                f"{index}: {device['name']} "
                f"[{hostapi}, default rate {device['default_samplerate']:.0f} Hz]"
            )
    return 0



def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.list_devices:
            return list_input_devices()
        if args.text is not None:
            return asyncio.run(run_text(args.text, args))
        if args.record:
            return asyncio.run(run_record(args))
        if args.stream:
            return asyncio.run(run_stream(args))
        build_parser().error("one of --text, --record, --stream, or --list-devices is required")
    except KeyboardInterrupt:
        log("operation interrupted")
        return 130
    except (RuntimeError, ValueError, OSError) as exc:
        log_error(str(exc))
        return 1
    except Exception as exc:
        log_error(f"unexpected failure: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
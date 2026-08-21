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
from voice_gateway.audio import AudioRecorder, EnergySpeechDetector, SileroSpeechDetector
from voice_gateway.pipeline import PushToTalkSession, VoicePipeline
from voice_gateway.routing import ClaudeCodeAgentPlatform, FakeAgentPlatform
from voice_gateway.tts import PiperTTS, SpokenDetail, speak_responses
from voice_gateway.understanding import GeminiAssistant, OllamaAssistant, RuleBasedUnderstanding



def build_understanding(args: argparse.Namespace) -> Any:
    if args.understanding == "gemini":
        return GeminiAssistant(model=args.gemini_model)
    if args.understanding == "ollama" or args.conversation:
        return OllamaAssistant(model=args.ollama_model)
    return RuleBasedUnderstanding()



def build_live_vad(args: argparse.Namespace) -> Any:
    if args.vad == "silero":
        return SileroSpeechDetector(threshold=args.silero_threshold)
    return EnergySpeechDetector(threshold=args.vad_threshold)


def pipeline_for(args: argparse.Namespace) -> VoicePipeline:
    if args.agent_platform == "claude-code":
        if args.agent_workdir is None:
            raise ValueError("--agent-workdir is required when using --agent-platform claude-code")
        agent_platform = ClaudeCodeAgentPlatform(
            workspace=args.agent_workdir,
            model=args.agent_model,
            timeout_seconds=args.agent_timeout,
        )
    else:
        agent_platform = FakeAgentPlatform()
    assistant = build_understanding(args)
    return VoicePipeline(
        understanding=assistant,
        agent_platform=agent_platform,
        conversation_engine=assistant if args.conversation else None,
    )


def speak_pipeline_responses(
    responses: List[str],
    args: argparse.Namespace,
    follow_up: Optional[str] = None,
) -> Optional[Path]:
    if args.tts != "piper":
        return None
    if not args.tts_model.is_file():
        raise ValueError(f"Piper voice model was not found: {args.tts_model}")
    log("synthesizing spoken response with Piper")
    output_path = speak_responses(
        responses,
        PiperTTS(executable=args.tts_executable, model=args.tts_model),
        args.tts_output,
        detail=SpokenDetail(args.spoken_detail),
        follow_up=follow_up,
    )
    if output_path is not None:
        log(f"spoken response played: {output_path}")
    return output_path



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local voice gateway experiments")
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument("--text", help="process a transcript without microphone or model dependencies")
    mode.add_argument("--record", action="store_true", help="record one push-to-talk utterance")
    mode.add_argument("--stream", action="store_true", help="transcribe while listening and stop after silence")
    mode.add_argument("--conversation", action="store_true", help="continue endpointed voice turns until 'end conversation'")
    parser.add_argument("--list-devices", action="store_true", help="list available microphone devices")
    parser.add_argument("--duration", type=float, default=5.0, help="recording duration in seconds")
    parser.add_argument("--silence-duration", type=float, default=3.0, help="seconds of silence that end streaming capture")
    parser.add_argument("--output", type=Path, default=Path("recordings/utterance.wav"))
    parser.add_argument("--device", help="microphone device index or name fragment")
    parser.add_argument("--model-size", default="small.en")
    parser.add_argument(
        "--understanding",
        choices=("rule", "ollama", "gemini"),
        default="rule",
        help="intent understanding provider",
    )
    parser.add_argument(
        "--ollama-model",
        default="qwen3:4b",
        help="shared local Ollama model for intent understanding and conversation",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-3.7-flash",
        help="shared Gemini model for intent understanding and conversation",
    )
    parser.add_argument(
        "--agent-platform",
        choices=("fake", "claude-code"),
        default="fake",
        help="agent backend; Claude Code runs with plan-mode permission",
    )
    parser.add_argument(
        "--agent-workdir",
        type=Path,
        help="explicit workspace for the Claude Code backend",
    )
    parser.add_argument(
        "--agent-timeout",
        type=float,
        default=120.0,
        help="seconds to wait for Claude Code",
    )
    parser.add_argument(
        "--agent-model",
        default="sonnet",
        help="Claude Code model alias",
    )
    parser.add_argument(
        "--tts",
        choices=("none", "piper"),
        default="none",
        help="spoken response backend",
    )
    parser.add_argument(
        "--tts-model",
        type=Path,
        default=Path("models/piper/jarvis-medium.onnx"),
        help="Piper voice model path",
    )
    parser.add_argument(
        "--tts-executable",
        default="piper",
        help="Piper executable path or command",
    )
    parser.add_argument(
        "--tts-output",
        type=Path,
        default=Path("recordings/response.wav"),
        help="WAV file written before response playback",
    )
    parser.add_argument(
        "--spoken-detail",
        choices=tuple(detail.value for detail in SpokenDetail),
        default=SpokenDetail.BRIEF.value,
        help="amount of each response spoken by TTS",
    )
    parser.add_argument("--vad", choices=("energy", "silero"), default="energy")
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.005,
        help="Energy VAD RMS threshold; lower values detect quieter speech",
    )
    parser.add_argument(
        "--silero-threshold",
        type=float,
        default=0.5,
        help="Silero VAD speech probability threshold",
    )
    return parser


async def run_text(text: str, args: argparse.Namespace) -> int:
    log("processing text input")
    log(f"transcript: {text!r}")
    result = await pipeline_for(args).process_transcript(text)
    log(f"string sent to agent: {result.command.content.get('instruction', '')!r}")
    speak_pipeline_responses(result.responses, args)
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
    speak_pipeline_responses(result.pipeline.responses, args)

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
    live_vad = build_live_vad(args)
    if args.vad == "silero":
        log(f"VAD: silero (threshold {args.silero_threshold:.2f})")
        log("loading Silero VAD")
        live_vad.warm_up()
        log("Silero VAD loaded")
    else:
        log(f"VAD: energy (threshold {args.vad_threshold:.4f})")
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

    while True:
        log("recording started; speak now")
        acknowledgement_task: Optional[asyncio.Task] = None

        def speak_acknowledgement(event: Any) -> None:
            nonlocal acknowledgement_task
            acknowledgement = session.voice_pipeline.response_formatter.acknowledgement(event)
            log(f"acknowledgement: {acknowledgement}")
            acknowledgement_task = asyncio.create_task(
                asyncio.to_thread(speak_pipeline_responses, [acknowledgement], args)
            )

        try:
            result = await session.record_until_silence_and_process(
                max_duration_seconds=args.duration,
                output_path=args.output,
                silence_duration_seconds=args.silence_duration,
                speech_threshold=args.vad_threshold,
                speech_detector=live_vad,
                device=device,
                on_agent_started=speak_acknowledgement if args.conversation else None,
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

        if acknowledgement_task is not None:
            await acknowledgement_task
        log("silence endpoint detected")
        log("intent and agent processing complete")
        log(f"audio saved: {result.audio_path}")
        log(f"final transcript: {result.transcript.text!r}")
        log(f"interpreted intent: {result.pipeline.command.content.get('intent', 'unknown')}")
        log(f"agent target: {result.pipeline.command.content.get('target', 'none')}")
        log(f"string sent to agent: {result.pipeline.command.content.get('instruction', '')!r}")
        log(
            "agent lifecycle events: "
            f"{[event.event.value for event in result.pipeline.agent_events] or 'none'}"
        )
        log(f"responses: {result.pipeline.responses or 'none'}")
        speak_pipeline_responses(
            result.pipeline.responses,
            args,
            follow_up=(
                "What would you like to do next?"
                if args.conversation
                and result.pipeline.command.content.get("intent") != "END_CONVERSATION"
                else None
            ),
        )
        print(
            json.dumps(
                {
                    "audio_path": str(result.audio_path),
                    "transcript": result.transcript.__dict__,
                    "responses": result.pipeline.responses,
                }
            )
        )
        if not args.conversation:
            return 0
        if result.pipeline.command.content.get("intent") == "END_CONVERSATION":
            return 0
        if acknowledgement_task is not None:
            log("agent acknowledgement played; awaiting next turn")
        else:
            log("response played; awaiting next turn")



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
        if args.stream or args.conversation:
            return asyncio.run(run_stream(args))
        build_parser().error("one of --text, --record, --stream, --conversation, or --list-devices is required")
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
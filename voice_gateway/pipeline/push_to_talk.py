"""Push-to-talk orchestration for the local voice gateway."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from voice_gateway.asr import ASREngine, Transcript
from voice_gateway.audio import (
    AudioRecorder,
    LiveSpeechDetector,
    SpeechSegment,
    VoiceActivityDetector,
)
from voice_gateway.pipeline.loop import PipelineResult, VoicePipeline


@dataclass
class TranscribedUtterance:
    transcript: Transcript
    audio_path: Path
    segment: SpeechSegment


@dataclass
class PushToTalkResult(TranscribedUtterance):
    pipeline: PipelineResult


class PushToTalkSession:
    def __init__(
        self,
        recorder: AudioRecorder,
        vad: Optional[VoiceActivityDetector],
        asr: ASREngine,
        voice_pipeline: VoicePipeline,
    ) -> None:
        self.recorder = recorder
        self.vad = vad
        self.asr = asr
        self.voice_pipeline = voice_pipeline

    def transcribe_audio(
        self,
        audio: bytes,
        output_path: Path,
    ) -> TranscribedUtterance:
        if self.vad is None:
            segment = SpeechSegment(
                start_frame=0,
                end_frame=len(audio) // (
                    self.recorder.config.channels * self.recorder.config.sample_width
                ),
                sample_rate=self.recorder.config.sample_rate,
            )
        else:
            segments = self.vad.detect(audio, self.recorder.config.sample_rate)
            if not segments:
                raise ValueError("no speech detected")
            segment = segments[0]
        frame_width = self.recorder.config.channels * self.recorder.config.sample_width
        start_byte = segment.start_frame * frame_width
        end_byte = segment.end_frame * frame_width
        utterance = audio[start_byte:end_byte]
        audio_path = self.recorder.save_wav(output_path, utterance)
        transcript = self.asr.transcribe(audio_path, self.recorder.config.sample_rate)
        return TranscribedUtterance(
            transcript=transcript,
            audio_path=audio_path,
            segment=segment,
        )

    async def process_audio(
        self,
        audio: bytes,
        output_path: Path,
        context: Optional[Dict[str, Any]] = None,
        on_agent_started: Optional[Callable[[Any], None]] = None,
    ) -> PushToTalkResult:
        utterance = self.transcribe_audio(audio, output_path)
        pipeline = await self.voice_pipeline.process_transcript(
            utterance.transcript.text,
            context,
            on_agent_started=on_agent_started,
        )
        return PushToTalkResult(
            transcript=utterance.transcript,
            audio_path=utterance.audio_path,
            segment=utterance.segment,
            pipeline=pipeline,
        )

    async def record_and_process(
        self,
        duration_seconds: float,
        output_path: Path,
        context: Optional[Dict[str, Any]] = None,
        device: Optional[Any] = None,
        on_agent_started: Optional[Callable[[Any], None]] = None,
    ) -> PushToTalkResult:
        audio = self.recorder.record(duration_seconds, device=device)
        return await self.process_audio(
            audio,
            output_path,
            context,
            on_agent_started=on_agent_started,
        )

    async def record_until_silence_and_transcribe(
        self,
        max_duration_seconds: float,
        output_path: Path,
        silence_duration_seconds: float = 3.0,
        speech_threshold: float = 0.003,
        speech_detector: Optional[LiveSpeechDetector] = None,
        device: Optional[Any] = None,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
        on_capture_complete: Optional[Callable[[], None]] = None,
    ) -> TranscribedUtterance:
        audio = await asyncio.to_thread(
            self.recorder.record_until_silence,
            max_duration_seconds=max_duration_seconds,
            silence_duration_seconds=silence_duration_seconds,
            speech_threshold=speech_threshold,
            speech_detector=speech_detector,
            device=device,
            on_chunk=on_audio_chunk,
        )
        if on_capture_complete is not None:
            on_capture_complete()
        return self.transcribe_audio(audio, output_path)

    async def record_until_silence_and_process(
        self,
        max_duration_seconds: float,
        output_path: Path,
        silence_duration_seconds: float = 3.0,
        speech_threshold: float = 0.003,
        speech_detector: Optional[LiveSpeechDetector] = None,
        context: Optional[Dict[str, Any]] = None,
        device: Optional[Any] = None,
        on_agent_started: Optional[Callable[[Any], None]] = None,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
        on_capture_complete: Optional[Callable[[], None]] = None,
    ) -> PushToTalkResult:
        utterance = await self.record_until_silence_and_transcribe(
            max_duration_seconds=max_duration_seconds,
            output_path=output_path,
            silence_duration_seconds=silence_duration_seconds,
            speech_threshold=speech_threshold,
            speech_detector=speech_detector,
            device=device,
            on_audio_chunk=on_audio_chunk,
            on_capture_complete=on_capture_complete,
        )
        pipeline = await self.voice_pipeline.process_transcript(
            utterance.transcript.text,
            context,
            on_agent_started=on_agent_started,
        )
        return PushToTalkResult(
            transcript=utterance.transcript,
            audio_path=utterance.audio_path,
            segment=utterance.segment,
            pipeline=pipeline,
        )
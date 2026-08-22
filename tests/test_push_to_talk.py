import math
import struct

import pytest

from voice_gateway.asr import Transcript
from voice_gateway.audio import AudioRecorder, EnergyVAD
from voice_gateway.pipeline import PushToTalkSession, VoicePipeline


def tone(duration_seconds, amplitude=12000, sample_rate=16000, frequency=440):
    count = int(duration_seconds * sample_rate)
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)))
        for i in range(count)
    )


def silence(duration_seconds, sample_rate=16000):
    return b"\x00\x00" * int(duration_seconds * sample_rate)


class FakeASR:
    def transcribe(self, audio, sample_rate=16000):
        return Transcript(text="Tell Claude to check the research folder", language="en")


class FakeRecorder(AudioRecorder):
    def __init__(self, audio):
        super().__init__()
        self.audio = audio
        self.recorded_device = "not-called"
        self.stream_kwargs = None

    def record(self, duration_seconds, device=None):
        self.recorded_device = device
        return self.audio

    def record_until_silence(
        self,
        max_duration_seconds,
        silence_duration_seconds=2.0,
        speech_threshold=0.003,
        chunk_duration_ms=100,
        device=None,
        on_chunk=None,
        speech_detector=None,
    ):
        self.stream_kwargs = {
            "max_duration_seconds": max_duration_seconds,
            "silence_duration_seconds": silence_duration_seconds,
            "speech_threshold": speech_threshold,
            "speech_detector": speech_detector,
            "device": device,
        }
        chunks = [self.audio[: len(self.audio) // 2], self.audio[len(self.audio) // 2 :]]
        for chunk in chunks:
            if on_chunk is not None:
                on_chunk(chunk)
        return self.audio


class RecordingUnderstanding:
    def __init__(self):
        self.seen = []

    def interpret(self, transcript, context=None):
        self.seen.append(transcript)
        from voice_gateway.understanding import RuleBasedUnderstanding

        return RuleBasedUnderstanding().interpret("Tell Claude to check the research folder", context)


@pytest.mark.asyncio
async def test_streaming_transcribes_and_interprets_only_after_capture_ends(tmp_path):
    recorder = FakeRecorder(tone(0.4))
    asr = FakeASR()
    understanding = RecordingUnderstanding()
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=asr,
        voice_pipeline=VoicePipeline(understanding=understanding),
    )

    result = await session.record_until_silence_and_process(
        max_duration_seconds=5.0,
        output_path=tmp_path / "stream.wav",
        silence_duration_seconds=3.0,
        device="stream-device",
    )

    assert understanding.seen == ["Tell Claude to check the research folder"]
    assert recorder.stream_kwargs["device"] == "stream-device"
    assert result.pipeline.responses == ["Task completed."]


@pytest.mark.asyncio
async def test_streaming_can_transcribe_without_processing_intent(tmp_path):
    recorder = FakeRecorder(tone(0.2))
    understanding = RecordingUnderstanding()
    calls = []
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(understanding=understanding),
    )

    result = await session.record_until_silence_and_transcribe(
        max_duration_seconds=1.0,
        output_path=tmp_path / "standby.wav",
        on_audio_chunk=lambda chunk: calls.append("chunk"),
        on_capture_complete=lambda: calls.append("complete"),
    )

    assert result.transcript.text == "Tell Claude to check the research folder"
    assert calls == ["chunk", "chunk", "complete"]
    assert understanding.seen == []


@pytest.mark.asyncio
async def test_streaming_forwards_audio_chunks_before_capture_complete(tmp_path):
    recorder = FakeRecorder(tone(0.2))
    calls = []
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    await session.record_until_silence_and_process(
        max_duration_seconds=1.0,
        output_path=tmp_path / "stream.wav",
        on_audio_chunk=lambda chunk: calls.append(("chunk", chunk)),
        on_capture_complete=lambda: calls.append(("complete", None)),
    )

    assert [kind for kind, _ in calls] == ["chunk", "chunk", "complete"]
    assert b"".join(chunk for kind, chunk in calls if kind == "chunk") == recorder.audio


@pytest.mark.asyncio
async def test_streaming_does_not_call_asr_from_capture_callback(tmp_path):
    class CallbackTrackingRecorder(FakeRecorder):
        def record_until_silence(self, *args, on_chunk=None, **kwargs):
            assert on_chunk is None
            return super().record_until_silence(*args, on_chunk=on_chunk, **kwargs)

    session = PushToTalkSession(
        recorder=CallbackTrackingRecorder(tone(0.1)),
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    await session.record_until_silence_and_process(
        max_duration_seconds=1.0,
        output_path=tmp_path / "stream.wav",
    )


@pytest.mark.asyncio
async def test_streaming_forwards_live_speech_detector(tmp_path):
    recorder = FakeRecorder(tone(0.1))
    detector = object()
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    await session.record_until_silence_and_process(
        max_duration_seconds=4.0,
        output_path=tmp_path / "stream.wav",
        speech_detector=detector,
    )

    assert recorder.stream_kwargs["speech_detector"] is detector


@pytest.mark.asyncio
async def test_streaming_forwards_endpoint_parameters(tmp_path):
    recorder = FakeRecorder(tone(0.1))
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    await session.record_until_silence_and_process(
        max_duration_seconds=4.0,
        output_path=tmp_path / "stream.wav",
        silence_duration_seconds=1.5,
        speech_threshold=0.01,
        device=7,
    )

    assert recorder.stream_kwargs == {
        "max_duration_seconds": 4.0,
        "silence_duration_seconds": 1.5,
        "speech_threshold": 0.01,
        "speech_detector": None,
        "device": 7,
    }


@pytest.mark.asyncio
async def test_push_to_talk_connects_audio_to_pipeline(tmp_path):
    session = PushToTalkSession(
        recorder=AudioRecorder(),
        vad=EnergyVAD(),
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )
    audio = silence(0.2) + tone(0.3) + silence(0.3)

    result = await session.process_audio(audio, tmp_path / "utterance.wav")

    assert result.audio_path.exists()
    assert result.transcript.text.startswith("Tell Claude")
    assert result.pipeline.command.content["target"] == "claude"
    assert result.pipeline.responses == ["Task completed."]


@pytest.mark.asyncio
async def test_push_to_talk_can_process_full_recording_without_vad(tmp_path):
    recorder = FakeRecorder(silence(0.2) + tone(0.3) + silence(0.3))
    session = PushToTalkSession(
        recorder=recorder,
        vad=None,
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    result = await session.process_audio(
        recorder.audio,
        tmp_path / "full-recording.wav",
    )

    assert result.segment.start_frame == 0
    assert result.segment.end_frame == len(recorder.audio) // 2
    assert result.audio_path.exists()


@pytest.mark.asyncio
async def test_record_and_process_forwards_microphone_device(tmp_path):
    recorder = FakeRecorder(silence(0.2) + tone(0.3) + silence(0.3))
    session = PushToTalkSession(
        recorder=recorder,
        vad=EnergyVAD(),
        asr=FakeASR(),
        voice_pipeline=VoicePipeline(),
    )

    result = await session.record_and_process(
        1.0,
        tmp_path / "utterance.wav",
        device="default-test-device",
    )

    assert recorder.recorded_device == "default-test-device"
    assert result.pipeline.command.content["target"] == "claude"
    assert result.audio_path.exists()

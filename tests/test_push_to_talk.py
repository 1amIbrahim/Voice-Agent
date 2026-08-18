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

    def record(self, duration_seconds, device=None):
        self.recorded_device = device
        return self.audio


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

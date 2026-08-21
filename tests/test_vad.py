import math
import struct

import pytest

from voice_gateway.audio import (
    EnergySpeechDetector,
    EnergyVAD,
    EnergyVADConfig,
    SileroSpeechDetector,
)


def tone(duration_seconds, amplitude=12000, sample_rate=16000, frequency=440):
    count = int(duration_seconds * sample_rate)
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)))
        for i in range(count)
    )


def silence(duration_seconds, sample_rate=16000):
    return b"\x00\x00" * int(duration_seconds * sample_rate)


class FakeWaveform(list):
    def __truediv__(self, divisor):
        return self


class FakeTorch:
    float32 = "float32"

    @staticmethod
    def tensor(samples, dtype):
        return FakeWaveform(samples)


class FakeIterator:
    def __init__(self, events):
        self.events = iter(events)
        self.calls = 0
        self.reset_count = 0

    def __call__(self, waveform):
        self.calls += 1
        return next(self.events, None)

    def reset_states(self):
        self.reset_count += 1


class StubSileroSpeechDetector(SileroSpeechDetector):
    def __init__(self, iterator):
        super().__init__()
        self._torch = FakeTorch()
        self._iterator = iterator

    def _load(self):
        return None


class MissingSileroSpeechDetector(SileroSpeechDetector):
    def _load(self):
        raise RuntimeError(
            "Silero live VAD requires the optional 'silero-vad' and 'torchaudio' packages"
        )


def test_energy_vad_detects_speech_between_silence():
    audio = silence(0.3) + tone(0.3) + silence(0.4)
    segments = EnergyVAD().detect(audio)

    assert len(segments) == 1
    assert 0.27 <= segments[0].start_time <= 0.33
    assert 0.54 <= segments[0].end_time <= 0.66


def test_energy_vad_ignores_short_speech():
    audio = silence(0.2) + tone(0.03) + silence(0.4)

    assert EnergyVAD().detect(audio) == []


def test_energy_vad_detects_quiet_microphone_audio():
    audio = silence(0.3) + tone(0.3, amplitude=400) + silence(0.4)

    assert len(EnergyVAD().detect(audio)) == 1


def test_energy_vad_rejects_odd_pcm16_bytes():
    with pytest.raises(ValueError, match="even number"):
        EnergyVAD().detect(b"\x00")


def test_energy_vad_default_detects_quiet_speech_fixture():
    audio = silence(0.2) + tone(0.2, amplitude=400) + silence(0.3)

    assert EnergyVAD().detect(audio)


def test_vad_config_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="speech_threshold"):
        EnergyVAD(EnergyVADConfig(speech_threshold=0))


def test_energy_live_detector_uses_configured_threshold():
    detector = EnergySpeechDetector(threshold=0.01)

    assert detector.process(tone(0.1, amplitude=1000)) is True
    assert detector.process(tone(0.1, amplitude=10)) is False


def test_silero_live_detector_buffers_to_512_sample_frames():
    iterator = FakeIterator([{"start": 0}, {"end": 0}, None])
    detector = StubSileroSpeechDetector(iterator)

    assert detector.process(b"\x00\x00" * 400) is False
    assert detector.process(b"\x00\x00" * 112) is True
    assert iterator.calls == 1
    assert detector.process(b"\x00\x00" * 1024) is False
    assert iterator.calls == 3


def test_silero_live_detector_reset_clears_model_state():
    iterator = FakeIterator([])
    detector = StubSileroSpeechDetector(iterator)

    detector.reset()

    assert iterator.reset_count == 1


def test_silero_live_detector_requires_16khz_pcm16_audio():
    detector = StubSileroSpeechDetector(FakeIterator([]))

    with pytest.raises(ValueError, match="16000"):
        detector.process(b"\x00\x00" * 512, sample_rate=8000)
    with pytest.raises(ValueError, match="even number"):
        detector.process(b"\x00")


def test_silero_live_detector_reports_missing_dependencies():
    with pytest.raises(RuntimeError, match="Silero live VAD requires"):
        MissingSileroSpeechDetector().warm_up()

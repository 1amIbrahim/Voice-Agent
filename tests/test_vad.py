import math
import struct

import pytest

from voice_gateway.audio import EnergyVAD, EnergyVADConfig, SileroVAD


def tone(duration_seconds, amplitude=12000, sample_rate=16000, frequency=440):
    count = int(duration_seconds * sample_rate)
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)))
        for i in range(count)
    )


def silence(duration_seconds, sample_rate=16000):
    return b"\x00\x00" * int(duration_seconds * sample_rate)


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


def test_silero_adapter_reports_missing_optional_dependency():
    with pytest.raises(RuntimeError, match="Silero VAD requires"):
        SileroVAD().detect(tone(0.2))

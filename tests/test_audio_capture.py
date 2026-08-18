import math
import struct
import wave

import pytest

from voice_gateway.audio import AudioConfig, AudioRecorder


def sine_wave(duration_seconds=0.1, sample_rate=16000, frequency=440):
    samples = int(duration_seconds * sample_rate)
    return b"".join(
        struct.pack("<h", int(12000 * math.sin(2 * math.pi * frequency * i / sample_rate)))
        for i in range(samples)
    )


def test_default_audio_config_is_16khz_mono_pcm16():
    assert AudioConfig() == AudioConfig(sample_rate=16000, channels=1, sample_width=2)


def test_save_and_load_wav_round_trip(tmp_path):
    recorder = AudioRecorder()
    audio = sine_wave()
    path = recorder.save_wav(tmp_path / "sample.wav", audio)

    assert path.exists()
    assert recorder.load_wav(path) == audio

    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2


def test_load_rejects_wrong_wav_format(tmp_path):
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00\x00\x00")

    with pytest.raises(ValueError, match="does not match"):
        AudioRecorder().load_wav(path)


def test_invalid_duration_is_rejected():
    with pytest.raises(ValueError, match="duration_seconds"):
        AudioRecorder().record(0)

import math
import struct
import sys
import types
import wave

import pytest


def _pcm16_tone(duration_seconds=0.1, sample_rate=16000, amplitude=12000, frequency=440):
    samples = int(duration_seconds * sample_rate)
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)))
        for i in range(samples)
    )


def _pcm16_silence(duration_seconds=0.1, sample_rate=16000):
    return b"\x00\x00" * int(duration_seconds * sample_rate)


class _FakeInputStream:
    def __init__(self, *, callback, **kwargs):
        self.callback = callback
        self.kwargs = kwargs

    def __enter__(self):
        for chunk in self.kwargs["chunks"]:
            self.callback(types.SimpleNamespace(tobytes=lambda chunk=chunk: chunk), 0, None, None)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _fake_sounddevice(chunks):
    return types.SimpleNamespace(
        InputStream=lambda **kwargs: _FakeInputStream(chunks=chunks, **kwargs),
    )

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


def test_record_until_silence_stops_after_silence(monkeypatch):
    chunks = [
        _pcm16_silence(0.1),
        _pcm16_tone(0.1),
        _pcm16_silence(0.1),
        _pcm16_silence(0.1),
    ]
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sounddevice(chunks))
    received = []

    audio = AudioRecorder().record_until_silence(
        max_duration_seconds=1.0,
        silence_duration_seconds=0.2,
        chunk_duration_ms=100,
        speech_threshold=0.003,
        on_chunk=received.append,
    )

    assert received == chunks
    assert audio == b"".join(chunks)


def test_record_until_silence_uses_live_speech_detector(monkeypatch):
    chunks = [
        _pcm16_silence(0.1),
        _pcm16_tone(0.1),
        _pcm16_silence(0.1),
        _pcm16_silence(0.1),
    ]
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sounddevice(chunks))

    class Detector:
        def __init__(self):
            self.reset_called = False
            self.calls = 0

        def reset(self):
            self.reset_called = True

        def process(self, audio, sample_rate):
            self.calls += 1
            return self.calls == 2

    detector = Detector()
    audio = AudioRecorder().record_until_silence(
        max_duration_seconds=1.0,
        silence_duration_seconds=0.2,
        speech_detector=detector,
    )

    assert detector.reset_called is True
    assert detector.calls == 4
    assert audio == b"".join(chunks)


def test_record_until_silence_rejects_non_pcm16():
    recorder = AudioRecorder(AudioConfig(sample_width=1))
    with pytest.raises(ValueError, match="mono PCM16"):
        recorder.record_until_silence(1.0)


def test_record_until_silence_requires_positive_silence_duration():
    with pytest.raises(ValueError, match="silence_duration_seconds"):
        AudioRecorder().record_until_silence(1.0, silence_duration_seconds=0)


def test_record_until_silence_requires_positive_threshold():
    with pytest.raises(ValueError, match="speech_threshold"):
        AudioRecorder().record_until_silence(1.0, speech_threshold=0)


def test_record_until_silence_requires_positive_chunk_duration():
    with pytest.raises(ValueError, match="chunk_duration_ms"):
        AudioRecorder().record_until_silence(1.0, chunk_duration_ms=0)


def test_record_until_silence_reports_chunks(monkeypatch):
    chunks = [_pcm16_tone(0.1), _pcm16_silence(0.1)]
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sounddevice(chunks))
    received = []

    AudioRecorder().record_until_silence(
        max_duration_seconds=1.0,
        silence_duration_seconds=1.0,
        on_chunk=received.append,
    )

    assert received == chunks

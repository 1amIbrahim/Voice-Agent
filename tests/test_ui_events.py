import json
import math
import struct

import pytest

from voice_gateway.ui import VoiceEventServer, normalized_pcm16_rms


def pcm16_tone(amplitude: int, sample_count: int = 100) -> bytes:
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * index / 20)))
        for index in range(sample_count)
    )


def test_normalized_pcm16_rms_handles_silence_and_clamps_loud_audio():
    assert normalized_pcm16_rms(b"") == 0.0
    assert normalized_pcm16_rms(b"\x00\x00" * 100) == 0.0
    assert 0 < normalized_pcm16_rms(pcm16_tone(1000)) < 1
    assert normalized_pcm16_rms(pcm16_tone(32767)) == 1.0


def test_voice_event_server_serializes_state_and_clamped_level():
    server = VoiceEventServer(0)
    client = server._subscribe()

    server.publish_state("listening")
    server.publish_level(2.0)

    assert json.loads(client.get_nowait()) == {
        "type": "voice.state",
        "state": "listening",
    }
    assert json.loads(client.get_nowait()) == {
        "type": "voice.level",
        "level": 1.0,
    }


def test_voice_event_server_rejects_nonlocal_bind_and_unknown_state():
    with pytest.raises(ValueError, match="127.0.0.1"):
        VoiceEventServer(8765, host="0.0.0.0")

    server = VoiceEventServer(0)
    with pytest.raises(ValueError, match="unsupported voice state"):
        server.publish_state("recording")


def test_voice_event_server_starts_and_closes():
    server = VoiceEventServer(0)

    server.start()

    assert server.bound_port > 0
    server.close()

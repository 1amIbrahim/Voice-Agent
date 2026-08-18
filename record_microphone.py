import argparse
import wave
from pathlib import Path

import sounddevice as sd


SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Record audio from the default microphone")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=Path("recordings/microphone_test.wav"))
    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be greater than zero")

    frames = int(args.duration * SAMPLE_RATE)
    print(f"Recording from the default microphone for {args.duration:.1f} seconds...")
    recording = sd.rec(
        frames,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(args.output), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(recording.tobytes())

    print(f"Recording saved to {args.output}")


if __name__ == "__main__":
    main()

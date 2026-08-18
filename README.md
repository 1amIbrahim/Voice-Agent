# Voice Gateway

A local-first voice gateway built incrementally from independently tested modules.

## Current queue

1. Audio capture and WAV persistence
2. Voice activity detection
3. Automatic speech recognition
4. Structured intent understanding
5. Intent/event protocol
6. Fake-agent event loop
7. Text-to-speech
8. Integrated push-to-talk loop

Run tests with:

```text
python -m pytest
```

Live microphone recording requires the optional `sounddevice` dependency.

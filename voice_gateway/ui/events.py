"""Localhost-only server-sent events for voice visualization."""

import array
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import queue
from threading import Lock, Thread
from typing import Any, Dict, Optional


_ALLOWED_STATES = {"idle", "listening", "processing", "speaking"}
_STOP = object()


def normalized_pcm16_rms(audio: bytes, gain: float = 8.0) -> float:
    samples = array.array("h")
    samples.frombytes(audio)
    if not samples:
        return 0.0
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    return max(0.0, min(1.0, rms / 32768 * gain))


class VoiceEventServer:
    def __init__(self, port: int, host: str = "127.0.0.1") -> None:
        if not 0 <= port <= 65535:
            raise ValueError("UI events port must be between 0 and 65535")
        if host != "127.0.0.1":
            raise ValueError("UI event server must bind to 127.0.0.1")
        self.host = host
        self.port = port
        self._clients: set[queue.Queue[object]] = set()
        self._lock = Lock()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[Thread] = None
        self._state = "idle"
        self._level = 0.0

    @property
    def bound_port(self) -> int:
        return self._server.server_port if self._server is not None else self.port

    def start(self) -> None:
        if self._server is not None:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:
                if self.path != "/events":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                client = owner._subscribe()
                try:
                    self.wfile.write(b": connected\n\n")
                    self.wfile.write(
                        b"data: "
                        + owner._encode({"type": "voice.state", "state": owner._state})
                        + b"\n\n"
                    )
                    self.wfile.write(
                        b"data: "
                        + owner._encode({"type": "voice.level", "level": owner._level})
                        + b"\n\n"
                    )
                    self.wfile.flush()
                    while True:
                        try:
                            item = client.get(timeout=15)
                        except queue.Empty:
                            self.wfile.write(b": heartbeat\n\n")
                            self.wfile.flush()
                            continue
                        if item is _STOP:
                            break
                        self.wfile.write(b"data: " + item + b"\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    owner._unsubscribe(client)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._server.daemon_threads = True
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def publish_state(self, state: str) -> None:
        if state not in _ALLOWED_STATES:
            raise ValueError(f"unsupported voice state: {state}")
        self._state = state
        self._broadcast({"type": "voice.state", "state": state})

    def publish_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self._broadcast({"type": "voice.level", "level": self._level})

    def close(self) -> None:
        if self._server is None:
            return
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            client.put(_STOP)
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._server = None
        self._thread = None

    @staticmethod
    def _encode(payload: Dict[str, Any]) -> bytes:
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def _broadcast(self, payload: Dict[str, Any]) -> None:
        encoded = self._encode(payload)
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            client.put(encoded)

    def _subscribe(self) -> queue.Queue[object]:
        client: queue.Queue[object] = queue.Queue()
        with self._lock:
            self._clients.add(client)
        return client

    def _unsubscribe(self, client: queue.Queue[object]) -> None:
        with self._lock:
            self._clients.discard(client)

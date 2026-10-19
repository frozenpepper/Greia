from __future__ import annotations

from contextlib import closing
import json
import socket
from typing import Callable

from .models import SpeechKind, VerificationMode, VoiceRequest


MAX_REQUEST_BYTES = 64 * 1024


def request_from_mapping(payload: dict) -> VoiceRequest:
    output = payload.get("output")
    from pathlib import Path
    return VoiceRequest(
        speaker=str(payload["speaker"]),
        kind=SpeechKind(str(payload["kind"])),
        locale=str(payload["locale"]),
        text=str(payload["text"]),
        cue_id=str(payload["cue_id"]) if payload.get("cue_id") is not None else None,
        output=Path(output) if output else None,
        verification=VerificationMode(str(payload.get("verification", "auto"))),
        max_attempts=int(payload.get("max_attempts", 2)),
    )


def serve_loop(host: str, port: int, handler: Callable[[VoiceRequest], dict]) -> None:
    """Run a deliberately single-threaded localhost JSON service.

    Single-threaded handling is a correctness constraint for MLX/Metal memory: one
    process owns one model instance and serializes generation requests. The service
    is authoring-local only and must never be exposed on a LAN interface.
    """
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Greia voice service may bind only to localhost")
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(8)
        while True:
            conn, _ = server.accept()
            with conn:
                data = b""
                while len(data) < MAX_REQUEST_BYTES:
                    chunk = conn.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                try:
                    payload = json.loads(data.decode("utf-8").strip())
                    if payload == {"command": "shutdown"}:
                        conn.sendall(b'{"ok":true,"shutdown":true}\n')
                        return
                    result = handler(request_from_mapping(payload))
                    response = {"ok": True, "result": result}
                except Exception as exc:
                    response = {"ok": False, "error": str(exc)}
                conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))


def send_request(host: str, port: int, payload: dict, response_timeout: float = 3600) -> dict:
    if not 1 <= response_timeout <= 7200:
        raise ValueError("response timeout must be between 1 and 7200 seconds")
    wire = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    if len(wire) > MAX_REQUEST_BYTES:
        raise ValueError("request exceeds Greia voice service size limit")
    with closing(socket.create_connection((host, port), timeout=10.0)) as conn:
        # Connecting should fail promptly, but queued synthesis can legitimately
        # take minutes. A ten-second read deadline encouraged duplicate requests.
        conn.settimeout(response_timeout)
        conn.sendall(wire)
        response = b""
        while b"\n" not in response:
            chunk = conn.recv(8192)
            if not chunk:
                break
            response += chunk
    return json.loads(response.decode("utf-8"))

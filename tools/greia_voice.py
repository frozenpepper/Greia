#!/usr/bin/env python3
"""Greia authoring-time voice production CLI.

This is the only production entry point Activity/OS/Encyclopedia authoring agents
should need. It routes semantic speech requests to canonical providers and keeps
VoxStage/Chatterbox mechanics, native TTS quirks, Whisper verification and receipts behind
one Greia-owned contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from greia_voice_core import SpeechKind, VerificationMode, VoiceEngine, VoiceRegistry, VoiceRequest
from greia_voice_core.audio import AudioPipeline
from greia_voice_core.composition import CHARACTER_PROVIDERS, build_providers, selected_character_provider
from greia_voice_core.locking import GenerationLockError, InterprocessGenerationLock, NullGenerationLock
from greia_voice_core.paths import voice_home
from greia_voice_core.registry import VoiceRegistryError
from greia_voice_core.providers import (
    ChatterboxMLXProvider,
)
from greia_voice_core.service import request_from_mapping, send_request, serve_loop
from greia_voice_core.verification import WhisperVerifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 43841


def build_engine(generation_lock: object | None = None, character_provider: str | None = None) -> VoiceEngine:
    registry = VoiceRegistry.load(PROJECT_ROOT)
    return VoiceEngine(
        project_root=PROJECT_ROOT,
        registry=registry,
        providers=build_providers(character_provider),
        verifier=WhisperVerifier(),
        audio_pipeline=AudioPipeline(),
        generation_lock=generation_lock,
    )


def _request_from_args(args: argparse.Namespace) -> VoiceRequest:
    return VoiceRequest(
        speaker=args.speaker,
        kind=SpeechKind(args.kind),
        locale=args.locale,
        text=args.text,
        cue_id=args.cue_id,
        output=Path(args.output) if args.output else None,
        verification=VerificationMode(args.verification),
        max_attempts=args.max_attempts,
        delivery_prompt=args.delivery_prompt,
        ignore_accents=not args.strict_accents,
        short_text_mode=args.short_text_mode,
        short_text_max_words=args.short_text_max_words,
        short_text_max_alnum=args.short_text_max_alnum,
    )


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_doctor(args: argparse.Namespace) -> int:
    registry = VoiceRegistry.load(PROJECT_ROOT)
    anchor_status = {}
    for name, profile in registry.profiles.items():
        if profile.anchor_path is None:
            anchor_status[name] = {"required": False, "ok": True}
            continue
        try:
            registry.verify_anchor(profile)
            anchor_status[name] = {"required": True, "ok": True, "path": str(profile.anchor_path)}
        except Exception as exc:
            anchor_status[name] = {"required": True, "ok": False, "detail": str(exc)}

    selected = selected_character_provider(args.character_provider)
    providers = list(build_providers(selected))
    if selected != "chatterbox":
        providers.append(ChatterboxMLXProvider())
    verifier = WhisperVerifier()
    verifier_ok, verifier_detail = verifier.probe()
    provider_statuses = [provider.probe().to_dict() for provider in providers]
    character_ready = (
        all(row["ok"] for row in anchor_status.values())
        and AudioPipeline.ffmpeg_available()
        and provider_statuses[0]["available"]
    )
    payload = {
        "registry_version": registry.registry_version,
        "default_character_provider": "voxstage",
        "selected_character_provider": selected,
        "character_production_ready": bool(character_ready),
        "anchors": anchor_status,
        "ffmpeg": {"available": AudioPipeline.ffmpeg_available()},
        "providers": provider_statuses,
        "verifier": {"id": verifier.verifier_id, "available": verifier_ok, "detail": verifier_detail},
    }
    _print(payload)
    return 0 if character_ready else 2


def cmd_generate(args: argparse.Namespace) -> int:
    with build_engine(character_provider=args.character_provider) as engine:
        result = engine.generate(_request_from_args(args))
    _print(result.to_dict())
    return 0 if result.output_path is not None else 2


def cmd_batch(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    results = []
    # Hold the global worker lock for the entire batch so no second process can
    # load another multi-GB model while this engine keeps its model warm.
    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        with build_engine(generation_lock=NullGenerationLock(), character_provider=args.character_provider) as engine:
            for line_number, raw in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
                if not raw.strip() or raw.lstrip().startswith("#"):
                    continue
                try:
                    request = request_from_mapping(json.loads(raw))
                    result = engine.generate(request)
                    results.append({"line": line_number, **result.to_dict()})
                except Exception as exc:
                    results.append({"line": line_number, "disposition": "REJECTED", "detail": str(exc)})
    _print(results)
    return 0 if results and all(row.get("output_path") for row in results) else 2


def cmd_serve(args: argparse.Namespace) -> int:
    # The daemon owns the global worker lock for its whole lifetime. That prevents
    # an idle warm daemon and a one-shot/batch process from holding two model copies.
    with InterprocessGenerationLock(voice_home() / "generation.lock"):
        engine = build_engine(generation_lock=NullGenerationLock(), character_provider=args.character_provider)
        try:
            print(
                json.dumps(
                    {"status": "READY", "host": args.host, "port": args.port, "single_worker": True, "character_provider": selected_character_provider(args.character_provider)}
                ),
                flush=True,
            )
            serve_loop(args.host, args.port, lambda request: engine.generate(request).to_dict())
        finally:
            engine.close()
    return 0


def cmd_request(args: argparse.Namespace) -> int:
    payload = _request_from_args(args).to_dict()
    response = send_request(args.host, args.port, payload, response_timeout=args.timeout)
    _print(response)
    if not response.get("ok"):
        return 2
    result = response.get("result", {})
    return 0 if result.get("output_path") else 2


def cmd_shutdown(args: argparse.Namespace) -> int:
    response = send_request(args.host, args.port, {"command": "shutdown"})
    _print(response)
    return 0 if response.get("ok") else 2


def add_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--speaker", required=True, help="leo/lilli/flash/tito/momo/dani/pedagogical")
    parser.add_argument("--kind", required=True, choices=[kind.value for kind in SpeechKind])
    parser.add_argument("--locale", required=True, help="BCP-47 locale, e.g. it or en")
    parser.add_argument("--text", required=True, help="exact reviewed text to synthesize")
    parser.add_argument("--cue-id")
    parser.add_argument("--delivery-prompt", default="", help="acting direction, separate from spoken words; VoxStage only")
    parser.add_argument("--output", help="optional absolute or repository-relative .wav/.ogg path")
    parser.add_argument(
        "--verification",
        default=VerificationMode.AUTO.value,
        choices=[mode.value for mode in VerificationMode],
    )
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--short-text-mode", choices=("auto", "off", "on"), default="auto")
    parser.add_argument("--short-text-max-words", type=int, default=4,
                        help="automatic carrier threshold, inclusive (default: fewer than five words)")
    parser.add_argument("--short-text-max-alnum", type=int,
                        help="optional additional Unicode letter/digit limit")
    parser.add_argument("--strict-accents", action="store_true",
                        help="treat ASR diacritic differences as errors (default ignores them)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Greia semantic voice production tool")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="non-mutating provider/reference readiness probe")
    doctor.set_defaults(func=cmd_doctor)

    generate = sub.add_parser("generate", help="generate one review asset")
    add_request_arguments(generate)
    generate.set_defaults(func=cmd_generate)

    batch = sub.add_parser("batch", help="generate newline-delimited JSON requests with one loaded model")
    batch.add_argument("--input", required=True)
    batch.set_defaults(func=cmd_batch)

    serve = sub.add_parser("serve", help="run a single-worker localhost service and keep models warm")
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.set_defaults(func=cmd_serve)

    for command in (doctor, generate, batch, serve):
        command.add_argument(
            "--character-provider", choices=CHARACTER_PROVIDERS,
            help="operator choice for character speech; defaults to GREIA_VOICE_CHARACTER_PROVIDER or voxstage",
        )

    request = sub.add_parser("request", help="send one semantic request to a running service")
    request.add_argument("--host", default=DEFAULT_HOST)
    request.add_argument("--port", type=int, default=DEFAULT_PORT)
    request.add_argument("--timeout", type=float, default=3600, help="bounded response wait in seconds (1–7200); generation may take minutes")
    add_request_arguments(request)
    request.set_defaults(func=cmd_request)

    shutdown = sub.add_parser("shutdown", help="cleanly stop a running voice service")
    shutdown.add_argument("--host", default=DEFAULT_HOST)
    shutdown.add_argument("--port", type=int, default=DEFAULT_PORT)
    shutdown.set_defaults(func=cmd_shutdown)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (GenerationLockError, VoiceRegistryError, ValueError, OSError) as exc:
        _print({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Provider-free regressions for selected masters and the shared-worker adapter."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from greia_voice import build_engine, build_parser, cmd_doctor
from greia_voice_core.composition import build_providers, selected_character_provider
from greia_voice_core.engine import VoiceEngine
from greia_voice_core.locking import NullGenerationLock
from greia_voice_core.models import GenerationDisposition, ProviderStatus, SpeechKind, VoiceRequest
from greia_voice_core.providers import ChatterboxMLXProvider, VoiceProviderError
from greia_voice_core.registry import VoiceRegistry
from greia_voice_core.service import send_request
from greia_voice_core.voxstage_client import VoxStageClient, VoxStageServiceError
from greia_voice_core.voxstage_provider import VoxStageProvider


def sample_wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        audio.writeframes(b"\x01\x08\xff\xf7" * 24000)
    return stream.getvalue()


class StubVoxStage:
    """Exercise the provider contract without importing or starting an ML model."""

    base_url = "http://127.0.0.1:8791"

    def __init__(self, profile, missing=False):
        self.profile = profile
        self.missing = missing
        self.calls = []
        self.saved = {"reference_sha256": profile.anchor_sha256, "transcript": profile.anchor_transcript}
        self.audio = sample_wav()
        self.job = {
            "status": "completed",
            "backend": {"model": "mlx-community/VoxCPM2-8bit", "revision": "test"},
            "results": [{"spec": {"voice": profile.voxstage_voice_id, "reference_sha256": profile.anchor_sha256, "mode": "reference", "seed": 123}, "file": "speech-001-take-01.wav", "sha256": "chunk-hash"}],
            "mixes": [{"file": "mix-take-01.wav", "sha256": hashlib.sha256(self.audio).hexdigest()}],
        }

    def json(self, route, payload=None, key=None):
        self.calls.append((route, payload, key))
        if route == "/health":
            return {"status": "ok", "backend": self.job["backend"]}
        if route == "/v1/capabilities":
            return {"modes": ["reference"]}
        if route == "/v1/voices/import":
            self.missing = False
            return self.saved
        if route.startswith("/v1/voices/"):
            if self.missing:
                raise VoxStageServiceError("Unknown voice: test", 400)
            return self.saved
        if route == "/v1/jobs":
            self.submitted = payload
            self.job["results"][0]["spec"]["text"] = payload["segments"][0]["text"]
            return {"id": "test-job-01"}
        raise AssertionError(route)

    def wait_job(self, job_id):
        return self.job

    def download(self, job_id, filename, destination):
        destination.write_bytes(self.audio)


class SelectedMasterTests(unittest.TestCase):
    def test_active_registry_promotes_exact_six_owner_selections(self):
        registry = VoiceRegistry.load(ROOT)
        selected = {
            "lilli": ("greia.lilli.v2", "greia-audition-20261019-lilli-v2-03", "lilli-source-v2.wav"),
            "leo": ("greia.leo.v2", "greia-audition-20261019-leo-v1-03", "leo-source-v2.wav"),
            "flash": ("greia.flash.v2", "greia-audition-20261019-flash-v1-02", "flash-source-v2.wav"),
            "dani": ("greia.dani.v3", "greia-audition-20261021-dani-v5-02", "dani-source-v3.wav"),
            "tito": ("greia.tito.v3", "greia-audition-20261021-tito-v3-01", "tito-source-v3.wav"),
            "momo": ("greia.momo.v3", "greia-audition-20261021-momo-v3-01", "momo-source-v3.wav"),
        }
        self.assertEqual(registry.registry_version, "v0.3")
        self.assertEqual(set(registry.profiles), set(selected))
        for character, (voice_id, audition, source_name) in selected.items():
            profile = registry.get(character)
            registry.verify_anchor(profile)
            self.assertEqual(profile.voice_id, voice_id)
            self.assertEqual(profile.voxstage_voice_id, audition)
            self.assertTrue(profile.anchor_transcript)
            source = ROOT / f"assets/source/audio/character-voice-masters/v0.3/{source_name}"
            self.assertEqual(source.read_bytes(), profile.anchor_path.read_bytes())

    def test_default_and_explicit_legacy_composition_use_one_character_renderer(self):
        with patch.dict("os.environ", {}, clear=True):
            engine = build_engine()
            self.assertIsInstance(engine.providers[0], VoxStageProvider)
            registry = engine.registry
            for character in registry.profiles:
                for locale in ("en", "it", "fr", "es"):
                    kind = SpeechKind.DANI_SYSTEM_SPEECH if character == "dani" else SpeechKind.CHARACTER_DIALOGUE
                    provider, _ = engine.route(VoiceRequest(character, kind, locale, "Hello there"))
                    self.assertIsInstance(provider, VoxStageProvider)
            provider, _ = engine.route(VoiceRequest("dani", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao mondo"))
            self.assertIsInstance(provider, VoxStageProvider)
            legacy = build_engine(character_provider="chatterbox")
            for character in registry.profiles:
                kind = SpeechKind.DANI_SYSTEM_SPEECH if character == "dani" else SpeechKind.SHARED_CHARACTER_UTTERANCE
                provider, _ = legacy.route(VoiceRequest(character, kind, "it", "Ciao mondo"))
                self.assertIsInstance(provider, ChatterboxMLXProvider)
            provider, profile = engine.route(VoiceRequest("pedagogical", SpeechKind.PEDAGOGICAL_SPEECH, "it", "ma"))
            self.assertNotIsInstance(provider, VoxStageProvider)
            self.assertIsNone(profile)

    def test_configuration_is_explicit_and_never_silently_falls_back(self):
        with patch.dict("os.environ", {"GREIA_VOICE_CHARACTER_PROVIDER": "chatterbox"}):
            self.assertIsInstance(build_providers()[0], ChatterboxMLXProvider)
            self.assertIsInstance(build_providers("voxstage")[0], VoxStageProvider)
        with self.assertRaises(ValueError):
            selected_character_provider("unknown")
        provider = VoxStageProvider(StubVoxStage(VoiceRegistry.load(ROOT).get("leo")))
        with patch.object(provider.client, "json", side_effect=VoxStageServiceError("offline")):
            engine = VoiceEngine(ROOT, VoiceRegistry.load(ROOT), [provider, ChatterboxMLXProvider()])
            result = engine.generate(VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao mondo"))
        self.assertEqual(result.disposition, GenerationDisposition.UNAVAILABLE)
        self.assertEqual(result.provider_id, "voxstage-voxcpm2")

    def test_operator_flag_exists_on_all_engine_entry_points(self):
        for command in ("doctor", "generate", "batch", "serve"):
            subparser = build_parser()._subparsers._group_actions[0].choices[command]
            self.assertIn("--character-provider", subparser._option_string_actions)

    def test_doctor_exit_code_tracks_selected_character_readiness(self):
        provider = VoxStageProvider(StubVoxStage(VoiceRegistry.load(ROOT).get("leo")))
        for available in (True, False):
            with patch("greia_voice.build_providers", return_value=(provider,)), patch.object(
                provider, "probe", return_value=MagicMock(to_dict=lambda: {"available": available})
            ), patch("greia_voice.ChatterboxMLXProvider"), patch(
                "greia_voice.WhisperVerifier.probe", return_value=(False, "optional unavailable")
            ), patch("greia_voice.AudioPipeline.ffmpeg_available", return_value=True), patch("greia_voice._print") as emit:
                result = cmd_doctor(build_parser().parse_args(["doctor"]))
            self.assertEqual(result, 0 if available else 2)
            self.assertEqual(emit.call_args.args[0]["character_production_ready"], available)


class VoxStageProviderTests(unittest.TestCase):
    def setUp(self):
        self.profile = VoiceRegistry.load(ROOT).get("leo")
        self.client = StubVoxStage(self.profile)
        self.provider = VoxStageProvider(self.client)
        self.request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "fr-CA", "Bonjour, mon ami.")

    def test_missing_voice_is_imported_once_and_saved_reference_reused(self):
        self.client.missing = True
        for _ in range(2):
            take = self.provider.generate(self.request, self.profile)
            try:
                self.assertEqual(take.temporary_wav.read_bytes(), self.client.audio)
                self.assertEqual(take.generation_parameters["language_direction"], "French")
                self.assertEqual(take.generation_parameters["recordings"][0]["seed"], 123)
            finally:
                take.temporary_wav.unlink()
        imports = [c for c in self.client.calls if c[0] == "/v1/voices/import"]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0][1]["transcript"], self.profile.anchor_transcript)
        self.assertEqual(self.client.submitted["voice"], self.profile.voxstage_voice_id)
        self.assertEqual(self.client.submitted["takes"], 1)
        self.assertEqual(self.client.submitted["segments"][0]["text"], self.request.text)
        self.assertIn("Speak in French.", self.client.submitted["segments"][0]["delivery"])
        self.assertTrue(take.generation_parameters["delivery_prompt"])

    def test_explicit_performance_reaches_worker_and_receipt_parameters(self):
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao!", delivery_prompt="Quiet, curious and reassuring.")
        take = self.provider.generate(request, self.profile)
        try:
            self.assertEqual(self.client.submitted["segments"][0]["delivery"], "Speak in Italian. Quiet, curious and reassuring.")
            self.assertEqual(take.generation_parameters["delivery_prompt"], request.delivery_prompt)
        finally:
            take.temporary_wav.unlink()

    def test_delivery_direction_fits_voxstage_limit_without_truncating_prompt(self):
        prefix = "Speak in Spanish. "
        delivery_prompt = "Dani, a cheerful, earnest little robot with neat, lightly staccato phrasing. Names one picture word for a young learner: natural, careful pronunciation of every sound, friendly and calm, no extra drama. Let the ending of the word ring out clearly so the rhyme is easy to hear."
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "es", "¡Fantástico, riman!", delivery_prompt=delivery_prompt)
        take = self.provider.generate(request, self.profile)
        try:
            delivery = self.client.submitted["segments"][0]["delivery"]
            self.assertEqual(delivery, prefix + delivery_prompt)
            self.assertLessEqual(len(delivery), 300)
        finally:
            take.temporary_wav.unlink()

    def test_overlong_delivery_is_rejected_before_job_submission(self):
        request = VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "es", "Hola!", delivery_prompt="x" * 283)
        with self.assertRaisesRegex(VoiceProviderError, "300-character segment limit"):
            self.provider.generate(request, self.profile)
        self.assertFalse(any(path == "/v1/jobs" for path, _ in self.client.calls))

    def test_chatterbox_rejects_explicit_unsupported_acting_direction(self):
        with build_engine(character_provider="chatterbox") as engine:
            result = engine.generate(VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "it", "Ciao!", delivery_prompt="Playful."))
        self.assertEqual(result.disposition, GenerationDisposition.REJECTED)
        self.assertIn("does not support delivery_prompt", result.detail)

    def test_conflicting_voice_is_not_replaced_or_submitted(self):
        self.client.saved["reference_sha256"] = "wrong-reference"
        with self.assertRaisesRegex(VoiceProviderError, "does not match"):
            self.provider.generate(self.request, self.profile)
        self.assertFalse(any(c[0] in {"/v1/voices/import", "/v1/jobs"} for c in self.client.calls))

    def test_bad_result_identity_or_transfer_cannot_be_reported_successful(self):
        self.client.job["results"][0]["spec"]["reference_sha256"] = "wrong-reference"
        with self.assertRaisesRegex(VoiceProviderError, "no matching"):
            self.provider.generate(self.request, self.profile)
        self.client.job["results"][0]["spec"]["reference_sha256"] = self.profile.anchor_sha256
        self.client.job["mixes"][0]["sha256"] = "bad-transfer"
        with self.assertRaisesRegex(VoiceProviderError, "Incomplete audio transfer"):
            self.provider.generate(self.request, self.profile)

    def test_provider_close_never_unloads_shared_worker(self):
        self.provider.close()
        self.assertEqual(self.client.calls, [])

    def test_missing_sentence_cannot_pass_as_complete_speech(self):
        with patch.object(self.client, "wait_job", side_effect=lambda _: {
            **self.client.job,
            "results": [{**self.client.job["results"][0], "spec": {**self.client.job["results"][0]["spec"], "text": "Bonjour."}}],
        }):
            with self.assertRaisesRegex(VoiceProviderError, "complete requested text"):
                self.provider.generate(self.request, self.profile)

    def test_complete_mix_includes_every_split_chunk(self):
        def chunked(_):
            first = self.client.job["results"][0]
            second = {**first, "file": "speech-002-take-01.wav", "spec": {**first["spec"], "text": "mon ami."}}
            first = {**first, "spec": {**first["spec"], "text": "Bonjour, "}}
            return {**self.client.job, "results": [first, second]}
        with patch.object(self.client, "wait_job", side_effect=chunked):
            take = self.provider.generate(self.request, self.profile)
            try:
                self.assertEqual(len(take.generation_parameters["recordings"]), 2)
                self.assertEqual(take.temporary_wav.read_bytes(), self.client.audio)
            finally:
                take.temporary_wav.unlink()

    def test_unavailable_or_malformed_service_is_not_readiness(self):
        self.client.job["backend"] = []
        self.assertFalse(self.provider.probe().available)


class VoxStageClientTests(unittest.TestCase):
    def test_no_cloud_origin_redirect_credentials_or_proxy(self):
        for url in ("https://example.com", "http://example.com", "http://user:pass@localhost:8791", "http://localhost:8791/v1", "http://localhost:8791?token=secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                VoxStageClient(url)
        client = VoxStageClient("http://localhost:8791")
        self.assertEqual(client.base_url, "http://localhost:8791")

    def test_http_timeout_is_configurable_and_posts_are_never_retried(self):
        client=VoxStageClient(http_timeout=180)
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'{}'
        with patch.object(client.opener,'open',return_value=response) as opened:
            self.assertEqual(client.json('/health'),{})
            self.assertEqual(opened.call_args.kwargs['timeout'],180)
        with patch.object(client.opener,'open',side_effect=TimeoutError('busy')) as opened:
            with self.assertRaisesRegex(VoxStageServiceError,'do not resubmit'):
                client.json('/v1/jobs',{'test':True},key='exact-key')
            self.assertEqual(opened.call_count,1)
        for value in (0,7201,float('nan')):
            with self.assertRaises(ValueError):VoxStageClient(http_timeout=value)

    def test_failed_job_and_timeout_report_same_job_for_recovery(self):
        client = VoxStageClient(job_timeout=1, poll_interval=0.01)
        with patch.object(client, "json", return_value={"status": "failed", "error": "cap reached"}):
            with self.assertRaisesRegex(VoxStageServiceError, "test-job.*failed"):
                client.wait_job("test-job")
        with patch.object(client, "json", return_value={"status": "running"}), patch("greia_voice_core.voxstage_client.time.monotonic", side_effect=[0, 2]):
            with self.assertRaisesRegex(VoxStageServiceError, "may still be running"):
                client.wait_job("test-job")

    def test_warm_client_separates_connection_and_generation_deadlines(self):
        conn = MagicMock()
        conn.recv.return_value = b'{"ok":true}\n'
        with patch("greia_voice_core.service.socket.create_connection", return_value=conn) as connect:
            self.assertTrue(send_request("127.0.0.1", 43841, {"speaker": "leo"})["ok"])
        connect.assert_called_once_with(("127.0.0.1", 43841), timeout=10.0)
        conn.settimeout.assert_called_once_with(3600)


class RetainedChatterboxTests(unittest.TestCase):
    def test_upstream_diagnostics_do_not_corrupt_cli_json_stdout(self):
        mx = types.SimpleNamespace(eval=lambda _: None, clear_cache=lambda: None)
        mlx = types.ModuleType("mlx")
        mlx.core = mx
        def generate(**kwargs):
            print("upstream generation diagnostic")
            yield types.SimpleNamespace(audio=[0.1], sample_rate=48000)
        def load():
            print("upstream model diagnostic")
            return types.SimpleNamespace(generate=generate)
        sf = types.SimpleNamespace(write=lambda path, *args, **kwargs: Path(path).write_bytes(sample_wav()))
        provider = ChatterboxMLXProvider()
        output, errors = io.StringIO(), io.StringIO()
        from contextlib import redirect_stderr, redirect_stdout
        with patch.dict(sys.modules, {"mlx": mlx, "mlx.core": mx, "numpy": types.SimpleNamespace(asarray=lambda a: a), "soundfile": sf}), patch.object(
            provider, "probe", return_value=ProviderStatus(provider.provider_id, True, "stub")
        ), patch.object(provider, "_load_model", side_effect=load), patch.object(
            provider, "_trim_audio", return_value=[0.1]
        ), redirect_stdout(output), redirect_stderr(errors):
            take = provider.generate(VoiceRequest("leo", SpeechKind.CHARACTER_DIALOGUE, "en", "Hello there"), VoiceRegistry.load(ROOT).get("leo"))
        take.temporary_wav.unlink()
        self.assertEqual(output.getvalue(), "")
        self.assertIn("upstream model diagnostic", errors.getvalue())
        self.assertIn("upstream generation diagnostic", errors.getvalue())


if __name__ == "__main__":
    unittest.main()

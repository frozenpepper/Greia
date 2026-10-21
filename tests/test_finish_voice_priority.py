"""Bounded continuation invariants; no provider requests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import finish_voice_priority as finish
from greia_voice_corpus.store import write_json
from greia_voice_corpus.inventory import digest, receipt_path


class PriorityContinuationTests(unittest.TestCase):
    def test_history_counts_are_max_not_sum_and_duplicate_audio_is_one_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            relative = 'activities/example/audio/en/short.wav'
            for folder, count in (('first', 1), ('continuation', 2)):
                write_json(root / folder / 'carrier-attempt-counts.json', {relative: count, 'out-of-scope': 99})
                raw = root / folder / 'carrier-raw' / (relative + '.raw.wav')
                raw.parent.mkdir(parents=True)
                raw.write_bytes(b'same preserved take')
                write_json(receipt_path(raw), {'output': {'sha256': digest(raw)}})
            counts, done, sources = finish.collect_history(root, {relative})
            self.assertEqual(counts, {relative: 2})
            self.assertEqual(len(sources[relative]), 1)
            self.assertEqual(done, {})

    def test_fresh_row_preserves_words_and_uses_frozen_base_policy(self):
        row = {'path': 'example.wav', 'request': {'speaker': 'momo', 'locale': 'it',
               'kind': 'character_dialogue', 'text': 'Trovò Luna.', 'delivery_prompt': 'Calm.'}}
        frozen = finish.fresh_row(row)
        self.assertEqual(frozen['request']['text'], 'Trovò Luna.')
        self.assertTrue(frozen['request']['ignore_accents'])
        self.assertEqual(frozen['spoken_carrier']['composite_text'], 'Ascolta questa frase in italiano...\n\nTrovò Luna.')
        self.assertIn('pause silently for two seconds', frozen['spoken_carrier']['composite_delivery_prompt'])
        self.assertEqual(frozen['spoken_carrier']['asr_revision'], finish.DEFAULT_ASR_REVISION)
        self.assertNotIn('spoken_carrier', row)

    def test_original_restoration_is_reconciled_but_unknown_edits_are_blocked(self):
        from contextlib import nullcontext
        for restored in (True, False):
            with self.subTest(restored=restored), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                root, history, work = base / 'repo', base / 'history', base / 'work'
                root.mkdir()
                relative = 'activities/example/audio/en/short.wav'
                target = root / relative
                target.parent.mkdir(parents=True)
                target.write_bytes(b'original')
                receipt_path(target).write_text('{}')
                row = {'path': relative, 'request': {'speaker': 'momo', 'locale': 'en',
                       'kind': 'character_dialogue', 'text': 'Find Luna', 'delivery_prompt': 'Calm.'},
                       'original_sha256': digest(target), 'original_receipt_sha256': digest(receipt_path(target))}
                if not restored:
                    target.write_bytes(b'custom intervening edit')
                write_json(history / 'run' / 'plan.json', {'root': str(root), 'rows': [row]})
                priority = base / 'priority.json'
                write_json(priority, {'records': [{'path': relative}]})
                args = SimpleNamespace(work_dir=work, history_root=history, priority_file=priority, fresh=True)
                registry = SimpleNamespace(profiles={})
                with patch.object(finish, 'ROOT', root), patch.object(finish, 'collect_history', return_value=({relative: 3}, {relative: {'old-installed'}}, {})), patch.object(finish.VoiceRegistry, 'load', return_value=registry), patch.object(finish, 'build_engine', return_value=nullcontext(object())), patch.object(finish, 'InterprocessGenerationLock', return_value=nullcontext()):
                    self.assertEqual(finish.run(args), 2)
                progress = json.loads((work / 'progress.json').read_text())
                self.assertEqual(bool(progress['blocked']), not restored)
                self.assertEqual(progress.get('reconciled_original_restorations', []), [relative] if restored else [])

    def test_current_audio_quality_uses_delivered_audio_and_accent_tolerance(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            audio = work / 'source.wav'
            audio.write_bytes(b'audio')
            engine = SimpleNamespace(audio=SimpleNamespace(decode_for_review=lambda a, b: None))
            row = {'path': 'example.wav', 'request': {'text': 'Trovò Luna.', 'locale': 'it'}}
            with patch.object(finish, 'signal_metrics', return_value=({'duration_seconds': 1}, [])):
                result = finish.final_quality(engine, audio, row, lambda p, l: {'text': 'Trovo Luna'}, work)
            self.assertTrue(result['pass'])
            self.assertEqual(result['score'], 1)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Export finished Greia automated review evidence to generic Takeboard JSON.

This adapter does not change audio, generation receipts or human acceptance.
"""
import argparse
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


class GreiaReviewExporter:
    """Translate existing review reports and canonical master paths to schema v1."""

    def __init__(self, report: Path, root: Path = ROOT):
        self.report, self.root = report.resolve(), root.resolve()

    def build(self) -> dict:
        summary = json.loads((self.report / 'summary.json').read_text())
        if not summary.get('complete') or not summary.get('full_corpus_coverage'):
            raise ValueError('export requires finished full-corpus traversal')
        master_dir = self.root / 'assets/audio/characters/canonical/v0.2'
        registry = tomllib.loads((master_dir / 'manifest.toml').read_text())
        masters = {voice['character']: voice for voice in registry['voice']}
        rows = []
        seen = set()
        for line in (self.report / 'review.jsonl').read_text().splitlines():
            item = json.loads(line)
            relative, request = item['path'], item['request']
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root) or relative in seen:
                raise ValueError(f'unsafe or duplicate recording path: {relative}')
            seen.add(relative)
            master = masters.get(request['speaker'])
            row = {'id': relative, 'title': f'{request["speaker"].title()} · {request["locale"].upper()} · {path.stem}',
                   'audio': {'path': relative}, 'text': request['text'], 'speaker': request['speaker'], 'language': request['locale'],
                   'generation': {'request': request, 'source_review_fingerprint': item.get('fingerprint')},
                   'automated': {key: item[key] for key in ('status', 'flags', 'asr', 'metrics', 'error', 'reviewed_at_utc') if key in item},
                   'review': {'state': 'unreviewed', 'score': None, 'notes': '', 'reviewer': ''}}
            if master:
                row['reference'] = {'path': str((master_dir / master['production_anchor']).relative_to(self.root)),
                                    'text': master['anchor_transcript'], 'voice_id': master['voice_id'], 'sha256': master['anchor_sha256']}
            receipt_path = path.with_suffix(path.suffix + '.receipt.json')
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                row['audio'].update({key: receipt.get('output', {}).get(key) for key in ('sha256', 'bytes')})
                row['generation'].update({key: receipt[key] for key in ('voice_id', 'provider_id', 'generation_parameters') if key in receipt})
            rows.append(row)
        if len(rows) != summary['total_done'] or len(rows) != summary['selected']:
            raise ValueError('report rows do not match finished summary')
        return {'schema_version': 1, 'batch_id': 'greia-' + self.report.name,
                'title': 'Greia · four-language corpus listening review', 'media_root': str(self.root),
                'source': {'project': 'Greia', 'report': str(self.report), 'summary': summary}, 'recordings': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        output = args.output.expanduser().resolve()
        if output.is_relative_to(ROOT):
            raise ValueError('keep listening batches outside the source checkout')
        if output.exists():
            raise ValueError('output already exists; choose a new file to preserve listening decisions')
        doc = GreiaReviewExporter(args.report_dir).build()
        output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting another operator\'s review.
        with output.open('x', encoding='utf-8') as handle:
            json.dump(doc, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write('\n')
        print(f'Exported {len(doc["recordings"])} unreviewed recordings: {output}')
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

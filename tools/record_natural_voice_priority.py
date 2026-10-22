#!/usr/bin/env python3
"""Prepare/run the owner-authorized natural-method priority replacement."""
import argparse
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src'),str(ROOT)]
from greia_voice_corpus.natural_plan import prepare_natural
from greia_voice_corpus.natural_run import run_natural


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--work-dir',type=Path,required=True)
    for name in ('priority-file','remaining-file','prior-run','history-root','cache-root'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();a.work_dir=a.work_dir.resolve()
    if a.work_dir.is_relative_to(ROOT):p.error('use an external work folder')
    if a.mode=='run':return run_natural(a.work_dir)
    if any(getattr(a,k) is None for k in ('priority_file','remaining_file','prior_run','history_root','cache_root')):p.error('prepare requires scope/prior/history/cache inputs')
    plan=prepare_natural(a,ROOT);print(json.dumps({'prepared':len(plan['rows']),'canary':plan['natural_run']['canary_count']}));return 0


if __name__=='__main__':raise SystemExit(main())

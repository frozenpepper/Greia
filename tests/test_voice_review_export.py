"""The Greia adapter exports evidence without turning machine scores into approval."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review_export',ROOT/'tools/export_voice_review_batch.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.report=Path(self.temp.name)
        self.row={'path':'activities/officina_dei_suoni/assets/audio/en/bear.wav','request':{'speaker':'leo','locale':'en','text':'Bear','cue_id':'bear'},'status':'FAIL','flags':['REVIEW_ERROR'],'error':'silent','asr':{'status':'NOT_RUN_ERROR'}}
        (self.report/'review.jsonl').write_text(json.dumps(self.row)+'\n')
        self.summary={'complete':True,'full_corpus_coverage':True,'total_done':1,'selected':1}
        self.write_summary()
    def tearDown(self):self.temp.cleanup()
    def write_summary(self):(self.report/'summary.json').write_text(json.dumps(self.summary))
    def test_export_keeps_machine_failure_and_master_separate_from_human(self):
        result=module.GreiaReviewExporter(self.report).build();row=result['recordings'][0]
        self.assertEqual(row['automated']['status'],'FAIL');self.assertEqual(row['review']['state'],'unreviewed')
        self.assertEqual(row['reference']['voice_id'],'greia.leo.v2');self.assertEqual(row['text'],'Bear')
        self.assertEqual(row['audio']['path'],self.row['path'])
        self.assertTrue(Path(result['media_root']).is_absolute())
    def test_partial_and_count_mismatch_refused(self):
        for key,value in [('complete',False),('selected',2)]:
            original=self.summary[key];self.summary[key]=value;self.write_summary()
            with self.assertRaises(ValueError):module.GreiaReviewExporter(self.report).build()
            self.summary[key]=original
    def test_exclusive_output_preserves_existing_file(self):
        output=self.report/'existing.json';output.write_text('preserve')
        self.assertEqual(module.main(['--report-dir',str(self.report),'--output',str(output)]),2)
        self.assertEqual(output.read_text(),'preserve')

if __name__=='__main__':unittest.main()

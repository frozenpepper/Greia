"""Experimental preparation uses existing packaging and preserves native source."""
import hashlib,sys,tempfile,unittest,wave,struct,math
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from greia_voice_core.carrier_source import CarrierSourcePreparation,SOURCE_POLICY
from greia_voice_core.audio import AudioPipeline,AudioPipelineError

class CarrierSourceTests(unittest.TestCase):
 def test_native_and_canonical_sources_remain_separate_and_hashed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);native=root/'native.wav';dest=root/'canonical.wav';rate=48000
   with wave.open(str(native),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(struct.pack('<'+str(rate)+'h',*(int(2000*math.sin(i*.1)) for i in range(rate))))
   before=native.read_bytes();e=CarrierSourcePreparation().prepare(native,dest)
   self.assertEqual(native.read_bytes(),before);self.assertEqual(e['policy'],SOURCE_POLICY);self.assertEqual(e['native_sha256'],hashlib.sha256(before).hexdigest());self.assertEqual(e['prepared_sample_rate'],22050)
   with wave.open(str(dest)) as w:self.assertEqual(w.getframerate(),22050);self.assertEqual(w.getsampwidth(),2)
   with self.assertRaises(ValueError):CarrierSourcePreparation().prepare(native,native)
   link=root/'alias.wav';link.hardlink_to(native)
   with self.assertRaises(ValueError):CarrierSourcePreparation().prepare(native,link)
 def test_wrong_rate_and_io_failure_are_not_acoustic_success(self):
  with self.assertRaises(ValueError):CarrierSourcePreparation(AudioPipeline(48000))
  with patch.object(AudioPipeline,'validate_review_wav',side_effect=AudioPipelineError('broken')):
   with self.assertRaises(AudioPipelineError):CarrierSourcePreparation().prepare(Path('native.wav'),Path('canonical.wav'))

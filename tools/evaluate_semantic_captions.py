"""Run in an isolated semantic-eval environment. No API keys or creator accounts."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.semantic_caption_matching import MODEL_NAME, cosine, local_encoder, semantic_text_observations

parser=argparse.ArgumentParser()
parser.add_argument('--cache-dir', default='/tmp/stratify-semantic-model')
parser.add_argument('--output', required=True)
parser.add_argument('--captions-json', help='Optional public-caption result JSON; processed locally, texts omitted from output.')
args=parser.parse_args()
fixture=Path(__file__).resolve().parents[1]/'tests/fixtures/semantic-caption-benchmark.json'
data=json.loads(fixture.read_text())
encode,count=local_encoder(args.cache_dir)
results=[]
for case in data['cases']:
    vectors=list(encode([case['anchor'],case['positive'],case['negative']]))
    positive,negative=cosine(list(vectors[0]),list(vectors[1])),cosine(list(vectors[0]),list(vectors[2]))
    results.append({'id':case['id'],'positive_score':positive,'negative_score':negative,'positive_ranks_first':positive>negative})
report={'model':MODEL_NAME,'benchmark_provenance':data['provenance'],'benchmark_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'cases':results,'ranking_passes':sum(r['positive_ranks_first'] for r in results),'case_count':len(results),'rollout_decision':'not_promoted','limitations':['Illustrative fixtures are not independent real-video validation.','Semantic similarity cannot verify format or shared footage. No grouping threshold has been calibrated.']}
if args.captions_json:
    raw=json.loads(Path(args.captions_json).read_text())
    report['live_text_observations']=semantic_text_observations([r for r in raw['results'] if r['status']=='available'],encode,count)
# Record model file hashes so a later run can identify changed assets.
report['model_assets']={str(p.relative_to(args.cache_dir)):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(args.cache_dir).rglob('*') if p.is_file() and p.suffix in {'.onnx','.json'}}
Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ranking_passes':report['ranking_passes'],'case_count':len(results),'failed_cases':[r['id'] for r in results if not r['positive_ranks_first']],'output':args.output}))

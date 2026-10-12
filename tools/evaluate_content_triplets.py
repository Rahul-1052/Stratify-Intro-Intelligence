"""Offline reviewed ranking; raw text stays local and is omitted from reports."""
import argparse
import importlib.metadata
import hashlib
import json
import re
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.content_ranking_evaluation import evaluate_reviewed_triplets
from core.semantic_caption_matching import MODEL_NAME, local_encoder, semantic_text_observations
from core.caption_comparison_checks import compare_caption_evidence

STOP = set('a an the this that these those and or but for of to in on at by with is are was were be been it its we you i they he she our your my their from as not can do does did have has had will would all so just'.split())


def vocabulary_observations(records):
    vectors = {r['video_id']: {t for t in re.findall(r'\w+', r['text'].lower()) if len(t)>2 and t not in STOP} for r in records if r.get('language_code') == 'en' and isinstance(r.get('text'),str) and r['text']}
    terms = set().union(*vectors.values()) if vectors else set()
    weights = {t: math.log((len(vectors)+1)/(sum(t in v for v in vectors.values())+1))+1 for t in terms}
    pairs = []
    for i, left in enumerate(vectors):
        for right in list(vectors)[i+1:]:
            a, b = vectors[left], vectors[right]
            denominator = math.sqrt(sum(weights[t]**2 for t in a)*sum(weights[t]**2 for t in b))
            if denominator:
                pairs.append({'left': left, 'right': right, 'cosine_similarity': sum(weights[t]**2 for t in a & b)/denominator})
    return {'model': 'weighted_unique_vocabulary_diagnostic', 'coverage': [{'video_id': r['video_id'], 'status': 'encoded' if r['video_id'] in vectors and vectors[r['video_id']] else 'missing_or_unsupported'} for r in records], 'pairs': pairs}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cases', required=True)
    p.add_argument('--captions-json', action='append', required=True)
    p.add_argument('--model', choices=[MODEL_NAME,'BAAI/bge-small-en-v1.5'], default=MODEL_NAME)
    p.add_argument('--cache-dir', required=True)
    p.add_argument('--output', required=True)
    args=p.parse_args()
    case_bytes=Path(args.cases).read_bytes()
    cases=json.loads(case_bytes)['cases']
    sources=[json.loads(Path(path).read_text()) for path in args.captions_json]
    records=[r for source in sources for r in source['results'] if r['status']=='available']
    if len({r['video_id'] for r in records}) != len(records):
        raise ValueError('Do not mix duplicate or different snapshots for the same video.')
    if records:
        encode,count=local_encoder(args.cache_dir,model_name=args.model)
        semantic=semantic_text_observations(records,encode,count,model_name=args.model)
    else:
        semantic={'coverage':[], 'pairs':[]}
    lexical=vocabulary_observations(records)
    checks=[compare_caption_evidence(a,b) for i,a in enumerate(records) for b in records[i+1:]]
    report={'implementation_sha256':{str(f.relative_to(Path(__file__).resolve().parents[1])):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__).resolve(),Path(__file__).resolve().parents[1]/'core/content_ranking_evaluation.py',Path(__file__).resolve().parents[1]/'core/semantic_caption_matching.py',Path(__file__).resolve().parents[1]/'core/caption_comparison_checks.py']},'case_sha256':hashlib.sha256(case_bytes).hexdigest(),'semantic_model':args.model,
            'runtime':{'python':sys.version.split()[0],'packages':{name:importlib.metadata.version(name) for name in ['fastembed','numpy','onnxruntime','tokenizers','huggingface-hub']} if records else {}},
            'input_sources':[{'provider':source.get('provider'),'fetched_at':source.get('fetched_at')} for source in sources],
            'retrieval_coverage':[{'video_id':r['video_id'],'status':r['status'],'language_code':r.get('language_code')} for source in sources for r in source['results']],
            'caption_evidence':[{'video_id':r['video_id'],'source':r['source'],'source_url':r['source_url'],'repository_commit':r.get('repository_commit'),'language_code':r['language_code'],'is_generated':r.get('is_generated'),'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest()} for r in records],
            'semantic':evaluate_reviewed_triplets(cases,semantic),'lexical':evaluate_reviewed_triplets(cases,lexical),
            'independent_checks':checks,'semantic_coverage':semantic['coverage'],
            'model_assets':{str(f.relative_to(args.cache_dir)):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path(args.cache_dir).rglob('*') if f.is_file() and f.suffix in {'.onnx','.json'}},
            'rollout_decision':'not_promoted'}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'model':args.model,'semantic':report['semantic']['summary_by_review_source'],'lexical':report['lexical']['summary_by_review_source'],'output':args.output}))


if __name__=='__main__': main()

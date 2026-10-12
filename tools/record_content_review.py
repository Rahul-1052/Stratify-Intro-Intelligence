"""Record a human review in a new file; no model calls or default labels."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.content_review_intake import record_content_review


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--packet',required=True);p.add_argument('--case',required=True)
    p.add_argument('--reviewer',required=True)
    p.add_argument('--reviewer-kind',required=True,choices=['user','independent_human'])
    p.add_argument('--choice',required=True,choices=['b','c','both','neither','unsure'])
    p.add_argument('--reason',required=True)
    p.add_argument('--basis',required=True,choices=['whole_videos','partial_videos','titles_only'])
    p.add_argument('--language',required=True,choices=['understood','not_understood','not_confirmed'])
    p.add_argument('--output',required=True)
    args=p.parse_args()
    result=record_content_review(json.loads(Path(args.packet).read_text()),args.case,reviewer=args.reviewer,reviewer_kind=args.reviewer_kind,choice=args.choice,reason=args.reason,review_basis=args.basis,understands_language=None if args.language=='not_confirmed' else args.language=='understood')
    with Path(args.output).open('x') as handle:json.dump(result,handle,indent=2,ensure_ascii=False);handle.write('\n')
    print(json.dumps({'status':result['packet']['cases'][[c['id'] for c in result['packet']['cases']].index(args.case)]['status'],'strict_ranking_available':result['ranking_case'] is not None}))


if __name__=='__main__':main()

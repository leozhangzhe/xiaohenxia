"""One synthetic probe per existing source; report live failures separately from local tests."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spiderfoot.live_process import ProcessRunner
from spiderfoot.live_search import SourceAdapter, safe_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise SystemExit('Report already exists; no duplicate external queries performed.')
    # Do not consume a user's configured paid key or include it in artifacts.
    os.environ.pop('SF_HIBP_API_KEY', None)
    runner = ProcessRunner(ROOT)
    synthetic_name = 'xhx_demo_' + secrets.token_hex(6)
    results = []

    def probe(source, kind, query):
        start = time.monotonic()
        outcome = SourceAdapter(source, runner).search(kind, query, threading.Event(), timeout=90)
        rows = outcome['results']
        fields = {'source','input_type','query','result_type','title','value','original_url',
                  'confidence','status','queried_at','limitations','raw_summary'}
        return {'source':source, 'status':outcome['status'], 'count':len(rows),
                'duration_seconds':round(time.monotonic()-start, 2),
                'queried_at':outcome['queried_at'], 'message':outcome['message'],
                'limitations':outcome['limitations'],
                'result_schema_valid':all(fields <= set(row) for row in rows),
                'links_safe':all(not row['original_url'] or safe_url(row['original_url']) for row in rows)}

    jobs = [('spiderfoot','domain','example.invalid'), ('sherlock','username',synthetic_name),
            ('maigret','username',synthetic_name), ('whatsmyname','username',synthetic_name),
            ('holehe','email','freeze-demo@example.invalid'), ('hibp','email','freeze-demo@example.invalid')]
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(probe,*job):job[0] for job in jobs}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(result['source'] + ': ' + result['status'] + ' (' + str(result['count']) + ' results)', flush=True)
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'category':'live_external_sources',
            'synthetic_inputs_only':True, 'attempts_per_source':1, 'concurrency':2, 'timeout_seconds':90,
            'hibp_key_used':False, 'results':sorted(results,key=lambda r:r['source']),
            'interpretation':'failed/partial/timeout/not_configured are not successful no-match outcomes'},
            ensure_ascii=False, indent=2),encoding='utf-8')
    # The exit code measures live source availability, never rewrites failures to zero matches.
    successful = len(results)==6 and all(r['status']=='completed' and r['result_schema_valid'] and r['links_safe']
        for r in results if r['source']!='hibp')
    raise SystemExit(0 if successful else 1)


if __name__ == '__main__':
    main()

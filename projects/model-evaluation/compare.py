"""Compare explicit chat-completions configurations; offline fixtures by default."""
import argparse
import json
import os
import time
import urllib.request
from decimal import Decimal
from pathlib import Path


def cost(usage, rates):
    """Cached input is a subset of prompt_tokens, not an additional token count."""
    total = usage['prompt_tokens']
    cached = usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
    output = usage['completion_tokens']
    if any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in [total, cached, output]):
        raise ValueError('Usage must contain nonnegative integer token counts')
    if cached > total:
        raise ValueError('Cached input exceeds total input')
    prices = [Decimal(str(rates[k])) for k in ['input', 'cached_input', 'output']]
    if any(not x.is_finite() or x < 0 for x in prices):
        raise ValueError('Rates must be finite and nonnegative')
    value = ((total-cached)*prices[0] + cached*prices[1] + output*prices[2])/Decimal(1000000)
    return str(value)


def live_call(config):
    # Only explicit HTTPS origin + fixed API route; credentials never enter reports.
    from urllib.parse import urlparse
    origin = config['base_url'].rstrip('/')
    parsed = urlparse(origin)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an explicit HTTPS base URL without credentials/query/fragment')
    payload = {'model': config['model'], 'messages': [
        {'role': 'system', 'content': 'Answer only from the supplied evidence; state when evidence is insufficient.'},
        {'role': 'user', 'content': 'Synthetic evidence: Model A has a lamp. No timer information is provided. Does it support a timer?'}]}
    request = urllib.request.Request(origin+'/chat/completions', data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer '+os.environ['MODEL_EVAL_API_KEY'], 'Content-Type': 'application/json'})
    # Do not follow redirects with credentials.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    start = time.perf_counter()
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        body = json.load(response)
    usage = body['usage']
    text = body['choices'][0]['message']['content']
    if not isinstance(text, str):
        raise ValueError('Expected textual response')
    return text, usage, round((time.perf_counter()-start)*1000, 2)


def run(configs, live=False):
    results = []
    for cfg in configs:
        item = {'config': cfg['name'], 'model': cfg['model'], 'mode': 'live' if live else 'offline_fixture',
                'currency': cfg['currency'], 'price_source': cfg['price_source'], 'rates_per_million': cfg['rates']}
        try:
            if live:
                answer, usage, elapsed = live_call(cfg)
            else:
                answer, usage, elapsed = cfg['fixture_answer'], cfg['fixture_usage'], None
            item.update(status='completed', answer=answer, usage=usage, latency_ms=elapsed,
                        estimated_token_cost=cost(usage,cfg['rates']), quality_review='unreviewed')
        except Exception as exc:
            # Avoid recording URLs, headers, response bodies or credentials from errors.
            item.update(status='error', error_type=type(exc).__name__, quality_review='not_applicable',
                        estimated_token_cost=None, billing_status='unknown_if_request_reached_provider')
        results.append(item)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path(__file__).parent/'configs.example.json')
    parser.add_argument('--live', action='store_true', help='Explicit opt-in to paid external requests')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'results/offline.json')
    args = parser.parse_args()
    if args.live and args.output == Path(__file__).parent/'results/offline.json':
        parser.error('Live mode requires a separate --output path')
    if args.live and not os.environ.get('MODEL_EVAL_API_KEY'):
        parser.error('Set MODEL_EVAL_API_KEY explicitly for live mode')
    configs = json.loads(args.config.read_text())
    if not configs:
        parser.error('At least one configuration is required')
    if args.live and any(c['model'].startswith('example-') or c['price_source']=='synthetic' for c in configs):
        parser.error('Replace placeholder models and synthetic rates before live mode')
    results = run(configs,args.live)
    report = {'scope': 'live measurement' if args.live else 'offline fixture; not actual model performance or pricing',
              'results': results, 'comparison_warning': 'One task cannot establish model quality; manual review required.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'mode':report['scope'],'configs':len(results),'errors':sum(r['status']=='error' for r in results)}))
    if any(r['status']=='error' for r in results):
        raise SystemExit(1)

if __name__ == '__main__':
    main()

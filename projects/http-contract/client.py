"""Read-only JSON client with explicit product result states; no automatic retries."""
import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def classify(status, raw):
    if status == 401: return 'unauthenticated'
    if status == 403: return 'forbidden'
    if status == 429: return 'rate_limited'
    if status >= 500: return 'upstream_error'
    if status != 200: return 'http_error'
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError):
        return 'invalid_json'
    if not isinstance(body, dict) or body.get('status') != 'ok':
        return 'business_error'
    records = body.get('records')
    if not isinstance(records, list): return 'invalid_contract'
    if any(not isinstance(r, dict) or set(r) != {'id', 'text'} or
           not all(isinstance(r[k], str) and r[k].strip() for k in ('id', 'text'))
           for r in records): return 'invalid_contract'
    return 'data_available' if records else 'empty'

def fetch(url, request_id, token=None, timeout=5, opener=None):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or
            parts.password or parts.query or parts.fragment):
        raise ValueError('Use an explicit HTTPS endpoint without credentials, query or fragment')
    if not request_id or any(c in request_id for c in '\r\n'):
        raise ValueError('Invalid request ID')
    headers = {'Accept': 'application/json', 'X-Request-ID': request_id}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = Request(url, headers=headers, method='GET')
    result = {'request_id': request_id, 'http_status': None, 'state': None}
    try:
        with (opener or build_opener(NoRedirect)).open(req, timeout=timeout) as response:
            result['http_status'] = response.status
            raw = response.read(1_048_577)
            result['state'] = ('response_too_large' if len(raw) > 1_048_576
                               else classify(response.status, raw))
    except HTTPError as error:
        result.update(http_status=error.code, state=classify(error.code, b''))
        error.close()
    except (TimeoutError, socket.timeout): result['state'] = 'timeout'
    except URLError as error:
        result['state'] = 'timeout' if isinstance(error.reason, TimeoutError) else 'network_error'
    return result

if __name__ == '__main__':
    # No built-in endpoint or credential; running explicitly performs one GET.
    print(json.dumps(fetch(os.environ['RECORDS_API_URL'], 'manual-request',
                           os.environ.get('RECORDS_API_TOKEN')), ensure_ascii=False))

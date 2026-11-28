import json
import unittest
from io import BytesIO
from urllib.error import HTTPError, URLError
from client import classify, fetch

class Response(BytesIO):
    status = 200
class Transport:
    def __init__(self, value): self.value = value; self.calls = 0
    def open(self, req, timeout):
        self.calls += 1
        self.request = req
        if isinstance(self.value, Exception): raise self.value
        return Response(self.value)

class ContractTests(unittest.TestCase):
    def test_result_matrix(self):
        cases = [(401,b'', 'unauthenticated'), (403,b'', 'forbidden'),
                 (429,b'', 'rate_limited'), (503,b'', 'upstream_error'),
                 (302,b'', 'http_error'), (200,b'<html>', 'invalid_json'),
                 (200,b'{"status":"error"}', 'business_error'),
                 (200,b'{"status":"ok","records":[]}', 'empty'),
                 (200,b'{"status":"ok","records":[7]}', 'invalid_contract'),
                 (200,b'{"status":"ok","records":[{"id":"1","text":"demo"}]}', 'data_available')]
        for status, raw, expected in cases:
            with self.subTest(expected=expected): self.assertEqual(classify(status,raw),expected)
    def test_request_and_no_secrets_in_report(self):
        t=Transport(b'{"status":"ok","records":[]}')
        r=fetch('https://example.invalid/records','r1','synthetic-token',opener=t)
        self.assertEqual(t.request.get_method(),'GET')
        self.assertEqual(r['state'],'empty')
        self.assertNotIn('synthetic-token',json.dumps(r))
    def test_timeout_not_retried(self):
        t=Transport(TimeoutError())
        self.assertEqual(fetch('https://example.invalid/records','r',opener=t)['state'],'timeout')
        self.assertEqual(t.calls,1)
    def test_network_failure(self):
        t=Transport(URLError('synthetic network failure'))
        self.assertEqual(fetch('https://example.invalid/records','r',opener=t)['state'],'network_error')
    def test_http_error(self):
        t=Transport(HTTPError('https://example.invalid',403,'forbidden',{},BytesIO(b'')))
        self.assertEqual(fetch('https://example.invalid/records','r',opener=t)['state'],'forbidden')
    def test_endpoint_boundary(self):
        for url in ['http://example.invalid','https://a:b@example.invalid','https://example.invalid?q=secret']:
            with self.assertRaises(ValueError): fetch(url,'r')
    def test_size_limit(self):
        self.assertEqual(fetch('https://example.invalid','r',opener=Transport(b'x'*1_048_577))['state'],'response_too_large')
if __name__ == '__main__': unittest.main()

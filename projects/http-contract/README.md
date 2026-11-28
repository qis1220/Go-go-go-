# Records API Contract

A read-only JSON client that distinguishes missing authentication, forbidden access, rate limiting, upstream errors, malformed responses, empty records and available data. It provides explicit result states for an assistant or interface instead of treating every HTTP 200 as task success.

Python standard library only. Run `python3 -m unittest -v` in this directory. Tests inject synthetic responses and exceptions; they do not contact a service, verify TLS, authenticate a real user or measure production reliability. Ten response matrix cases and six additional test methods cover request construction and failure boundaries.

To make one real GET, explicitly configure `RECORDS_API_URL` (HTTPS, no URL credentials/query/fragment) and optionally `RECORDS_API_TOKEN`, then run `python3 client.py`. No real endpoint or credentials are supplied. Requests use the configured host, so only configure a trusted endpoint. Redirects are rejected and reports exclude body, URL and token. The expected response is `{"status":"ok","records":[{"id":"1","text":"example"}]}`. This is a project-specific contract, not a provider API standard.

No automatic retries, writes, model calls, persistence or user-facing answer generation. A timeout provides no proof of remote outcome. The timeout setting is for blocking network operations, not a total task deadline; the response size is capped at 1 MiB. Empty data is a valid read result, not permission to invent records. A downstream assistant must separately validate source, applicability and task outcome.

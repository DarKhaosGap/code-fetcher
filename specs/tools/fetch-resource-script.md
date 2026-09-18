# Fetch Resource Script

## Summary
Add a Python CLI script that performs an authenticated HTTP GET request against a versioned
repository-style endpoint and returns the response body as a string.

## Requirements
- URL is composed from a protocol (default `https`), a domain, a version (e.g. `27.1.0`) and a
  resource path (e.g. `/com/example/Example.java`).
- Protocol, domain and version are read from environment variables.
- Version can be overridden with an optional command line argument.
- Resource path is a mandatory positional argument.
- Requests use HTTP basic authentication with credentials from environment variables.
- The function returns the response body as a string; the CLI prints it to stdout.
- Missing required configuration or HTTP errors exit with a non-zero status and a message on stderr.

## Scope
- `fetch_resource.py` (new): CLI entry point and reusable `fetch_resource` function.
- `requirements.txt` (new): declares the `requests` dependency.

## Implementation
- Configuration is resolved in `load_config()` from environment variables:
  `RESOURCE_PROTOCOL` (default `https`), `RESOURCE_DOMAIN`, `RESOURCE_VERSION`,
  `RESOURCE_USERNAME`, `RESOURCE_PASSWORD`. A missing required value raises `ConfigError`.
- `build_url()` normalizes the domain and resource path and uses `urllib.parse.quote` on the path
  segments so user input cannot inject a different host or query string. Only `http`/`https` are
  accepted as protocols.
- `fetch_resource()` uses `requests.get` with `HTTPBasicAuth`, an explicit timeout, and
  `raise_for_status()`. The response encoding falls back to `utf-8` when the server does not
  declare one, so the returned value is a deterministic string.
- `argparse` exposes `resource_path` as positional, plus `--version`, `--protocol`, `--domain`
  and `--timeout` overrides.
- Credentials are never logged or echoed.

## Validation
- `python -m py_compile fetch_resource.py` succeeds.
- `python fetch_resource.py --help` renders the expected CLI usage.
- No network call was executed against a real endpoint.

## Status
Complete. Retries/backoff and proxy configuration are out of scope.

# Fetch Resource Script

## Summary
Add a Python CLI script that performs an authenticated HTTP GET request against a versioned
repository-style endpoint and returns the response body as a string.

## Requirements
- URL is composed from a protocol (default `https`), a domain, a version (e.g. `27.1.0`) and a
  resource path derived from a full class name (e.g. `com.example.Example` becomes
  `com/example/Example`).
- Protocol, domain and version are read from environment variables.
- Version can be overridden with an optional command line argument.
- A full dotted class name is a mandatory positional argument. A terminal `.java` suffix is
  preserved, so `com.example.Example.java` becomes `com/example/Example.java`.
- Empty class-name segments and slash-separated input are rejected.
- After fetching the requested class, the script fetches each directly imported project class once.
- Explicit ordinary and static imports are supported; wildcard imports and standard-library
  packages such as `java.*`, `javax.*`, `sun.*`, and `com.sun.*` are skipped.
- Missing dependency requests produce warnings and do not prevent other classes from being printed.
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
- `class_name_to_resource_path()` converts the dotted class name into a slash-separated resource
  path and validates the input before URL construction.
- `extract_imports()` identifies unique explicit project imports from Java source and omits wildcard
  and standard-library imports.
- `fetch_class_sources()` fetches the root class and its direct dependencies without recursive
  traversal. `format_class_sources()` prints each successful source body under a fully qualified
  class-name header.
- `argparse` exposes `class_name` as positional, plus `--version`, `--protocol`, `--domain` and
  `--timeout` overrides. The CLI converts `class_name` before calling `fetch_resource()`.
- Credentials are never logged or echoed.

## Validation
- `python -m py_compile fetch_resource.py` succeeds.
- The CLI help describes a fully qualified class name such as `com.example.Example`.
- Conversion behavior is implemented for plain class names and `.java` names; malformed and
  slash-separated inputs raise `ConfigError`.
- Isolated dependency checks confirm import filtering, static-import handling, deduplication, one
  fetch per direct dependency, and tagged output without network access.
- No network call was executed against a real endpoint.

## Status
Complete. Runtime conversion assertions were not executed because the local environment did not
have the declared `requests` dependency installed. Retries/backoff and proxy configuration are
out of scope.

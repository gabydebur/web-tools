# web-tools

Minimal HTTP tooling service exposing web primitives (`web_search`, `fetch_url`,
`extract_text`) intended to be consumed as tools by a local LLM.

The project is deliberately small, strictly typed, and structured so it can
later be exposed as an MCP server without rewriting the core logic.

## Features

- `POST /web_search` — SearxNG-backed web search
- `POST /fetch_url` — fetch a URL and return size-limited HTML + title
- `POST /extract_text` — fetch a URL and return readable plain text
- `GET /health`, `GET /ready` — liveness / readiness probes
- Strict URL validation (`http` / `https` only, SSRF hooks reserved)
- Structured JSON logs
- Configurable timeouts and size limits
- Docker-friendly

## Requirements

- Python 3.12+
- A reachable SearxNG instance exposing the JSON format

## Installation (local)

```bash
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# .venv\Scripts\activate        # Windows PowerShell / cmd

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to point `SEARXNG_BASE_URL` at your SearxNG instance.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Docker

```bash
docker build -t web-tools .
docker run --rm -p 8000:8000 --env-file .env web-tools
```

The image runs as a non-root user and exposes port 8000.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `SEARXNG_BASE_URL` | `http://searxng:8080` | Base URL of SearxNG |
| `SEARXNG_LANGUAGE` | `fr` | Preferred language |
| `SEARXNG_SAFESEARCH` | `1` | `0` off, `1` moderate, `2` strict |
| `HTTP_TIMEOUT_SECONDS` | `10` | Timeout for outgoing HTTP calls |
| `HTTP_USER_AGENT` | `web-tools/0.1 ...` | User-Agent header |
| `HTTP_MAX_REDIRECTS` | `5` | Max redirects followed |
| `MAX_HTML_BYTES` | `2000000` | Max bytes read from an upstream response |
| `MAX_HTML_CHARS` | `500000` | Max HTML chars returned by `/fetch_url` |
| `MAX_TEXT_CHARS` | `50000` | Max text chars returned by `/extract_text` |
| `SEARCH_DEFAULT_LIMIT` | `5` | Default `limit` when not provided |
| `SEARCH_MAX_LIMIT` | `20` | Hard cap on `limit` |

## Examples (curl)

### Search

```bash
curl -s http://localhost:8000/web_search \
  -H "Content-Type: application/json" \
  -d '{"query":"FastAPI tutorial","limit":3}'
```

### Fetch URL

```bash
curl -s http://localhost:8000/fetch_url \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

### Extract text

```bash
curl -s http://localhost:8000/extract_text \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

### Health / ready

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

## Error format

All errors return a consistent JSON payload:

```json
{ "error": "invalid_url", "detail": "URL scheme 'ftp' is not allowed" }
```

Known codes: `invalid_url`, `upstream_error`, `payload_too_large`,
`search_backend_error`, `validation_error`, `internal_error`.

## Limits & caveats

- Not a crawler: there is no retry, no caching, no rate limiting.
- No authentication — deploy behind a trusted network boundary.
- JavaScript-heavy pages may yield poor extraction (no headless browser).
- SearxNG must have the `json` format enabled in its `settings.yml`.
- SSRF mitigations are scaffolded (`validate_url`) but not enforced yet —
  do not expose this service to untrusted networks without adding
  host whitelist / IP filtering.

## Roadmap

- [ ] Local documentation ingestion (indexing + search)
- [ ] Open WebUI integration recipe
- [ ] MCP server adapter (stdio + HTTP) wrapping the same services
- [ ] SSRF hardening (private-range blocklist, DNS pinning)
- [ ] Optional response caching

## Project layout

```
app/
  main.py              # FastAPI app factory, lifespan, error handlers
  config.py            # Pydantic settings
  schemas.py           # Request/response models
  routes/
    health.py
    search.py          # /web_search
    fetch.py           # /fetch_url
    extract.py         # /extract_text
  services/
    http_client.py     # shared httpx client + size-guarded fetch
    searxng.py         # SearxNG JSON client
    extractor.py       # title / readable text extraction
  utils/
    logging.py         # JSON logging
    url_validation.py  # scheme + host checks
    errors.py          # domain exceptions
tests/
Dockerfile
requirements.txt
requirements-dev.txt
.env.example
```

## License

MIT — see source for details (add `LICENSE` file as needed).

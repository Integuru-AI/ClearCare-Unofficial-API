# ClearCare Unofficial API

Unofficial Python integrations for ClearCare.

## Integrations

- `clearcare_find_client_by_name.py` - `find_client_by_name` (308 live events).
- `clearcare_read_adls.py` - `read_adls` (282 live events).
- `clearcare_read_iadls.py` - `read_iadls` (272 live events).
- `clearcare_update_adls.py` - `update_adls` (267 live events).

## Usage

Each file exposes a `run(input, context)` entrypoint. The runtime is expected to provide:

- `input`: integration-specific request fields.
- `context["headers"]`: authenticated request headers when required.
- `context["base_url"]`: the platform base URL when overriding the default.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Info

This unofficial API is built by [Integuru.ai](https://integuru.ai/).

For custom requests or hosted authentication, contact richard@taiki.online.

See the [complete list of APIs by Integuru](https://github.com/Integuru-AI/APIs-by-Integuru).

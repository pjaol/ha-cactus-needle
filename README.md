# Cactus Needle for Home Assistant

Fast, private intent routing for Home Assistant Assist using
[Cactus Needle](https://github.com/cactus-compute/needle).

Cactus Needle is not a chat model. It recognizes a small set of safe smart-home
operations in tens of milliseconds and extracts the target exactly as spoken.
Home Assistant still resolves the target, enforces Assist exposure settings,
and performs the action. Everything else goes to an optional fallback
conversation agent such as Ollama, OpenAI, or another local LLM.

```text
Voice or text
     │
     ▼
Cactus Needle conversation entity
     ├── device action/state query ──► Home Assistant native agent
     └── general question ───────────► configured fallback agent
```

## Why

General-purpose LLM agents often receive a large entity catalog and spend
seconds deciding that “kill the lamps in the kitchen” means “turn off the
kitchen lights.” Needle performs only that normalization step. It never gets
credentials and it does not execute Home Assistant services directly.

## Features

- Local inference with no cloud dependency after model download
- Home Assistant `ConversationEntity` for native Assist pipeline selection
- Native HA entity, area, alias, and exposure resolution
- Safe routing surface: turn on, turn off, toggle, and state query
- Configurable fallback conversation agent
- Home Assistant App for one-click supervised deployment
- Remote service mode for a Mac, PC, NAS, or Raspberry Pi
- Server/model sensors, reset button, and downloadable diagnostics
- AMD64 and ARM64 container builds
- Telemetry disabled by default

## Installation

### Home Assistant App — recommended

Once this repository has a release:

1. Add `https://github.com/pjaol/ha-cactus-needle` as a Home Assistant App
   repository.
2. Install and start **Cactus Needle**.
3. Install the Cactus Needle integration from the Home Assistant Marketplace.
4. Accept the discovered integration and choose a fallback agent.
5. Select **Cactus Needle** as the conversation agent in an Assist pipeline.

The first start downloads the base Needle model. The App keeps its cache in
persistent `/data` storage.

### Remote Cactus service

Install the integration, then enter a server URL such as
`http://192.168.1.50:18080`. A `launchd` example for macOS is included under
[`macos/`](macos/).

### Manual integration install

Copy `custom_components/cactus_needle` to
`/config/custom_components/cactus_needle`, restart Home Assistant, and add
**Cactus Needle** under **Settings → Devices & services**.

## Components

| Path | Purpose |
|---|---|
| `custom_components/cactus_needle` | Home Assistant integration |
| `cactus_needle` | App metadata, container, and production server |
| `macos` | Optional remote macOS service definition |
| `tests` | Standalone API tests |

## HTTP API

The bundled service deliberately has a small surface:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health, model, version, and aggregate timing |
| `GET` | `/version` | Service/runtime version |
| `GET` | `/model` | Compatibility model response |
| `POST` | `/complete` | Classify one utterance against supplied tools |
| `POST` | `/reset` | Unload the in-memory agent |

There is no network model-upload or fine-tuning endpoint. Requests are bounded
to 256 KiB, 4,096 query characters, and 64 tool definitions.

## Development

```bash
python -m pytest -q
ruff check custom_components cactus_needle/server.py tests
docker build -f cactus_needle/Dockerfile -t cactus-needle-ha:test .
```

Releases tagged `vX.Y.Z` build a multi-architecture image and publish both
`X.Y.Z` and `latest` tags to GitHub Container Registry. Keep the version in
`cactus_needle/config.yaml` and the integration manifest synchronized.

## Privacy and security

- Cactus runtime telemetry is disabled by default. Users can explicitly opt in.
- This project does not log utterances, prompts, or model outputs.
- The App API is internal to the Home Assistant App network unless the user
  explicitly publishes its port.
- Device execution remains inside Home Assistant and honors Assist exposure.
- The fallback agent receives only requests Needle did not handle, or commands
  HA could not safely resolve.

## Licensing

This project is MIT licensed. `cactus-compute` is separately distributed under
Apache-2.0 by Cactus Compute; Apache-2.0 dependencies can be used by an
MIT-licensed project while retaining their own notices and license terms.
Model files remain subject to the terms published with their respective Cactus
model repositories.



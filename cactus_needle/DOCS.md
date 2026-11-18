# Cactus Needle Home Assistant App

## Installation

Install and start the App. Home Assistant should discover the service. Accept
the discovered **Cactus Needle** integration and select a fallback conversation
agent. Finally choose **Cactus Needle** as the conversation agent in an Assist
pipeline.

The first startup downloads the selected base model and may take several
minutes. Later starts use the persistent model cache.

## Configuration

- `port`: internal HTTP API port; normally leave at `18080`.
- `generation`: Cactus Needle generation, currently `3` by default.
- `weights`: optional path to a custom `.cact` model mounted in the App.
- `telemetry`: opt in to Cactus's anonymous runtime usage telemetry. Prompts
  and outputs are not included by Cactus. Disabled by default here.
- `debug_logging`: verbose service logging. Prompts and outputs are never
  logged by this service.

The API is not published to the LAN by default. Home Assistant connects over
the internal App network.


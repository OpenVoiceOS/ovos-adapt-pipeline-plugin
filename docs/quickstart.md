# Quickstart

## Install

```bash
pip install ovos-adapt-parser
```

This pulls in the OVOS pipeline plugin and the bundled adapt parser.

## Match an utterance with the engine directly

The adapt parser works standalone, no OVOS, no messagebus. This is the fastest
way to see it work and the best way to prototype intents.

```python
from ovos_adapt.intent import IntentBuilder
from ovos_adapt.engine import IntentDeterminationEngine

engine = IntentDeterminationEngine()

# 1. register vocabulary: surface forms grouped by entity type
for word in ["weather", "forecast"]:
    engine.register_entity(word, "WeatherKeyword")
for city in ["Seattle", "San Francisco", "Tokyo"]:
    engine.register_entity(city, "Location")
for kind in ["snow", "rain", "wind", "sun"]:
    engine.register_entity(kind, "WeatherType")

# 2. build an intent over those entity types
weather = IntentBuilder("WeatherIntent") \
    .require("WeatherKeyword") \
    .require("Location") \
    .optionally("WeatherType") \
    .build()
engine.register_intent_parser(weather)

# 3. match
for intent in engine.determine_intent("what is the rain forecast in Tokyo"):
    if intent.get("confidence", 0) > 0:
        print(intent)
```

Output (abridged):

```python
{'intent_type': 'WeatherIntent',
 'WeatherKeyword': 'forecast',
 'Location': 'Tokyo',
 'WeatherType': 'rain',
 'confidence': 0.72}
```

`determine_intent` yields one result per clique, best first. Filter on
`confidence > 0`, a zero score means a required slot was missing.

More runnable examples ship in the [`examples/`](../examples) folder.

## Enable the pipeline in OVOS

In a full OVOS install the plugin runs as a pipeline stage. Add its entry-point
id to the pipeline list in `mycroft.conf`:

```json
{
  "intents": {
    "pipeline": [
      "ovos-adapt-pipeline-plugin-high",
      "ovos-padatious-pipeline-plugin-high",
      "ovos-adapt-pipeline-plugin-medium",
      "ovos-adapt-pipeline-plugin-low"
    ]
  }
}
```

The `-high` / `-medium` / `-low` suffixes select the confidence tier for that
slot in the pipeline (see [Configuration](configuration.md)). Skills then
register their vocabulary and intents over the messagebus. The plugin matches
incoming utterances automatically. You do not call the engine yourself, see
[Bus protocol](bus-protocol.md) for what happens under the hood.

## Next

- [Writing intents](writing-intents.md), `require` / `optionally` / `one_of` /
  `exclude`, regex entities, and full examples.
- [Configuration](configuration.md), tune the confidence thresholds.

---
[← Concepts](concepts.md) · [Home](index.md) · [Writing intents →](writing-intents.md)

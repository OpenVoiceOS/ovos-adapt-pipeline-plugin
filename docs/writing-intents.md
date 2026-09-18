# Writing intents

This page is the practical reference for defining vocabulary and intents.

## Registering vocabulary

Vocabulary is registered on the engine as `(surface_form, entity_type)` pairs.
Register every form a user might say:

```python
engine.register_entity("lights", "LightKeyword")
engine.register_entity("light", "LightKeyword")
engine.register_entity("lamp", "LightKeyword")
```

All three are type `LightKeyword`. An intent that requires `LightKeyword`
matches if any one of them appears. Matching is exact and case-insensitive.
Register plurals, contractions, and synonyms explicitly.

### Aliases

`alias_of` records that one surface form should be reported as another, useful
when several spellings should resolve to one canonical value:

```python
engine.register_entity("NYC", "City", alias_of="New York")
```

A match on `NYC` reports the value `New York`.

## Building intents

`IntentBuilder` is a fluent builder. Chain rules, then `build()`:

```python
from ovos_adapt.intent import IntentBuilder

intent = IntentBuilder("kitchen.lights:turn_off") \
    .require("OffKeyword") \
    .require("LightKeyword") \
    .optionally("RoomKeyword") \
    .build()
engine.register_intent_parser(intent)
```

### `require(entity_type)`

The intent only fires when a tag of this type is present. Missing any required
type scores the intent **zero**. Use `require` for the words that define the
command.

### `optionally(entity_type)`

Used when present, ignored when absent. An optional tag that *is* found raises
the confidence (it explains more of the utterance) but never blocks a match.
Use it for refinements, a room name, a media genre.

### `one_of([entity_type, ...])`

At least one type from the list must be present. Use it when a command can be
triggered several equivalent ways:

```python
IntentBuilder("media:stop") \
    .one_of(["StopKeyword", "PauseKeyword", "HaltKeyword"]) \
    .require("MediaKeyword") \
    .build()
```

### `exclude(entity_type)`

The intent is rejected outright if a tag of this type is present. Use it to
keep two similar intents apart:

```python
# "play music" but NOT "stop music"
IntentBuilder("media:play") \
    .require("PlayKeyword") \
    .require("MediaKeyword") \
    .exclude("StopKeyword") \
    .build()
```

## Regex entities

For values you cannot enumerate, numbers, free text, register a regular
expression with a named group. The group name becomes the entity type.

```python
engine.register_regex_entity(r"for (?P<Duration>\d+) minutes")
```

A match on *"set a timer for 10 minutes"* produces a `Duration` tag with value
`10`. Use regex entities for slots, and keep `require`/`optionally` keywords for the
words that identify the command.

## A complete example

```python
from ovos_adapt.intent import IntentBuilder
from ovos_adapt.engine import IntentDeterminationEngine

engine = IntentDeterminationEngine()

for w in ["turn on", "switch on"]:
    engine.register_entity(w, "OnKeyword")
for w in ["turn off", "switch off"]:
    engine.register_entity(w, "OffKeyword")
for w in ["light", "lights", "lamp"]:
    engine.register_entity(w, "LightKeyword")
for w in ["kitchen", "bedroom", "hallway"]:
    engine.register_entity(w, "RoomKeyword")

engine.register_intent_parser(
    IntentBuilder("lights:on")
    .require("OnKeyword").require("LightKeyword")
    .optionally("RoomKeyword").build())

engine.register_intent_parser(
    IntentBuilder("lights:off")
    .require("OffKeyword").require("LightKeyword")
    .optionally("RoomKeyword").build())

for intent in engine.determine_intent("switch on the kitchen lights"):
    if intent.get("confidence", 0) > 0:
        print(intent["intent_type"], intent.get("RoomKeyword"))
        # -> lights:on kitchen
```

## Tips

- **Name intents `skill_id:intent_name`.** OVOS routes a match back to the
  skill by the `skill_id` prefix. The colon convention is expected.
- **Multi-word keywords must be contiguous.** `"turn off"` is registered as one
  surface form and only tags when those words appear together. `"turn the
  lights off"` will *not* match the keyword `"turn off"`.
- **More `require`d slots = a sharper, higher-confidence intent.** A
  single-keyword intent fires on that lone word in any sentence. A two-slot
  intent demands a real command shape.
- **Disambiguate overlapping intents** with `exclude`, not by hoping confidence
  sorts them out.

## In an OVOS skill

Skills built with `ovos-workshop` do not call the engine directly, they
register vocabulary and intents over the messagebus, and this plugin consumes
those messages. The `IntentBuilder` API above is exactly what the skill side
uses. See [Bus protocol](bus-protocol.md) for the message flow.

---
[← Quickstart](quickstart.md) · [Home](index.md) · [Configuration →](configuration.md)

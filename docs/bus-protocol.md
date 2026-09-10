# Bus protocol

In a full OVOS install the plugin is driven entirely over the messagebus.
Skills emit registration messages. The plugin matches utterances and emits
results. This page documents that contract, useful when writing a skill
framework, debugging, or integrating a non-standard skill.

## Registration messages (skill → plugin)

The plugin listens for four messages:

### `register_vocab`

Registers one entity. `message.data`:

| Field | Meaning |
|---|---|
| `entity_value` | the surface form, e.g. `"Tokyo"` |
| `entity_type` | the type, e.g. `"Location"` |
| `regex` | a regex string (instead of `entity_value`/`entity_type`) |
| `alias_of` | optional canonical form this value resolves to |
| `lang` | language tag; routed to that language's engine |

A plain keyword sends `entity_value` + `entity_type`. A regex entity sends
`regex` (with a named group). One message registers one entity, so a skill
emits many.

### `register_intent`

Registers a built intent. The data is an intent envelope produced by
`IntentBuilder(...).build()` and serialised by `ovos_workshop.intents`. The
plugin reconstructs the parser and adds it to the engine.

### `detach_intent`

Removes a single intent. `message.data['intent_name']`, the intent's name.

### `detach_skill`

Removes every intent and vocab item belonging to a skill.
`message.data['skill_id']`, all intents whose name starts with that prefix are
dropped. Emitted when a skill unloads.

## Query messages

### `intent.service.adapt.get`

Ask the plugin to match an utterance directly (debugging / introspection). The
plugin replies with the best intent or a null match.

### `intent.service.adapt.manifest.get`

Replies with the list of registered intents.

### `intent.service.adapt.vocab.manifest.get`

Replies with the list of registered vocabulary.

## Matching flow

The plugin does not match on `register_*`. Matching is driven by the OVOS
intent service, which calls the tier methods (`match_high`, `match_medium`,
`match_low`) as it walks the configured pipeline. Each call:

1. takes the incoming utterance(s) for the session language,
2. skips anything longer than `max_words`,
3. runs the engine's `determine_intent`,
4. returns the best result **if** its confidence clears the tier threshold,
5. on a returned match, feeds the matched entities back into the session
   context so follow-up utterances can use them.

## Result shape

A match is an `IntentHandlerMatch` carrying:

- `match_type`, the intent name (`skill_id:intent_name`)
- `match_data`, the parsed intent dict: `confidence`, every matched slot keyed
  by entity type, and `__tags__` (the raw tags, used for context)
- `skill_id`, the owning skill, taken from the intent-name prefix
- `utterance`, the utterance that matched

## Sessions and context

Each match updates the `Session` context with the entities it consumed.
A later utterance can then satisfy a `require`d slot from context instead of
from its own words, this is how follow-up commands ("...and the bedroom one
too") resolve. Context is per-session. See [Internals](internals.md).

---
[← Pipeline variants](pipelines.md) · [Home](index.md) · [Internals →](internals.md)

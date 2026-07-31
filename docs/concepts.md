# Concepts

This page explains *how* Adapt decides which intent an utterance belongs to.
No prior knowledge is assumed.

## The problem

A user says *"what's the weather in Tokyo"*. The assistant must decide which
registered action, which **intent**, that sentence is asking for, and pull
out the useful values (`Tokyo`). Adapt solves this with keyword matching plus a
few combination rules.

## Entities

An **entity** is a named value. You register entities by listing their possible
surface forms and giving each a **type**:

```text
type "WeatherKeyword"  ->  "weather", "forecast"
type "Location"        ->  "Seattle", "San Francisco", "Tokyo"
```

When Adapt sees one of those words in an utterance, it **tags** it: the word
`Tokyo` becomes a tag of type `Location`. Tagging is exact, Adapt only finds
words you registered. There is no fuzzy matching and no generalisation.

Internally every registered surface form is stored in a **Trie** (a prefix
tree), so tagging an utterance is fast even with thousands of entities.

## Intents

An **intent** is an action, defined as a set of requirements over entity
*types*. You build one with `IntentBuilder`:

```python
from ovos_adapt.intent import IntentBuilder

weather = IntentBuilder("WeatherIntent") \
    .require("WeatherKeyword") \
    .require("Location") \
    .optionally("WeatherType") \
    .build()
```

This says: the `WeatherIntent` fires when the utterance contains **both** a
`WeatherKeyword` tag and a `Location` tag. A `WeatherType` tag is used if
present but is not required.

The four rules an intent can use:

| Rule | Meaning |
|---|---|
| `require(type)` | the intent only matches if a tag of this type is present |
| `optionally(type)` | used if present, ignored if absent, adds confidence |
| `one_of([types])` | at least one of these types must be present |
| `exclude(type)` | the intent is rejected if a tag of this type is present |

An intent that misses any `require` (or `one_of`, or hits an `exclude`) scores
**zero** and does not fire.

## Cliques: handling overlap

A word can be tagged as more than one type, and two tags can cover overlapping
parts of the utterance. Adapt cannot use two overlapping tags in the same
answer, so it expands the tag list into **cliques**, maximal sets of tags that
do *not* overlap each other. Each clique is one self-consistent reading of the
utterance. Every intent is then validated against each clique.

## Confidence

OVOS pipelines work in confidence scores between 0 and 1. Adapt computes an
intent's confidence from three things:

```text
confidence = intent_weight / total_tags  x  clique_coverage
```

- **intent_weight**, how many of the clique's tags this intent actually used
  (its required + optional slots). More matched slots → higher weight.
- **total_tags**, how many tags the clique has in total. Tags the intent did
  *not* use still divide the score, so an utterance crowded with unrelated
  keywords **dilutes** every intent.
- **clique_coverage**, how much of the utterance, character for character, the
  clique's tags cover. Longer matched keywords cover more and score higher.

The practical consequences:

- An intent that explains *more* of the utterance scores higher.
- A short keyword buried in a long sentence scores low, most of the sentence
  is uncovered.
- Stray keywords from other intents lower everyone's score.

## Confidence tiers

OVOS runs pipeline plugins in three passes, `match_high`, `match_medium`,
`match_low`. Adapt exposes the same matching at three thresholds
(`conf_high` 0.65, `conf_med` 0.45, `conf_low` 0.25). A match is only returned
in a pass if its confidence clears that pass's threshold, so a confident Adapt
intent is matched before lower-confidence pipeline stages get a turn. See
[Configuration](configuration.md).

## Next

- [Quickstart](quickstart.md), see all of this run end to end.
- [Writing intents](writing-intents.md), the full `IntentBuilder` API with
  worked examples.
- [Internals](internals.md), the exact tagging, clique, and confidence maths.

---
[Home](index.md) · [Quickstart →](quickstart.md)

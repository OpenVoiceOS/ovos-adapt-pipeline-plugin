# ovos-adapt-pipeline-plugin documentation

`ovos-adapt-pipeline-plugin` is an OVOS intent pipeline plugin. It matches a
spoken utterance to a registered intent using **keyword and rule matching** —
no training step, no model files, no GPU. It bundles a maintained fork of the
original MycroftAI [adapt](https://github.com/MycroftAI/adapt) parser.

This documentation goes from zero to hero. If you have never written an intent,
start at [Concepts](concepts.md). If you just want it running, jump to the
[Quickstart](quickstart.md).

## Reading order

**New to intent parsing** — read in order:

1. [Concepts](concepts.md) — what an entity, an intent, and a confidence score are
2. [Quickstart](quickstart.md) — install, enable, and match your first utterance
3. [Writing intents](writing-intents.md) — register vocabulary and build intents
4. [Configuration](configuration.md) — confidence tiers and every config key

**Building on or extending the plugin:**

5. [Bus protocol](bus-protocol.md) — the messagebus API skills use to register
6. [Internals](internals.md) — the tagger, clique expansion, the confidence math

## At a glance

```text
utterance
  -> tokenize into words
  -> tag every entity found in the vocabulary Trie
  -> expand the tags into non-overlapping entity sets ("cliques")
  -> validate each intent's required / optional slots against a clique
  -> confidence = matched-slot weight / total tags  x  clique coverage
  -> the highest-confidence intent wins
```

## Where Adapt fits

OVOS runs several intent matchers in a pipeline. Adapt is the **keyword/rule**
matcher:

- **Adapt** — you list the words that trigger each intent. Deterministic,
  registers instantly, no training. Best for command-style intents
  (*"turn off the kitchen lights"*).
- **Padatious / Padacioso** — train a small model on example sentences.
  Generalises to phrasings you did not write, at the cost of a training step.
- **Common Query / fallback** — catch-all stages for everything else.

A skill can register intents with whichever matcher suits each intent. Adapt is
the right choice when the trigger words are known and finite.

## Requirements

- Python 3.10+
- `ovos-plugin-manager`, `ovos-bus-client`, `ovos-config`, `ovos-utils`,
  `ovos-workshop`

The adapt parser itself (`ovos_adapt.engine`, `ovos_adapt.intent`) has no
runtime dependency beyond the standard library and can be used standalone.

# Pipeline variants

The package ships **three** OPM pipeline plugins. All match intents with the
same Adapt engine and expose the same bus protocol. They differ only in how
intents are *organised* and *scored*.

| Plugin class | Entry-point id | Config section |
|---|---|---|
| `AdaptPipeline` | `ovos-adapt-pipeline-plugin` | `intents.ovos-adapt-pipeline-plugin` |
| `DomainAdaptPipeline` | `ovos-adapt-domain-pipeline-plugin` | `intents.ovos_adapt_domain_pipeline` |
| `HierarchicalAdaptPipeline` | `ovos-adapt-hierarchical-pipeline-plugin` | `intents.ovos_adapt_hierarchical_pipeline` |

Each is selected by adding its id (with a `-high` / `-medium` / `-low` tier
suffix) to `intents.pipeline`, see [Configuration](configuration.md). They can
coexist. Each reads its own config section.

## flat, `AdaptPipeline`

One `IntentDeterminationEngine`. Every intent parser and every entity share a
single Trie and tagger. This is the default and the right choice for almost all
installs.

## domain, `DomainAdaptPipeline`

A `DomainIntentDeterminationEngine`. Intents are grouped into **domains**, one
per `skill_id`, taken from the `skill_id:intent_name` label, and each domain
gets its own isolated sub-engine (its own Trie and tagger). At match time every
domain is scored and the global argmax wins.

Isolating each skill's vocabulary in its own Trie means a domain's parses carry
fewer foreign tags. Because Adapt's confidence divides by the total tag count of
a parse (see [Internals](internals.md)), less foreign vocabulary means less
dilution. On a clean single-intent command this changes the score but not the
winner. It can matter on utterances that carry several skills' keywords.

## hierarchical, `HierarchicalAdaptPipeline`

A `HierarchicalIntentDeterminationEngine`, the same per-skill domain model as
above, but two-stage. A stage-1 keyword-coverage classifier picks **one** domain
first, then only that domain's sub-engine is scored. A misrouted domain cannot
be recovered, so this trades recall (a wrong route loses the command) for
precision (a stray keyword routed to an unrelated domain triggers nothing).

## Which should I use?

Use the **flat** `AdaptPipeline` unless you have a specific reason not to. The
domain and hierarchical variants change *how* matching is organised, not its
correctness. Whether they help depends on your skill mix and how command-like
your false traffic is. The differences, and how they can be measured or
misrepresented, are covered in detail in the
[engine comparison reference](benchmark.md).

## Engine classes

All three pipelines are thin wrappers over engine classes in
`ovos_adapt.engine`, which can be used standalone:

- `IntentDeterminationEngine`, flat
- `DomainIntentDeterminationEngine`, per-domain, parallel argmax
- `HierarchicalIntentDeterminationEngine`, per-domain, two-stage routing

See [Internals](internals.md) and [Quickstart](quickstart.md) for direct engine
use.

---
[← Configuration](configuration.md) · [Home](index.md) · [Bus protocol →](bus-protocol.md)

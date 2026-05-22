# Internals

This page traces what happens inside `determine_intent`, derives the confidence
formula from the source, and covers the domain engine and context. It is for
developers extending the plugin or debugging surprising scores.

## The matching pipeline

`IntentDeterminationEngine.determine_intent(utterance, num_results=1)` runs four
stages:

```text
utterance
  1. tag      EntityTagger      -> every entity occurrence in the utterance
  2. expand   BronKerboschExpander -> non-overlapping tag sets (cliques)
  3. validate Intent.validate_with_tags -> best intent per clique
  4. rank     -> highest-confidence intent overall
```

### 1. Tagging

The engine keeps every registered surface form in a **Trie** (`ovos_adapt`'s
`trie.py`). The `EntityTagger` walks the tokenised utterance against the Trie
and against any registered regex entities, emitting a tag for every match —
position, matched text, entity type, and a per-entity confidence. One word can
produce several tags if it was registered under several types.

### 2. Clique expansion

Tags can overlap in the utterance, and a valid answer cannot use two
overlapping tags at once. The `BronKerboschExpander` treats "does not overlap"
as a graph edge and finds **maximal cliques** — each clique is one complete,
self-consistent set of non-overlapping tags. Cliques are scored and yielded
best-first; `num_results` (`N`) caps how many are produced.

The clique score (`score_clique` in `parser.py`) is:

```text
clique_score = Σ  entity_confidence × len(match) / (len(utterance) + 1)
```

summed over the clique's tags — i.e. how much of the utterance the clique
covers, weighted by each tag's confidence.

### 3. Validation

For each clique, `__best_intent` runs every registered intent's
`validate_with_tags(tags, clique_confidence)` and keeps the highest scorer.

### 4. Ranking

`determine_intent` yields one best-intent per clique. Callers take the global
maximum by `confidence`.

## The confidence formula

`Intent.validate_with_tags` (in `ovos_workshop.intents`) computes:

```text
intent_confidence = Σ  tag_confidence   over the intent's used slots
                    (required + one_of + optional tags it matched)

total_confidence  = intent_confidence / len(tags)  ×  clique_confidence
```

where `len(tags)` is **every** tag in the clique — including tags this intent
did not use. Three forces, then:

- **`intent_confidence`** rises with each required/optional slot the intent
  fills. More matched slots → higher score.
- **`len(tags)`** is a divisor over *all* clique tags. Tags belonging to other
  intents still divide the score — unrelated keywords in the utterance
  **dilute** every intent equally.
- **`clique_confidence`** is the coverage term — longer matched keywords, and
  more of the utterance explained, score higher.

A missing `require`d slot, an unmet `one_of`, or a hit `exclude` short-circuits
to `confidence = 0.0`.

### Worked example

Utterance *"turn off the kitchen lights"*, intent `lights:off` requiring
`OffKeyword` + `LightKeyword`, optional `RoomKeyword`. The best clique tags
`turn off` (Off), `kitchen` (Room), `lights` (Light) — 3 tags, all used by the
intent. `intent_confidence` sums all three; `len(tags)` is 3; `clique_confidence`
reflects that those three tags cover most of the sentence. The score is high.

Add an unrelated registered word — say `play` — and a fourth tag appears.
`lights:off` still uses 3 tags but `len(tags)` is now 4, so its score drops even
though the command is unchanged. This dilution is the main reason scores differ
between engine topologies (see below).

## Domain engines

Two engine classes group intents into **domains** — each domain backed by its
own `IntentDeterminationEngine` (its own Trie, tagger, and parser set).
Registration takes a `domain=` argument.

**`DomainIntentDeterminationEngine`** scores every domain and the caller takes
the global argmax. Because each domain tags against only its own vocabulary, a
domain's cliques carry fewer foreign tags, so the `len(tags)` dilution above is
smaller than in a single flat engine. On a clean single-intent utterance this
changes the score but not the winner; on utterances carrying several intents'
keywords it can change which intent wins.

**`HierarchicalIntentDeterminationEngine`** subclasses the above and keeps the
same registration API. Its `determine_intent` is two-stage: a `classify_domain`
keyword-coverage classifier picks a single domain, then only that domain's
sub-engine is scored. A misrouted domain cannot be recovered.

The `DomainAdaptPipeline` and `HierarchicalAdaptPipeline` plugins wrap these two
engines — see [Pipeline variants](pipelines.md). The
[engine comparison reference](benchmark.md) measures how the three topologies
diverge and explains why.

## Context

A returned match feeds its matched entities into the `Session` context. On the
next utterance the tagger seeds the Trie with those context entities (weighted
by recency), so a `require`d slot can be satisfied from context rather than from
the utterance's own words. This is how follow-up commands resolve. Context is
per-session and decays as new entities arrive.

## Debugging tips

- **An intent scores 0** — a required slot has no tag. Confirm the exact
  surface form is registered (matching is exact) and that multi-word keywords
  appear contiguously.
- **The wrong intent wins** — inspect `__tags__` on the result. Usually a
  competing intent covered more of the utterance, or a stray keyword diluted
  the right one. Add `require`d slots or an `exclude`.
- **Confidence lower than expected** — short keyword, long utterance: little is
  covered. Register longer surface forms or add `optionally` slots.
- **Run the engine standalone** — drop the messagebus and call
  `determine_intent` directly (see [Quickstart](quickstart.md)); print every
  yielded result, not just the best, to see the full ranking.

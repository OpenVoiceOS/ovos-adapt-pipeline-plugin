# Benchmark

`benchmark/compare.py` measures intent-matching accuracy and speed of three
Adapt engine topologies on one shared keyword dataset:

- **flat** — a single `IntentDeterminationEngine`. Every intent parser and
  every entity share one `Trie` and one entity tagger.
- **domain** — a `DomainIntentDeterminationEngine`. Intents are grouped into
  domains; each domain owns an isolated sub-engine with its own `Trie` and
  tagger. Every domain is scored and the global argmax wins.
- **hierarchical** — true two-stage routing. A stage-1 keyword-coverage
  classifier picks one domain; stage 2 runs only that domain's sub-engine.
  A wrong stage-1 route cannot be recovered.

## Dataset

`benchmark/dataset.py` defines the vocabulary, intents, domain grouping, and
labelled utterances:

```text
Cases   : 171  (125 match, 46 no-match)
Intents : 26   across 11 domains
```

Intents are mostly **two-slot** — an ACTION keyword plus an OBJECT keyword
(`turn` + `up` + `the` + `volume`), so a single stray keyword cannot trigger
an intent on its own. OBJECT vocabularies are domain-distinctive (`thermostat`
only appears in *climate*, `playlist` only in *media*); ACTION vocabularies are
deliberately shared across domains (`turn up` is both a volume and a heating
action). A few intents are genuinely single-trigger (`weather_query`,
`navigate_to`, `get_help`) and stay one-slot.

The 46 `NO_MATCH_UTTERANCES` are plausible but not commands, many containing a
keyword used outside a command context (`"they cancel each other out"`).

## Metrics

- **Accuracy** — correct predictions over all cases (a no-match case is
  correct when the engine returns nothing).
- **Precision / Recall / F1** — over the match cases.
- **TN / FP** — true negatives and false positives over the no-match cases.
- **Head-to-head** — the cases where flat and domain predict a *different*
  intent. This isolates the effect of trie isolation from the dataset.
- **Stage-1 routing** — for the hierarchical engine, the share of match cases
  whose stage-1 classifier picked the domain that owns the correct intent.
- **Latency** — per-query wall time.

## Results

Single run, all engines on the same machine and dataset:

| Engine | Accuracy | Precision | Recall | F1 | TN/NM | FP | FN | Median lat |
|---|---|---|---|---|---|---|---|---|
| flat         | 94.2% | 92.6% | 100.0% | 0.962 | 36/46 | 10 | 0 | 0.22 ms |
| domain       | 94.2% | 92.6% | 100.0% | 0.962 | 36/46 | 10 | 0 | 0.82 ms |
| hierarchical | 94.7% | 94.6% |  98.4% | 0.965 | 39/46 |  7 | 2 | 0.32 ms |

Flat vs domain head-to-head: **0 / 171 different** — identical predictions.

Hierarchical stage-1 routing: **123 / 125 match cases (98%)** routed to the
correct domain.

## Interpreting the results

**Flat and domain are identical.** With two-slot intents and domain-distinctive
object vocabularies, the two engines agree on every one of the 171 cases. A
parser only fires when its own required entity types are tagged; a domain
sub-engine's trie holds exactly those types, so isolation removes only tags no
parser would have used. `DomainIntentDeterminationEngine` is a packaging and
lifecycle convenience here, not an accuracy change.

**Two-stage routing trades recall for precision.** The hierarchical engine
edges ahead — 94.7% vs 94.2% — but the gain is a precision/recall swap, not a
free win:

- It suppresses **3 false positives**. Each is a no-match utterance containing
  a bare keyword for a *single-slot* intent — `"they cancel each other out"`,
  `"stop right there"`, `"can you cancel it"`. Flat fires `stop_all` on the
  lone `stop` / `cancel`. The classifier routes these to a *two-slot* domain
  (*media* or *timers*), whose intents need a second keyword that is absent, so
  nothing fires and no false positive is emitted. FP drops 10 → 7, precision
  rises 92.6% → 94.6%.
- It costs **2 false negatives**. Bare `"stop"` and `"cancel"`, issued as real
  `stop_all` commands, are routed by the *same* mechanism to a domain that does
  not own `stop_all`, so the command is lost. Recall drops 100% → 98.4%.

Both effects come from one cause: a one-word utterance gives the stage-1
classifier nothing to disambiguate, so it routes by a vocabulary-overlap
tie-break. When the utterance is genuinely off-topic that accidentally helps;
when it is a real command it hurts. Two-stage routing cannot recover an
utterance whose domain is ambiguous from its own text.

**Routing must be reliable for two-stage to be viable.** Stage 1 here is a
keyword-coverage classifier and routes 98% of match cases correctly — only
because the dataset's OBJECT vocabularies are domain-distinctive. With muddy,
overlapping domain vocabulary the router degrades and every misroute is an
unrecoverable error; two-stage is only worth it when domains are lexically
separable.

**Latency.** Flat is fastest (~0.2 ms). Hierarchical (~0.3 ms) runs a cheap
classifier plus one sub-engine. The parallel domain engine (~0.8 ms) evaluates
every sub-engine per query. All are far below any perceptible threshold.

## How to run

```bash
python benchmark/compare.py
```

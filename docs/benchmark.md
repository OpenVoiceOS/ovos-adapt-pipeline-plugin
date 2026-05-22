# Benchmark

`benchmark/compare.py` measures intent-matching accuracy and speed of three
Adapt engine topologies on one shared keyword dataset:

- **flat** — a single `IntentDeterminationEngine`. Every intent parser and
  every entity share one `Trie` and one entity tagger.
- **domain** — a `DomainIntentDeterminationEngine`. Intents are grouped into
  domains; each domain owns an isolated sub-engine with its own `Trie` and
  tagger. Every domain is scored and the global argmax wins.
- **hierarchical** — true two-stage routing. A stage-1 domain classifier (a
  flat engine whose 'intents' are domains, each requiring a pooled keyword
  entity covering every word the domain uses) picks one domain; stage 2 runs
  only that domain's sub-engine. A wrong stage-1 route cannot be recovered.

## Dataset

`benchmark/dataset.py` defines the vocabulary, intents, domain grouping, and
labelled utterances:

```text
Cases   : 329  (249 match, 80 no-match)
Intents : 22   across 10 domains
Vocab   : 184 keyword samples across 28 entity types
```

`TEST_CASES` are natural-language utterances — contractions, filler words,
politeness markers, word-order variation — not template fills. It includes a
dedicated **entity-overlap** section: utterances built around words registered
under two or more entity types spanning two or more domains (`turn up` is both
a `VolumeKeyword` in *media* and a `HeatKeyword` in *climate*; `temperature` is
both a `WeatherKeyword` and a `ThermostatKeyword`; `stop` / `cancel` / `kill`
span *media*, *timers*, and *lights*). These are the only cases where a
per-domain trie can tag an utterance differently from a shared trie.

The 80 `NO_MATCH_UTTERANCES` are plausible but off-topic, many sharing surface
words with real intents (e.g. *"the music just would not stop"*) to stress the
false-positive rate.

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
| flat         | 79.3% | 79.6% | 91.2% | 0.850 | 34/80 | 58 | 22 | 0.23 ms |
| domain       | 79.3% | 79.6% | 91.2% | 0.850 | 34/80 | 58 | 22 | 0.94 ms |
| hierarchical | 74.5% | 80.2% | 81.5% | 0.809 | 42/80 | 50 | 46 | 0.38 ms |

Flat vs domain head-to-head:

```text
Cases             : 329
Same prediction   : 318
Different         :  11   (3.3%)
```

Of the 11 cases where flat and domain diverge: domain is correct on 4, flat is
correct on 4, and both are wrong on 3 (a different false positive each).

Hierarchical stage-1 routing: **211 / 249 match cases (85%)** are routed to the
correct domain. The other 15% are misrouted and cannot be recovered by stage 2.

## Interpreting the results

**The engines are not identical, but neither is better.** Trie isolation does
change the matched intent — on 11 of 329 cases (3.3%), all of them
entity-overlap utterances. But the divergences cancel: every case domain wins,
another case flat wins, so all aggregate metrics are equal to three decimals.

**Why they diverge.** A domain sub-engine's `Trie` holds only the entity types
its own intents declare. So a domain sub-engine tags *fewer* entities in an
utterance than the shared flat trie does. Adapt confidence is driven by how
much of the utterance tagged entities cover, so dropping foreign tags shifts
the per-intent confidences and can flip the global argmax. Examples:

- *"what are the symptoms of a cold"* — flat tags `cold` as a `WeatherKeyword`
  and matches `weather_query`; the *information* sub-engine has no
  `WeatherKeyword`, so `cold` is not tagged and `search_query` wins (domain
  correct).
- *"how warm is it today"* — flat matches `weather_query`; in domain mode the
  *information* sub-engine scores `date_query` on `today` slightly higher than
  the *weather* sub-engine scores `weather_query` on `warm`, and the global
  argmax flips to `date_query` (domain wrong).

The flip is a side effect of which entities happen to be visible, not a
smarter decision — which is why the wins and losses come out even.

**Two-stage routing is worse, not better.** The hierarchical engine scores
74.5% — five points below flat — because hard stage-1 routing is lossy.
Stage 1 misroutes 15% of match cases, and a misrouted utterance is
unrecoverable: stage 2 only ever sees one domain. Recall drops from 91.2% to
81.5% as a direct result.

This is structural, not a tuning problem. Flat global-argmax already considers
every intent, so it is an *upper bound* that hard two-stage routing cannot
exceed — two-stage only ever removes candidates. The misroutes are caused by
the same shared vocabulary the overlap cases stress: `cancel the timer` routes
to *media* because `cancel` is a `StopKeyword` there, never reaching the
*timers* domain that owns `cancel_timer`.

Hierarchical does buy a little precision: the stage-1 gate rejects 8 more
no-match utterances (TN 34 → 42, FP 58 → 50), lifting precision to 80.2%. But
the recall it sacrifices to get there costs far more accuracy than the
precision it gains. It is also faster than the parallel domain engine
(~0.38 ms vs ~0.94 ms) because stage 2 evaluates only one sub-engine — but
speed was never the bottleneck.

**Domain routing costs latency.** The parallel domain engine evaluates every
domain's sub-engine per query, so median latency rises from ~0.2 ms to
~0.9 ms. Both remain far below any perceptible threshold.

**False positives are inherent to keyword matching.** 46 of the 80 no-match
utterances trigger a parse under both engines because they contain a required
keyword used outside a command context (*"the heating engineer came round"*,
*"they cancel each other out"*). This is a property of keyword parsing, not of
engine topology — domain grouping does not address it.

## When the domain engine is still useful

The benchmark measures accuracy, not lifecycle. `DomainIntentDeterminationEngine`
keeps each domain's parsers, entities, and regexes in a separate sub-engine,
which makes it cheap to add or drop a whole domain at runtime (`remove_domain`)
without rebuilding a shared `Trie`. That is an operational benefit; it does not
show up as an accuracy difference.

## How to run

```bash
python benchmark/compare.py
```

# Benchmark

`benchmark/compare.py` measures intent-matching accuracy and speed of the
two Adapt engine topologies on one shared keyword dataset:

- **flat** — a single `IntentDeterminationEngine`. Every intent parser and
  every entity share one `Trie` and one entity tagger.
- **domain** — a `DomainIntentDeterminationEngine`. Intents are grouped into
  domains; each domain owns an isolated sub-engine with its own `Trie` and
  tagger. Every domain is scored and the global argmax wins.

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
- **Latency** — per-query wall time.

## Results

Single run, both engines on the same machine and dataset:

| Engine | Accuracy | Precision | Recall | F1 | TN/NM | FP | FN | Median lat |
|---|---|---|---|---|---|---|---|---|
| flat   | 79.3% | 79.6% | 91.2% | 0.850 | 34/80 | 58 | 22 | 0.28 ms |
| domain | 79.3% | 79.6% | 91.2% | 0.850 | 34/80 | 58 | 22 | 0.85 ms |

Head-to-head:

```text
Cases             : 329
Same prediction   : 318
Different         :  11   (3.3%)
```

Of the 11 cases where the engines diverge: domain is correct on 4, flat is
correct on 4, and both are wrong on 3 (a different false positive each).

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

**Domain routing costs latency.** The domain engine evaluates every domain's
sub-engine per query, so median latency rises from ~0.3 ms to ~0.85 ms. Both
remain far below any perceptible threshold.

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

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
Cases   : 284  (217 match, 67 no-match)
Intents : 22   across 10 domains
Vocab   : 184 keyword samples across 28 entity types
```

`TEST_CASES` are natural-language utterances — contractions, filler words,
politeness markers, word-order variation — not template fills. The 67
`NO_MATCH_UTTERANCES` are plausible but off-topic, many sharing surface words
with real intents (e.g. *"the music at that restaurant was terrible"*) to
stress-test the false-positive rate.

## Metrics

- **Accuracy** — correct predictions over all cases (a no-match case is
  correct when the engine returns nothing).
- **Precision / Recall / F1** — over the match cases.
- **TN / FP** — true negatives and false positives over the no-match cases.
- **Latency** — per-query wall time.

## Results

Single run, both engines on the same machine and dataset:

| Engine | Accuracy | Precision | Recall | F1 | TN/NM | FP | FN | Median lat |
|---|---|---|---|---|---|---|---|---|
| flat   | 80.3% | 81.0% | 90.3% | 0.854 | 32/67 | 46 | 21 | 0.18 ms |
| domain | 80.6% | 81.4% | 90.8% | 0.858 | 32/67 | 45 | 20 | 0.74 ms |

## Interpreting the results

**Domain grouping does not change matching quality here.** Accuracy,
precision, recall, and the true-negative count are within one case of each
other. Both engines reject the same 32 of 67 no-match utterances.

The reason is structural. Adapt isolates vocabulary by giving each domain its
own `Trie`, so a shared engine tags *more* entities in an utterance. But an
intent parser only fires when **its own** required entity types are tagged —
extra tags from unrelated intents do not satisfy a parser that needs a
different type. Entity types are also globally named, so an entity carries
the same type whether it is registered once or per domain. The extra tags a
flat engine produces are therefore inert for parsers that gate on required
types, and grouping changes neither the winning parse nor its confidence.

**Domain routing costs latency.** The domain engine evaluates every domain's
sub-engine per query, so median latency rises from ~0.18 ms to ~0.74 ms. Both
remain far below any perceptible threshold.

**The false positives are inherent to keyword matching.** 35 of the 67
no-match utterances trigger a parse under both engines because they contain a
required keyword used outside a command context (*"i always stop for coffee"*,
*"the forecast was wrong again"*). This is a property of keyword parsing, not
of engine topology — domain grouping does not address it.

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

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

## How the topologies can differ

Adapt scores a parse with
`confidence = intent_confidence / len(clique_tags) × clique_confidence`,
where `clique_tags` is *every* entity tagged in the matched clique — including
entities from unrelated intents. So an intent's confidence is **diluted by the
number of foreign tags** sharing its clique.

- **flat** tags an utterance against every domain's vocabulary at once, so
  cliques carry the most foreign tags and dilute the most.
- **domain** tags each utterance against one domain's vocabulary at a time, so
  cliques are smaller and the in-domain intent is diluted less.
- **hierarchical** additionally discards every domain but one before scoring.

On a clean single-intent utterance all three pick the same winner — there is
no competitor for dilution to reorder. They diverge on utterances that carry
more than one intent's keywords.

## Dataset

`benchmark/dataset.py` defines the vocabulary, intents, domain grouping, and
labelled utterances:

```text
Cases   : 195  (139 match, 56 no-match)
Intents : 26   across 11 domains
```

Intents are mostly **two-slot** — a shared ACTION keyword plus a
domain-distinctive OBJECT keyword — so a single stray keyword cannot trigger an
intent. Beyond the everyday cases, the dataset carries three hand-crafted
discriminating sections, each built to give one topology a clear edge:

- **flat & domain win, hierarchical loses** — real commands carrying a long
  room/topic word (or a bare one-word command) that pulls the stage-1
  classifier to the wrong domain. The misroute is unrecoverable.
- **flat and domain diverge** — two-clause utterances carrying two intents,
  labelled by the leading clause. Flat scores both clauses in one shared
  clique; domain scores each clause in its own sub-engine. The dilution term
  breaks the clause tie differently.
- **hierarchical wins, flat & domain lose** — utterances that are not commands
  but contain a bare keyword for a single-slot intent. Flat and domain fire on
  the lone word; the classifier routes them to a two-slot domain where the
  missing second keyword means nothing fires.

## Results

Single run, all engines on the same machine and dataset:

| Engine | Accuracy | Precision | Recall | F1 | TN/NM | FP | FN | Median lat |
|---|---|---|---|---|---|---|---|---|
| flat         | 87.2% | 84.3% | 96.4% | 0.899 | 36/56 | 25 |  5 | 0.21 ms |
| domain       | 88.2% | 85.5% | 97.8% | 0.913 | 36/56 | 23 |  3 | 0.82 ms |
| hierarchical | 90.3% | 93.4% | 91.4% | 0.924 | 49/56 |  9 | 12 | 0.32 ms |

Flat vs domain head-to-head: **6 / 195 different** — all six the two-clause
utterances. Flat resolves the leading clause on 2 of them, domain on all 6.

Hierarchical stage-1 routing: **127 / 139 match cases (91%)** routed to the
correct domain.

## Interpreting the results

**Flat and domain are not equivalent.** They agree on every clean single-intent
utterance — correctly, since dilution cannot reorder an uncontested winner —
but diverge on the two-clause cases. There, flat scores both clauses inside one
clique whose tag count dilutes them equally, and the tie falls to the
higher-coverage (usually later, longer) clause. Domain scores each clause in
its own sub-engine, where the leading clause's intent stands alone and is
diluted less. Domain resolves the labelled (leading) intent on all 6; flat on
2. Domain ends 1 point ahead overall (88.2% vs 87.2%) with fewer false
positives and false negatives.

**Hierarchical trades recall for precision, and here comes out ahead.** Its
stage-1 gate cuts false positives from ~24 to 9 (true negatives 36 → 49): a
no-match utterance carrying a bare `stop` / `cancel` is routed to a two-slot
domain where nothing fires, so no intent is emitted. That lifts precision to
93.4%. The cost is recall: 12 false negatives, because a real command that the
classifier misroutes — a one-word command, or one carrying a long room word
that outweighs the intent keyword — is unrecoverable. On this dataset the
precision gain outweighs the recall loss and hierarchical leads at 90.3%, but
that balance depends entirely on how command-like the no-match traffic is.

**Routing must be reliable for two-stage to pay off.** Stage 1 routes 91% of
match cases correctly. Every one of the 9% misroutes is an unrecoverable error.
Two-stage is only viable when domain vocabularies are distinctive enough to
classify; the discriminating section deliberately includes utterances where
they are not, and hierarchical loses exactly those.

**Latency.** Flat is fastest (~0.2 ms). Hierarchical (~0.3 ms) runs a cheap
classifier plus one sub-engine. The parallel domain engine (~0.8 ms) evaluates
every sub-engine per query. All are far below any perceptible threshold.

## How to run

```bash
python benchmark/compare.py
```

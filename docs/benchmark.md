# Engine comparison reference

> **This is not a benchmark.** `benchmark/dataset.py` is a small, hand-tuned
> reference corpus built to *expose behavioural differences* between the three
> Adapt engine topologies. It is not a representative sample of real traffic,
> and the headline accuracy numbers below are an artifact of how the dataset is
> composed — see [Reading the numbers](#reading-the-numbers). Use it to
> understand *how* the topologies diverge and *why*, not to rank them.

`benchmark/compare.py` runs three Adapt engine topologies on one shared
keyword dataset:

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
no competitor for dilution to reorder. They diverge only on utterances that
carry more than one intent's keywords, or that the stage-1 router misroutes.

## Dataset

`benchmark/dataset.py` defines the vocabulary, intents, domain grouping, and
labelled utterances:

```text
Cases   : 195  (139 match, 56 no-match)
Intents : 26   across 11 domains
```

Intents are mostly **two-slot** — a shared ACTION keyword plus a
domain-distinctive OBJECT keyword. Beyond the everyday cases, the dataset
carries three hand-crafted discriminating sections, each *deliberately
constructed* to give one topology an edge:

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

## Reading the numbers

**The accuracy ordering is something this dataset was built to produce, not a
property of the engines.** The three discriminating sections each move the
result a fixed amount, so the headline ranking is whatever their proportions
make it. The dataset can be tuned to crown any engine:

- **To make hierarchical win** — add more bare-keyword non-commands
  (`"they cancel each other out"`). Each is a false positive flat and domain
  emit and hierarchical's gate suppresses. The current dataset has ten; doubling
  them widens hierarchical's lead.
- **To make hierarchical lose** — add more routing-hard commands: one-word
  utterances, or commands carrying a long off-domain word that outweighs the
  intent keyword in the stage-1 classifier. Each is an unrecoverable misroute,
  a false negative only hierarchical suffers.
- **To separate flat from domain** — add more two-clause utterances. Domain
  resolves the leading clause more often, so each case widens domain's margin.
  Remove them and flat and domain are once again indistinguishable.
- **To erase all differences** — keep only clean single-intent commands with
  distinctive per-domain vocabulary. Dilution cannot reorder an uncontested
  winner, so all three topologies score identically. An earlier revision of
  this dataset did exactly that and reported flat ≡ domain ≡ hierarchical.

The same freedom applies to the vocabulary: sharing a keyword across domains
(`temperature` here is both a weather and a climate word) manufactures
cross-domain competition; keeping every object word domain-unique removes it.
Optional slots, keyword lengths, and how intents are grouped into domains all
shift the confidence arithmetic.

So treat the table as a description of *behaviour* — flat dilutes most, domain
dilutes less, hierarchical gates false positives at the cost of misroutes — not
as a measurement of accuracy. A real accuracy figure requires a corpus sampled
from production traffic, with the section mix reflecting how often each
situation actually occurs. This dataset makes no such claim.

## Interpreting the divergences

**Flat and domain are not equivalent.** They agree on every clean single-intent
utterance — correctly, since dilution cannot reorder an uncontested winner —
but diverge on the two-clause cases. There, flat scores both clauses inside one
clique whose tag count dilutes them equally, and the tie falls to the
higher-coverage clause. Domain scores each clause in its own sub-engine, where
the leading clause's intent stands alone and is diluted less.

**Hierarchical trades recall for precision.** Its stage-1 gate suppresses false
positives (a no-match utterance carrying a bare `stop` / `cancel` is routed to
a two-slot domain where nothing fires) but cannot recover a real command the
classifier misroutes. Whether that trade is net positive depends entirely on
how command-like the no-match traffic is — i.e. on the dataset.

**Routing must be reliable for two-stage to pay off.** Every stage-1 misroute
is an unrecoverable error. Two-stage is only viable when domain vocabularies
are distinctive enough to classify.

**Latency.** Flat is fastest (~0.2 ms). Hierarchical (~0.3 ms) runs a cheap
classifier plus one sub-engine. The parallel domain engine (~0.8 ms) evaluates
every sub-engine per query. All are far below any perceptible threshold.

## How to run

```bash
python benchmark/compare.py
```

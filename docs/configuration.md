# Configuration

## Entry point

The plugin is published under the OPM `opm.pipeline` entry point:

```toml
[project.entry-points."opm.pipeline"]
"ovos-adapt-pipeline-plugin" = "ovos_adapt.opm:AdaptPipeline"
```

OVOS discovers it by that id — `ovos-adapt-pipeline-plugin`.

## Enabling it in the pipeline

`mycroft.conf`, under `intents.pipeline`, lists the matcher stages in priority
order. Each Adapt stage is referenced by id plus a confidence-tier suffix:

```json
{
  "intents": {
    "pipeline": [
      "ovos-adapt-pipeline-plugin-high",
      "ovos-padatious-pipeline-plugin-high",
      "ovos-adapt-pipeline-plugin-medium",
      "ovos-adapt-pipeline-plugin-low"
    ]
  }
}
```

A stage earlier in the list wins ties. A common layout runs every matcher's
**high** tier first, then medium, then low, so a confident match from any
matcher beats a shaky match from the one listed first.

## Confidence tiers

The plugin exposes three matchers, one per tier. Each returns a match only when
its confidence clears the tier threshold:

| Tier | Method | Default threshold | Config key |
|---|---|---|---|
| high | `match_high` | 0.65 | `conf_high` |
| medium | `match_medium` | 0.45 | `conf_med` |
| low | `match_low` | 0.25 | `conf_low` |

The same utterance is scored once; the tier only decides which threshold the
score must clear. Lower a threshold to let weaker matches through that tier;
raise it to demand a stronger match.

## Settings

| Key | Default | Effect |
|---|---|---|
| `conf_high` | `0.65` | minimum confidence for a `match_high` result |
| `conf_med` | `0.45` | minimum confidence for a `match_medium` result |
| `conf_low` | `0.25` | minimum confidence for a `match_low` result |
| `max_words` | `50` | utterances longer than this are skipped unmatched |

Keep the thresholds ordered `conf_low <= conf_med <= conf_high`; an inverted
order makes a tier unreachable.

`max_words` is a guard: very long utterances are rarely commands and are
expensive to expand into cliques, so they are dropped before matching.

## Tuning

- **Too many false matches** (the assistant acts on off-hand remarks) — raise
  `conf_high`, or give the over-eager intents more `require`d slots so they
  demand a fuller command. See [Concepts](concepts.md).
- **Real commands missed** — check the utterance actually contains a registered
  surface form for every required slot; confidence cannot rescue a missing
  `require`. Lowering `conf_low` only helps if the intent scored *something*.
- **Confidence feels low on correct matches** — short keywords in long
  sentences score low by design (little of the utterance is covered). Register
  longer, more specific surface forms, or add `optionally` slots that cover
  more words.

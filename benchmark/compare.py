"""
Comparative accuracy + speed benchmark: flat Adapt vs domain Adapt.

Both runners use the same keyword vocabulary and intent definitions. The
only difference is engine topology:

- **flat**   — one :class:`IntentDeterminationEngine`; every intent parser
  and every entity share a single Trie and tagger.
- **domain** — one :class:`DomainIntentDeterminationEngine`; intents are
  grouped into domains, each domain owning an isolated sub-engine (its own
  Trie + tagger). At match time every domain is scored and the global
  argmax wins.

Usage
-----
    python benchmark/compare.py
"""
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.dataset import (  # noqa: E402
    VOCAB, INTENTS, DOMAINS, TEST_CASES, NO_MATCH_UTTERANCES,
)
from ovos_adapt.engine import (  # noqa: E402
    IntentDeterminationEngine, DomainIntentDeterminationEngine,
)
from ovos_adapt.intent import IntentBuilder  # noqa: E402


# ── shared helpers ─────────────────────────────────────────────────────────

def all_cases():
    return list(TEST_CASES) + [(u, None) for u in NO_MATCH_UTTERANCES]


def _build_parser(intent_name):
    slots = INTENTS[intent_name]
    builder = IntentBuilder(intent_name)
    for slot in slots["required"]:
        builder.require(slot)
    for slot in slots["optional"]:
        builder.optionally(slot)
    return builder.build()


def _entity_types(intent_names):
    etypes = set()
    for name in intent_names:
        etypes.update(INTENTS[name]["required"])
        etypes.update(INTENTS[name]["optional"])
    return etypes


#: intent_name -> its domain
INTENT_DOMAIN = {i: d for d, names in DOMAINS.items() for i in names}


def _best_name(intents):
    """Global argmax intent label over a list of Adapt parse dicts."""
    if not intents:
        return None, 0.0
    best = max(intents, key=lambda x: x.get("confidence", 0.0))
    conf = best.get("confidence", 0.0)
    return (best.get("intent_type") if conf > 0 else None), conf


def compute_metrics(results, cases):
    total = len(cases)
    match_n = sum(1 for _, e in cases if e is not None)
    nomatch_n = total - match_n
    tp = fp = fn = tn = 0
    per_tp = defaultdict(int)
    per_fn = defaultdict(int)
    per_fp = defaultdict(int)
    wrong = []
    for (predicted, conf), (utt, expected) in zip(results, cases):
        if expected is not None:
            if predicted == expected:
                tp += 1
                per_tp[expected] += 1
            else:
                fn += 1
                per_fn[expected] += 1
                if predicted is not None:
                    fp += 1
                    per_fp[predicted] += 1
                wrong.append((utt, expected, predicted, conf))
        else:
            if predicted is not None:
                fp += 1
                per_fp[predicted] += 1
                wrong.append((utt, expected, predicted, conf))
            else:
                tn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / match_n if match_n else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return dict(
        accuracy=(tp + tn) / total, precision=prec, recall=rec, f1=f1,
        tp=tp, fp=fp, fn=fn, tn=tn,
        match_n=match_n, nomatch_n=nomatch_n,
        per_tp=per_tp, per_fn=per_fn, per_fp=per_fp, wrong=wrong,
    )


def print_report(label, m, latencies):
    s = sorted(latencies)
    total = m["match_n"] + m["nomatch_n"]
    print(f"\n{'=' * 66}")
    print(f"  {label}")
    print(f"{'=' * 66}")
    print(f"  Accuracy  : {m['accuracy']:.1%}  ({int(round(m['accuracy'] * total))}/{total})")
    print(f"  Precision : {m['precision']:.1%}")
    print(f"  Recall    : {m['recall']:.1%}")
    print(f"  F1        : {m['f1']:.3f}")
    print(f"  TN        : {m['tn']} / {m['nomatch_n']}  ({m['tn'] / m['nomatch_n']:.0%} of no-match)")
    print(f"  FP        : {m['fp']} / {m['nomatch_n']}  ({m['fp'] / m['nomatch_n']:.0%} of no-match)")
    print(f"  FN        : {m['fn']} / {m['match_n']}  ({m['fn'] / m['match_n']:.0%} of match)")
    print(f"  Latency   : median={statistics.median(latencies):.2f}ms  "
          f"p95={s[int(len(s) * .95)]:.2f}ms  max={s[-1]:.2f}ms")
    if m["wrong"]:
        print(f"\n  Mismatches ({len(m['wrong'])}):")
        for utt, exp, pred, conf in m["wrong"]:
            print(f"    [{exp or '—'} → {pred or '—'}] ({conf:.2f})  \"{utt}\"")


# ── engine runners ─────────────────────────────────────────────────────────

def run_flat(cases):
    engine = IntentDeterminationEngine()
    for entity_type, values in VOCAB.items():
        for value in values:
            engine.register_entity(value, entity_type)
    for intent_name in INTENTS:
        engine.register_intent_parser(_build_parser(intent_name))

    results, latencies = [], []
    for utt, _ in cases:
        t0 = time.perf_counter()
        intents = list(engine.determine_intent(utt, 100))
        latencies.append((time.perf_counter() - t0) * 1000)
        results.append(_best_name(intents))

    m = compute_metrics(results, cases)
    print_report("flat  —  IntentDeterminationEngine", m, latencies)
    return m, statistics.median(latencies), results


def run_domain(cases):
    engine = DomainIntentDeterminationEngine()
    for domain, intent_names in DOMAINS.items():
        for etype in _entity_types(intent_names):
            for value in VOCAB.get(etype, []):
                engine.register_entity(value, etype, domain=domain)
        for intent_name in intent_names:
            engine.register_intent_parser(_build_parser(intent_name),
                                          domain=domain)

    results, latencies = [], []
    for utt, _ in cases:
        t0 = time.perf_counter()
        intents = list(engine.determine_intent(utt, 100))
        latencies.append((time.perf_counter() - t0) * 1000)
        results.append(_best_name(intents))

    m = compute_metrics(results, cases)
    print_report("domain  —  DomainIntentDeterminationEngine", m, latencies)
    return m, statistics.median(latencies), results


# ── summary table ──────────────────────────────────────────────────────────

def run_hierarchical(cases):
    """Two-stage routing: classify the domain, then resolve within it.

    Stage 1 is a domain classifier — a flat engine whose 'intents' are
    domains, each requiring a pooled keyword entity covering every word
    used by that domain's intents. Stage 2 runs only the winning domain's
    sub-engine. A wrong stage-1 route cannot be recovered.
    """
    sub = {}
    for domain, intent_names in DOMAINS.items():
        engine = IntentDeterminationEngine()
        for etype in _entity_types(intent_names):
            for value in VOCAB.get(etype, []):
                engine.register_entity(value, etype)
        for intent_name in intent_names:
            engine.register_intent_parser(_build_parser(intent_name))
        sub[domain] = engine

    classifier = IntentDeterminationEngine()
    for domain, intent_names in DOMAINS.items():
        pooled = set()
        for etype in _entity_types(intent_names):
            pooled.update(VOCAB.get(etype, []))
        for value in pooled:
            classifier.register_entity(value, f"{domain}_kw")
        classifier.register_intent_parser(
            IntentBuilder(domain).require(f"{domain}_kw").build())

    results, latencies = [], []
    routed_ok = routed_total = 0
    for utt, expected in cases:
        t0 = time.perf_counter()
        domain, _ = _best_name(list(classifier.determine_intent(utt, 100)))
        if domain in sub:
            name, conf = _best_name(list(sub[domain].determine_intent(utt, 100)))
        else:
            name, conf = None, 0.0
        latencies.append((time.perf_counter() - t0) * 1000)
        results.append((name, conf))
        if expected is not None:
            routed_total += 1
            if domain == INTENT_DOMAIN.get(expected):
                routed_ok += 1

    m = compute_metrics(results, cases)
    print_report("hierarchical  —  two-stage (classify domain, then intent)",
                 m, latencies)
    print(f"  Stage-1 routing : {routed_ok}/{routed_total} match cases "
          f"routed to the correct domain ({routed_ok / routed_total:.0%})")
    return m, statistics.median(latencies), results


def head_to_head(cases, flat_results, domain_results):
    """Report the cases where flat and domain predict a different intent."""
    diffs = []
    for (utt, expected), (fn, fc), (dn, dc) in zip(cases, flat_results,
                                                   domain_results):
        if fn != dn:
            diffs.append((utt, expected, fn, fc, dn, dc))
    print(f"\n\n{'=' * 66}")
    print("  Head-to-head: flat vs domain")
    print(f"{'=' * 66}")
    print(f"  Cases             : {len(cases)}")
    print(f"  Same prediction   : {len(cases) - len(diffs)}")
    print(f"  Different          : {len(diffs)}")
    if diffs:
        print(f"\n  {'utterance':<44} {'expected':<16} {'flat':<16} {'domain':<16}")
        print(f"  {'-' * 90}")
        for utt, exp, fn, fc, dn, dc in diffs:
            u = utt if len(utt) <= 42 else utt[:41] + "…"
            print(f"  {u:<44} {exp or '—':<16} "
                  f"{(fn or '—') + f' {fc:.2f}':<16} "
                  f"{(dn or '—') + f' {dc:.2f}':<16}")
    return len(diffs)


def summary(rows):
    print(f"\n\n{'─' * 84}")
    print(f"  {'Engine':<14} {'Acc':>6} {'Prec':>6} {'Recall':>7} {'F1':>6}  "
          f"{'TN/NM':>8}  {'FP':>4}  {'FN':>4}  {'Median':>8}")
    print(f"{'─' * 84}")
    for label, m, median_lat in rows:
        tn_frac = f"{m['tn']}/{m['nomatch_n']}"
        print(f"  {label:<14} {m['accuracy']:>5.1%} {m['precision']:>5.1%} "
              f"{m['recall']:>6.1%} {m['f1']:>5.3f}  {tn_frac:>8}  "
              f"{m['fp']:>4}  {m['fn']:>4}  {median_lat:>6.2f}ms")
    print(f"{'─' * 84}")
    print("  TN/NM = true negatives / total no-match cases (correctly returned nothing)")


# ── main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cases = all_cases()
    match_n = sum(1 for _, e in cases if e is not None)
    print(f"\nDataset : {len(cases)} cases  ({match_n} match, {len(cases) - match_n} no-match)")
    print(f"Intents : {len(INTENTS)}  across {len(DOMAINS)} domains")
    print(f"Vocab   : {sum(len(v) for v in VOCAB.values())} keyword samples "
          f"across {len(VOCAB)} entity types")

    rows = []
    m, lat, flat_results = run_flat(cases)
    rows.append(("flat", m, lat))
    m, lat, domain_results = run_domain(cases)
    rows.append(("domain", m, lat))
    m, lat, _ = run_hierarchical(cases)
    rows.append(("hierarchical", m, lat))
    head_to_head(cases, flat_results, domain_results)
    summary(rows)

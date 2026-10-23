"""Summaries and the registered decision rules (PLAN.md), computed from the saved call files.

    python3 analyze.py claude-haiku-5-5
Accuracy is whole run accuracy against the hidden rule. Unreadable replies count as wrong.
Intervals are 95 percent bootstrap intervals, resampling test orders (experiment 1) or runs (experiment 2).
"""
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import route_env as E

model = sys.argv[1]
D = Path(__file__).resolve().parent / "results" / "full" / model
rng = random.Random(0)


def load(name):
    p = D / name
    return [json.loads(l) for l in open(p)] if p.exists() else []


def boot(vals, fn=st.mean, n=4000):
    vals = list(vals)
    out = sorted(fn([vals[rng.randrange(len(vals))] for _ in vals]) for _ in range(n))
    return out[int(0.025 * n)], out[int(0.975 * n)]


def fmt(m, ci):
    return f"{100*m:5.1f} [{100*ci[0]:5.1f}, {100*ci[1]:5.1f}]"


e1 = [r for n in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["exp1.jsonl"]) for r in load(n)]
e2 = load("exp2.jsonl") if len(sys.argv) <= 2 else []
SEEDS = sorted({r["seed"] for r in e1})
res = {"model": model}
if e1:
    print(f"\nEXPERIMENT 1  seeds {SEEDS}  ({len(e1)} calls)  accuracy points, 95 percent interval")
    print("cond          " + "".join(f"{'k='+str(k):>24}" for k in sorted({r['k'] for r in e1})))
    by = defaultdict(list)
    for r in e1:
        by[(r["cond"], r["k"])].append(r)
    for c in E.EXP1_CONDITIONS:
        line = f"{c:13s} "
        for k in sorted({r["k"] for r in e1}):
            rs = by.get((c, k)) or (by.get((E.NONE, 0)) if k == 0 and c == E.NONE else None)
            if not rs:
                line += f"{'':>24}"
                continue
            v = [r["correct"] for r in rs]
            line += f"{fmt(st.mean(v), boot(v)):>24}"
        print(line)
    ceil = {k: st.mean(E.oracle_accuracy(E.build_memory(s, k, E.TRUE) if k else [], E.make_rule(s), E.test_orders(s, 60)) for s in SEEDS) for k in sorted({r['k'] for r in e1})}
    print("ceiling (perfect label reader, true labels): " + "  ".join(f"k={k}: {100*v:.1f}" for k, v in ceil.items()))
    print("\nlabel following rate (answer is a route labeled 1 for its region; only where such a route exists)")
    for c in (E.TRUE, E.FLIPPED, E.RANDOM):
        for k in sorted({r["k"] for r in e1} - {0}):
            v = [int(r["follows"]) for r in by.get((c, k), []) if r["follows"] is not None]
            if v:
                print(f"  {c:8s} k={k:2d}  {fmt(st.mean(v), boot(v))}  (n={len(v)})")
    print("\nunreadable replies:", sum(r["ans"] is None for r in e1), "of", len(e1))
    # P1 / P2: true minus flipped at k = 8, paired by (seed, order)
    for k in sorted({r["k"] for r in e1} - {0}):
        t = {(r["seed"], r["i"]): r["correct"] for r in by.get((E.TRUE, k), [])}
        f = {(r["seed"], r["i"]): r["correct"] for r in by.get((E.FLIPPED, k), [])}
        keys = sorted(set(t) & set(f))
        if keys:
            d = [t[x] - f[x] for x in keys]
            ci = boot(d)
            verdict = "P1 (labels are used)" if (st.mean(d) >= 0.15 and ci[0] > 0) else \
                      "P2 (labels not used)" if (abs(st.mean(d)) < 0.05 and ci[0] <= 0 <= ci[1]) else "P3 (partial)"
            print(f"true minus flipped, k={k}: {fmt(st.mean(d), ci)} points  ->  {verdict}")
            res[f"d_true_flipped_k{k}"] = st.mean(d)
    # P4: success only versus true
    k = 8
    so = [r["correct"] for r in by.get((E.SUCCESS_ONLY, k), [])]
    tr = [r["correct"] for r in by.get((E.TRUE, k), [])]
    if so and tr:
        print(f"P4 check, k=8: success only {100*st.mean(so):.1f} vs true labels {100*st.mean(tr):.1f}")

if e2:
    print(f"\nEXPERIMENT 2  ({len(e2)} calls)  accuracy points by block of 6 trials, 95 percent interval over runs")
    runs = defaultdict(lambda: defaultdict(dict))
    for r in e2:
        runs[r["cond"]][r["seed"]][r["t"]] = r["correct"]
    print("cond        " + "".join(f"{'trials '+str(a+1)+'-'+str(a+6):>24}" for a in (0, 6, 12, 18)))
    last = {}
    for c in E.EXP2_CONDITIONS:
        sd = {s: v for s, v in runs[c].items() if len(v) == 24}
        line = f"{c:11s} "
        for a in (0, 6, 12, 18):
            per = [st.mean(v[t] for t in range(a, a + 6)) for v in sd.values()]
            line += f"{fmt(st.mean(per), boot(per)):>24}"
            if a == 18:
                last[c] = {s: st.mean(v[t] for t in range(18, 24)) for s, v in sd.items()}
        print(line + f"   runs {len(sd)}")
    ok = set(last.get(E.TRUE, {})) & set(last.get(E.FLIPPED, {}))
    if ok:
        d = [last[E.TRUE][s] - last[E.FLIPPED][s] for s in sorted(ok)]
        print(f"true minus flipped, last block, paired by hidden rule: {fmt(st.mean(d), boot(d))} points")
        res["e2_last_true_minus_flipped"] = st.mean(d)
    print("unreadable replies:", sum(r["ans"] is None for r in e2), "of", len(e2))

allr = e1 + e2
if allr:
    usd = sum(r["usd"] for r in allr)
    print(f"\ncalls {len(allr)}  input tokens {sum(r['in'] for r in allr)}  output tokens {sum(r['out'] for r in allr)}  recorded spend ${usd:.4f}")

"""Pilot. Haiku only, pilot seeds 1 and 2 (not among the registered seeds 11 to 13 and 101 to 130).

    ../../agentic-rag-eval/.venv/bin/python run_pilot.py

Part A (experiment 1 style): k = 0 and k = 8, conditions true, flipped, none, 20 test orders.
Part B (experiment 2 style): 2 online runs of 24 trials each, conditions true and flipped.
Writes results/pilot/*.jsonl and prints a summary. Spend cap 0.50 US dollars.
"""
import json
import statistics as st
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import route_env as E
from clients import BudgetExceeded, Chooser, Ledger

OUT = Path(__file__).resolve().parent / "results" / "pilot"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = "claude-haiku-5-5"
LEDGER = Ledger(cap_usd=0.50)
CH = Chooser(MODEL, LEDGER)


def part_a():
    seed, n_test = 1, 20
    rule = E.make_rule(seed)
    orders = E.test_orders(seed, n_test)
    jobs = []
    for k, conds in ((0, [E.NONE]), (8, [E.TRUE, E.FLIPPED, E.NONE])):
        for c in conds:
            mem = E.build_memory(seed, k, c) if k else []
            for i, o in enumerate(orders):
                jobs.append((k, c, i, o, mem))

    def one(j):
        k, c, i, o, mem = j
        text, rec = CH.choose(E.system_for(c), E.user_prompt(mem, o))
        ans = E.parse_route(text)
        return {"part": "A", "model": MODEL, "seed": seed, "k": k, "cond": c, "i": i, "region": o.region,
                "gold": rule[o.region], "raw": text, "ans": ans, "correct": int(ans == rule[o.region]),
                "follows": E.follows_label(mem, o, ans), **rec}

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, jobs))
    with open(OUT / "part_a.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def part_b():
    jobs = [(s, c) for s in (1, 2) for c in (E.TRUE, E.FLIPPED)]

    def run(job):
        seed, cond = job
        rule = E.make_rule(seed)
        orders = E.balanced_orders(24, __import__("random").Random(f"online-{seed}"))
        lab_rng = __import__("random").Random(f"onlab-{seed}-{cond}")
        mem, rows = [], []
        for t, o in enumerate(orders):
            text, rec = CH.choose(E.system_for(cond), E.user_prompt(mem, o))
            ans = E.parse_route(text)
            tr = int(ans == rule[o.region])
            label = {E.TRUE: tr, E.FLIPPED: 1 - tr}[cond]
            rows.append({"part": "B", "model": MODEL, "seed": seed, "cond": cond, "t": t, "region": o.region,
                         "gold": rule[o.region], "raw": text, "ans": ans, "correct": tr,
                         "follows": E.follows_label(mem, o, ans), **rec})
            if ans is not None:
                mem.append(E.Entry(o, ans, label))
        return rows

    with ThreadPoolExecutor(4) as ex:
        out = [r for rows in ex.map(run, jobs) for r in rows]
    with open(OUT / "part_b.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    return out


def summarize(a, b):
    print("\nPART A (20 test orders, seed 1)")
    for k, c in ((0, "none"), (8, "true"), (8, "flipped"), (8, "none")):
        rs = [r for r in a if r["k"] == k and r["cond"] == c]
        fl = [r["follows"] for r in rs if r["follows"] is not None]
        print(f"  k={k} {c:8s} accuracy {st.mean(r['correct'] for r in rs):.2f}  unreadable {sum(r['ans'] is None for r in rs)}  "
              f"follows label {('%.2f' % st.mean(fl)) if fl else 'n/a'} (n={len(fl)})")
    print("PART B (online, 24 trials, 2 runs per condition): accuracy by block of 6 trials")
    for c in ("true", "flipped"):
        rs = [r for r in b if r["cond"] == c]
        blocks = [st.mean(r["correct"] for r in rs if t0 <= r["t"] < t0 + 6) for t0 in (0, 6, 12, 18)]
        print(f"  {c:8s} " + "  ".join(f"{x:.2f}" for x in blocks) + f"   unreadable {sum(r['ans'] is None for r in rs)}")
    allr = a + b
    print(f"\ncalls {LEDGER.calls}  input tokens {LEDGER.tin}  output tokens {LEDGER.tout}  spend ${LEDGER.usd:.4f}  "
          f"mean input tokens per call {LEDGER.tin / LEDGER.calls:.0f}")
    print("raw replies seen:", sorted({r['raw'].strip()[:20] for r in allr})[:12])


if __name__ == "__main__":
    try:
        a = part_a()
        b = part_b()
    except BudgetExceeded as e:
        raise SystemExit(f"STOPPED: {e}")
    summarize(a, b)

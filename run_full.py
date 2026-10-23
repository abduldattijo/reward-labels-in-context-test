"""Full run, as registered in PLAN.md. One model per call. Resumes from the saved files if it is stopped.

    ../../agentic-rag-eval/.venv/bin/python run_full.py --model claude-haiku-5-5 --cap 1.0
    (reduced design for a paid frontier model) --ks 8 --exp2-runs 15 --cap 3.0

Experiment 1: seeds 11 to 13, k in --ks, six conditions, 60 test orders each, plus k = 0 once per seed.
Experiment 2: seeds 101 to 100+exp2_runs, four conditions, 24 trials each.
Unreadable replies count as wrong. In experiment 2 an unreadable reply is not added to memory.
"""
import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import route_env as E
from clients import BudgetExceeded, Chooser, Ledger

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--cap", type=float, required=True)
ap.add_argument("--ks", default="4,8,16")
ap.add_argument("--exp2-runs", type=int, default=30)
ap.add_argument("--workers", type=int, default=8)
args = ap.parse_args()
KS = [int(x) for x in args.ks.split(",") if x]
OUT = Path(__file__).resolve().parent / "results" / "full" / args.model
OUT.mkdir(parents=True, exist_ok=True)
LEDGER = Ledger(args.cap)
CH = Chooser(args.model, LEDGER)


def load(path):
    return [json.loads(l) for l in open(path)] if path.exists() else []


def exp1():
    path = OUT / "exp1.jsonl"
    done = {(r["seed"], r["k"], r["cond"], r["i"]) for r in load(path)}
    jobs = []
    for seed in (11, 12, 13):
        orders = E.test_orders(seed, 60)
        for k in [0] + KS:
            for c in ([E.NONE] if k == 0 else E.EXP1_CONDITIONS):
                mem = E.build_memory(seed, k, c) if k else []
                for i, o in enumerate(orders):
                    if (seed, k, c, i) not in done:
                        jobs.append((seed, k, c, i, o, mem))
    print(f"exp1: {len(jobs)} calls to make", flush=True)

    def one(j):
        seed, k, c, i, o, mem = j
        rule = E.make_rule(seed)
        text, rec = CH.choose(E.system_for(c), E.user_prompt(mem, o))
        ans = E.parse_route(text)
        return {"exp": 1, "model": args.model, "seed": seed, "k": k, "cond": c, "i": i, "region": o.region,
                "gold": rule[o.region], "raw": text, "ans": ans, "correct": int(ans == rule[o.region]),
                "follows": E.follows_label(mem, o, ans), **rec}

    with ThreadPoolExecutor(args.workers) as ex, open(path, "a") as f:
        for r in ex.map(one, jobs):
            f.write(json.dumps(r) + "\n")
            f.flush()


def exp2():
    path = OUT / "exp2.jsonl"
    rows_done = load(path)
    done_runs = {(r["seed"], r["cond"]) for r in rows_done if r["t"] == 23}
    jobs = [(101 + n, c) for n in range(args.exp2_runs) for c in E.EXP2_CONDITIONS if (101 + n, c) not in done_runs]
    # drop partial runs from an interrupted earlier attempt, then rerun them whole
    keep = [r for r in rows_done if (r["seed"], r["cond"]) in done_runs]
    with open(path, "w") as f:
        for r in keep:
            f.write(json.dumps(r) + "\n")
    print(f"exp2: {len(jobs)} runs to make", flush=True)

    def run(job):
        seed, cond = job
        rule = E.make_rule(seed)
        orders = E.balanced_orders(24, random.Random(f"online-{seed}"))
        lab = random.Random(f"onlab-{seed}")
        mem, rows = [], []
        for t, o in enumerate(orders):
            text, rec = CH.choose(E.system_for(cond), E.user_prompt(mem, o))
            ans = E.parse_route(text)
            tr = int(ans == rule[o.region])
            draw = lab.random()  # drawn every trial so the random stream does not depend on the answers
            label = {E.TRUE: tr, E.FLIPPED: 1 - tr, E.RANDOM: int(draw < E.RANDOM_LABEL_RATE), E.NONE: None}[cond]
            rows.append({"exp": 2, "model": args.model, "seed": seed, "cond": cond, "t": t, "region": o.region,
                         "gold": rule[o.region], "raw": text, "ans": ans, "correct": tr,
                         "follows": E.follows_label(mem, o, ans), **rec})
            if ans is not None:
                mem.append(E.Entry(o, ans, label))
        return rows

    with ThreadPoolExecutor(args.workers) as ex, open(path, "a") as f:
        for rows in ex.map(run, jobs):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()


if __name__ == "__main__":
    try:
        exp1()
        if args.exp2_runs > 0:
            exp2()
    except BudgetExceeded as e:
        print("STOPPED:", e)
        raise SystemExit(1)
    print(f"done. calls {LEDGER.calls}  input tokens {LEDGER.tin}  output tokens {LEDGER.tout}  spend ${LEDGER.usd:.4f}")
    with open(OUT / "run_cost.jsonl", "a") as f:
        f.write(json.dumps({"calls": LEDGER.calls, "tin": LEDGER.tin, "tout": LEDGER.tout, "usd": round(LEDGER.usd, 6)}) + "\n")

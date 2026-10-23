"""Read-only checks added 2026-10-23 after an outside review of the draft claims. Uses saved replies only.

1. Seed level true minus flipped gaps (each seed has its own hidden rule and memory, so seeds are the independent units).
2. Route reuse: how often the answer is a route already shown in memory for the same region, against the share expected if the
   answer were a uniform random route.
"""
import json, random, statistics as st
from collections import defaultdict
from pathlib import Path
import route_env as E

R = Path("results/full")
def load(m, names):
    return [json.loads(l) for n in names for l in open(R / m / n)]
DATA = {"claude-haiku-5-5": load("claude-haiku-5-5", ["exp1.jsonl"]),
        "gpt-6-sol": load("gpt-6-sol", ["exp1.jsonl"]),
        "qwen3-4b (seeds 11-13)": load("qwen3-4b-instruct-2507", ["exp1.jsonl"]),
        "qwen3-4b (seeds 11-16)": load("qwen3-4b-instruct-2507", ["exp1.jsonl", "exp1_extra.jsonl"])}
rng = random.Random(0)

print("SEED LEVEL true minus flipped (points). Each value is one seed, 60 test orders.")
for name, rows in DATA.items():
    for k in sorted({r["k"] for r in rows} - {0}):
        gaps = []
        for s in sorted({r["seed"] for r in rows}):
            t = [r["correct"] for r in rows if r["seed"] == s and r["k"] == k and r["cond"] == "true"]
            f = [r["correct"] for r in rows if r["seed"] == s and r["k"] == k and r["cond"] == "flipped"]
            if t and f:
                gaps.append(100 * (st.mean(t) - st.mean(f)))
        if not gaps:
            continue
        bs = sorted(st.mean(rng.choices(gaps, k=len(gaps))) for _ in range(5000))
        sd = st.stdev(gaps) if len(gaps) > 1 else 0
        print(f"{name:24s} k={k:2d} mean {st.mean(gaps):6.1f}  seed bootstrap [{bs[125]:6.1f}, {bs[4875]:6.1f}]  "
              f"mean +- 2 se [{st.mean(gaps)-2*sd/len(gaps)**.5:6.1f}, {st.mean(gaps)+2*sd/len(gaps)**.5:6.1f}]  "
              f"all positive: {all(g > 0 for g in gaps)}  values: {[round(g) for g in gaps]}")

print("\nROUTE REUSE. reuse = answer is a route shown in memory for that region. chance = share expected from a uniform random answer.")
print(f"{'model':24s} {'cond':13s} {'k':>3s} {'reuse':>7s} {'chance':>7s} {'answers a route labeled 0':>26s} {'(chance)':>9s}")
for name, rows in DATA.items():
    mem_cache = {}
    for k in sorted({r["k"] for r in rows} - {0}):
        for cond in E.EXP1_CONDITIONS:
            reuse, chance, zero, zero_ch = [], [], [], []
            for r in rows:
                if r["k"] != k or r["cond"] != cond:
                    continue
                key = (r["seed"], k, cond)
                if key not in mem_cache:
                    mem_cache[key] = E.build_memory(r["seed"], k, cond)
                shown = {e.route for e in mem_cache[key] if e.order.region == r["region"]}
                zeros = {e.route for e in mem_cache[key] if e.order.region == r["region"] and e.label == 0}
                if shown:
                    reuse.append(int(r["ans"] in shown)); chance.append(len(shown) / 4)
                if zeros:
                    zero.append(int(r["ans"] in zeros)); zero_ch.append(len(zeros) / 4)
            if reuse:
                z = f"{100*st.mean(zero):5.1f}" if zero else "   n/a"
                zc = f"{100*st.mean(zero_ch):5.1f}" if zero_ch else "  n/a"
                print(f"{name:24s} {cond:13s} {k:3d} {100*st.mean(reuse):6.1f} {100*st.mean(chance):7.1f} {z:>26s} {zc:>9s}")


# ---- second review round: model specific baseline, elimination policy, avoidance by memory type ----
print("\n\nSECOND BASELINE: the model's own saved no-memory answer to the same order, checked against the shown routes")
print(f"{'model':24s} {'cond':13s} {'k':>3s} {'reuse':>7s} {'uniform':>8s} {'own no-memory baseline':>23s}")
for name, rows in DATA.items():
    base = {(r["seed"], r["i"]): r["ans"] for r in rows if r["k"] == 0}
    mem_cache = {}
    for k in sorted({r["k"] for r in rows} - {0}):
        for cond in E.EXP1_CONDITIONS:
            reuse, uni, own = [], [], []
            for r in rows:
                if r["k"] != k or r["cond"] != cond:
                    continue
                key = (r["seed"], k, cond)
                mem_cache.setdefault(key, E.build_memory(r["seed"], k, cond))
                shown = {e.route for e in mem_cache[key] if e.order.region == r["region"]}
                if shown and (r["seed"], r["i"]) in base:
                    reuse.append(int(r["ans"] in shown)); uni.append(len(shown) / 4)
                    own.append(int(base[(r["seed"], r["i"])] in shown))
            if reuse and k in (8,):
                print(f"{name:24s} {cond:13s} {k:3d} {100*st.mean(reuse):7.1f} {100*st.mean(uni):8.1f} {100*st.mean(own):23.1f}")

print("\nELIMINATION POLICY, failures only memory: drop every shown (wrong) route for the region, guess uniformly among the rest")
for name, rows in DATA.items():
    seeds = sorted({r["seed"] for r in rows})
    for k in (4, 8, 16):
        accs = []
        for s in seeds:
            rule = E.make_rule(s); mem = E.build_memory(s, k, E.FAILURE_ONLY)
            for o in E.test_orders(s, 60):
                left = [x for x in E.ROUTES if x not in {e.route for e in mem if e.order.region == o.region}]
                accs.append(1 / len(left) if rule[o.region] in left else 0)
        got = [r["correct"] for r in rows if r["cond"] == "failure_only" and r["k"] == k]
        if got:
            print(f"{name:24s} k={k:2d} policy {100*st.mean(accs):5.1f}   model {100*st.mean(got):5.1f}")

print("\nAVOIDING ROUTES LABELED 0: failures only memory against mixed memory (true labels). Share of answers that are a route labeled 0, against the uniform share")
for name, rows in DATA.items():
    mem_cache = {}
    for k in (4, 8, 16):
        line = f"{name:24s} k={k:2d}"
        for cond in (E.FAILURE_ONLY, E.TRUE):
            z, zc = [], []
            for r in rows:
                if r["k"] != k or r["cond"] != cond:
                    continue
                key = (r["seed"], k, cond); mem_cache.setdefault(key, E.build_memory(r["seed"], k, cond))
                zeros = {e.route for e in mem_cache[key] if e.order.region == r["region"] and e.label == 0}
                if zeros:
                    z.append(int(r["ans"] in zeros)); zc.append(len(zeros) / 4)
            if z:
                line += f"   {cond:12s} {100*st.mean(z):5.1f} vs {100*st.mean(zc):5.1f} uniform (n={len(z)})"
        print(line)

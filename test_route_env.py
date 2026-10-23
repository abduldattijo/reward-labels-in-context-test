"""Unit checks for route_env. Run: python3 test_route_env.py. Nothing here calls a model."""
import random
import statistics as st

import route_env as E


def check(cond, msg):
    assert cond, msg
    print("ok  ", msg)


# rule is a permutation and changes with the seed
rules = [E.make_rule(s) for s in range(40)]
check(all(sorted(r.values()) == sorted(E.ROUTES) for r in rules), "rule is a permutation of the four routes")
check(len({tuple(r.items()) for r in rules}) > 10, "rule varies across seeds")
check(E.make_rule(11) == E.make_rule(11), "rule is repeatable from the seed")

# memory pairing, labels, coverage
for seed in (11, 12, 13):
    rule = E.make_rule(seed)
    for k in (4, 8, 16):
        t = E.build_memory(seed, k, E.TRUE)
        f = E.build_memory(seed, k, E.FLIPPED)
        n = E.build_memory(seed, k, E.NONE)
        r = E.build_memory(seed, k, E.RANDOM)
        check(len(t) == k, f"seed {seed} k {k} memory length")
        check([(e.order, e.route) for e in t] == [(e.order, e.route) for e in f] == [(e.order, e.route) for e in n]
              == [(e.order, e.route) for e in r], f"seed {seed} k {k} conditions share orders and routes")
        check(all(a.label == 1 - b.label for a, b in zip(t, f)), f"seed {seed} k {k} flipped labels are the opposite")
        check(all(e.label is None for e in n), f"seed {seed} k {k} none has no labels")
        check(all(e.label == E.true_reward(rule, e.order, e.route) for e in t), f"seed {seed} k {k} true labels match the rule")
        regions = [e.order.region for e in t]
        check(all(regions.count(x) == k // 4 for x in E.REGIONS), f"seed {seed} k {k} regions are balanced")
        so = E.build_memory(seed, k, E.SUCCESS_ONLY)
        check(all(e.route == rule[e.order.region] and e.label is None for e in so), f"seed {seed} k {k} success only shows correct routes, no labels")
        fo = E.build_memory(seed, k, E.FAILURE_ONLY)
        check(all(e.route != rule[e.order.region] and e.label == 0 for e in fo), f"seed {seed} k {k} failure only shows wrong routes labeled 0")

# random label rate close to 0.25 over many seeds, and independent of correctness
labs, corr = [], []
for s in range(200, 400):
    rule = E.make_rule(s)
    for e, t in zip(E.build_memory(s, 16, E.RANDOM), E.build_memory(s, 16, E.TRUE)):
        labs.append(e.label)
        corr.append(t.label)
check(abs(st.mean(labs) - 0.25) < 0.03, f"random label rate is about 0.25 (got {st.mean(labs):.3f})")
agree = st.mean(int(a == b) for a, b in zip(labs, corr))
check(abs(agree - (0.25 * 0.25 + 0.75 * 0.75)) < 0.04, f"random labels are independent of correctness (agreement {agree:.3f})")

# rule is not recoverable without labels: a reader who sees only orders and random routes does no better than chance
rng = random.Random(0)
hits = []
for s in range(300):
    rule = E.make_rule(s)
    mem = E.build_memory(s, 16, E.NONE)
    for o in E.test_orders(s, 20):
        seen = [e.route for e in mem if e.order.region == o.region]
        guess = max(set(seen), key=seen.count) if seen else rng.choice(E.ROUTES)
        hits.append(int(guess == rule[o.region]))
check(abs(st.mean(hits) - 0.25) < 0.03, f"random routes without labels carry no information (accuracy {st.mean(hits):.3f})")

# ceiling accuracy by k for a perfect label reader, and for a label follower under flipped labels
print("ceiling table (mean over 300 seeds), true labels, perfect reader:")
ceil = {}
for k in (0, 4, 8, 16):
    vals = []
    for s in range(300):
        rule = E.make_rule(s)
        vals.append(E.oracle_accuracy(E.build_memory(s, k, E.TRUE) if k else [], rule, E.test_orders(s, 40)))
    ceil[k] = st.mean(vals)
    print(f"  k={k:>2} ceiling {ceil[k]:.3f}")
check(abs(ceil[0] - 0.25) < 0.02, "k = 0 ceiling is chance")
check(ceil[4] < ceil[8] < ceil[16], "ceiling rises with k")
fl = []
for s in range(300):
    rule = E.make_rule(s)
    mem = E.build_memory(s, 8, E.FLIPPED)
    for o in E.test_orders(s, 40):
        chosen = E.label_choice_set(mem, o.region)
        if chosen:
            fl.append(int(rule[o.region] in chosen) / len(chosen))
print(f"  label follower under flipped labels, k=8, accuracy where a label exists: {st.mean(fl):.3f}")
check(st.mean(fl) < 0.05, "following flipped labels gives near zero accuracy where labels exist")

# parsing and prompts
check(E.parse_route("Plum") == "Plum", "parse plain answer")
check(E.parse_route("Route: fig.") == "Fig", "parse with punctuation and case")
check(E.parse_route("Kiwi or Plum") is None, "two routes is unreadable")
check(E.parse_route("I cannot tell") is None, "no route is unreadable")
m = E.build_memory(11, 4, E.TRUE)
u = E.user_prompt(m, E.test_orders(11, 4)[0])
check("Reward:" in u and u.rstrip().endswith("Route:"), "labeled prompt shows rewards and ends with Route:")
check("Reward" not in E.user_prompt(E.build_memory(11, 4, E.NONE), E.test_orders(11, 4)[0]), "unlabeled prompt shows no rewards")
check(E.system_for(E.NONE) == E.SYSTEM_UNLABELED and E.system_for(E.FLIPPED) == E.SYSTEM_LABELED, "system prompt matches condition")
print("all checks passed")

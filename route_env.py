"""The Route task. Pure Python, no model calls. Everything is drawn from a seed.

An order has a region, a size, a color and a product code. Four routes exist. Only the region decides
the correct route, through a hidden random permutation. Reward is 1 for the correct route and 0 for a
wrong one. Memory entries are (order, route, label) triples. Conditions change only the labels, or
(for the two demonstration conditions) which entries are shown.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

REGIONS = ["Kelva", "Orrin", "Tavish", "Mundo"]
ROUTES = ["Kiwi", "Plum", "Fig", "Lime"]
SIZES = ["S", "M", "L", "XL"]
COLORS = ["teal", "amber", "gray", "violet", "olive", "coral"]

# label conditions for experiment 1 (the first four also run in experiment 2)
TRUE, FLIPPED, RANDOM, NONE, SUCCESS_ONLY, FAILURE_ONLY = (
    "true", "flipped", "random", "none", "success_only", "failure_only")
EXP1_CONDITIONS = [TRUE, FLIPPED, RANDOM, NONE, SUCCESS_ONLY, FAILURE_ONLY]
EXP2_CONDITIONS = [TRUE, FLIPPED, RANDOM, NONE]
LABELED = {TRUE, FLIPPED, RANDOM, FAILURE_ONLY}
RANDOM_LABEL_RATE = 0.25  # share of 1s in random labels. Equals the share of 1s in a random-action memory.


@dataclass(frozen=True)
class Order:
    region: str
    size: str
    color: str
    code: int


@dataclass(frozen=True)
class Entry:
    order: Order
    route: str
    label: int | None  # None means no label is shown


def make_rule(seed: int) -> dict[str, str]:
    """Hidden region to route map, a permutation drawn from the seed."""
    rng = random.Random(f"rule-{seed}")
    routes = ROUTES[:]
    rng.shuffle(routes)
    return dict(zip(REGIONS, routes))


def _order(rng: random.Random, region: str) -> Order:
    return Order(region, rng.choice(SIZES), rng.choice(COLORS), rng.randint(1000, 9999))


def balanced_orders(n: int, rng: random.Random) -> list[Order]:
    """n orders with regions as equal as possible (n a multiple of 4 gives exact balance), in random order."""
    regions = [REGIONS[i % 4] for i in range(n)]
    rng.shuffle(regions)
    return [_order(rng, r) for r in regions]


def true_reward(rule: dict[str, str], order: Order, route: str) -> int:
    return int(rule[order.region] == route)


def build_memory(seed: int, k: int, condition: str) -> list[Entry]:
    """Experiment 1 memory. The same orders and random routes serve conditions true, flipped, random, none.
    success_only and failure_only keep the same orders but choose the route to match the condition."""
    rule = make_rule(seed)
    rng = random.Random(f"mem-{seed}-{k}")
    orders = balanced_orders(k, rng)
    routes = [rng.choice(ROUTES) for _ in orders]            # drawn once, so conditions are paired
    lab_rng = random.Random(f"lab-{seed}-{k}")
    wrong_pick = random.Random(f"wrong-{seed}-{k}")
    out = []
    for o, r in zip(orders, routes):
        t = true_reward(rule, o, r)
        if condition == TRUE:
            out.append(Entry(o, r, t))
        elif condition == FLIPPED:
            out.append(Entry(o, r, 1 - t))
        elif condition == RANDOM:
            out.append(Entry(o, r, int(lab_rng.random() < RANDOM_LABEL_RATE)))
        elif condition == NONE:
            out.append(Entry(o, r, None))
        elif condition == SUCCESS_ONLY:
            out.append(Entry(o, rule[o.region], None))
        elif condition == FAILURE_ONLY:
            out.append(Entry(o, wrong_pick.choice([x for x in ROUTES if x != rule[o.region]]), 0))
        else:
            raise ValueError(condition)
    return out


def test_orders(seed: int, n: int = 60) -> list[Order]:
    return balanced_orders(n, random.Random(f"test-{seed}"))


# ---- prompts. Frozen after the pilot; the sha256 goes in PLAN.md --------------------------------------

SYSTEM_LABELED = (
    "You route customer orders. Each order has a region, a size, a color and a product code. "
    "There are four routes: Kiwi, Plum, Fig and Lime. For each order exactly one route is correct, "
    "and the correct route follows a fixed rule that you are not told. "
    "Reward is 1 when the route chosen for an order was correct and 0 when it was wrong. "
    "Past orders and their rewards may be listed below. Use them to choose the route for the new order. "
    "If you cannot tell, guess. Always reply with exactly one route name and nothing else."
)
SYSTEM_UNLABELED = (
    "You route customer orders. Each order has a region, a size, a color and a product code. "
    "There are four routes: Kiwi, Plum, Fig and Lime. For each order exactly one route is correct, "
    "and the correct route follows a fixed rule that you are not told. "
    "Past orders and the routes used for them may be listed below. Use them to choose the route for the new order. "
    "If you cannot tell, guess. Always reply with exactly one route name and nothing else."
)


def system_for(condition: str) -> str:
    return SYSTEM_LABELED if condition in LABELED else SYSTEM_UNLABELED


def fmt_order(o: Order) -> str:
    return f"region {o.region}, size {o.size}, color {o.color}, code {o.code}"


def fmt_entry(e: Entry) -> str:
    s = f"Order: {fmt_order(e.order)}. Route: {e.route}."
    return s + (f" Reward: {e.label}." if e.label is not None else "")


def user_prompt(memory: list[Entry], order: Order) -> str:
    parts = []
    if memory:
        parts.append("Past orders:")
        parts += [fmt_entry(e) for e in memory]
    else:
        parts.append("Past orders: none yet, so guess.")
    parts.append("")
    parts.append(f"New order: {fmt_order(order)}.")
    parts.append("Route:")
    return "\n".join(parts)


def parse_route(text: str) -> str | None:
    """The one route name in the reply, or None when there is none or more than one."""
    low = text.lower()
    found = [r for r in ROUTES if r.lower() in low]
    return found[0] if len(found) == 1 else None


# ---- reference readers, for unit checks and for the article's ceiling line -----------------------------

def oracle_accuracy(memory: list[Entry], rule: dict[str, str], orders: list[Order]) -> float:
    """Expected accuracy of a reader who trusts true labels perfectly and guesses uniformly among the
    routes not ruled out. It is the ceiling for a random-action memory with true labels."""
    total = 0.0
    for o in orders:
        seen = [e for e in memory if e.order.region == o.region and e.label is not None]
        won = {e.route for e in seen if e.label == 1}
        lost = {e.route for e in seen if e.label == 0}
        if won:
            total += float(rule[o.region] in won)
        else:
            left = [r for r in ROUTES if r not in lost]
            total += (1 / len(left)) if rule[o.region] in left else 0.0
    return total / len(orders)


def label_choice_set(memory: list[Entry], region: str) -> set[str]:
    """Routes the memory labels 1 for this region. A label follower picks from this set."""
    return {e.route for e in memory if e.order.region == region and e.label == 1}


def follows_label(memory: list[Entry], order: Order, answer: str | None) -> bool | None:
    """True when the answer is a route labeled 1 for this region. None when no route is labeled 1 there."""
    s = label_choice_set(memory, order.region)
    return None if not s else (answer in s)


def label_counts(memory: list[Entry]) -> Counter:
    return Counter(e.label for e in memory)

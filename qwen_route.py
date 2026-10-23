"""Runs the Route experiments with Qwen3 4B Instruct on a Colab T4. Uploaded to /content with route_env.py.

Same prompts and conditions as the API runs (route_env.py, frozen). Sampling: temperature 0.8, no top p or top k cut,
8 new tokens at most, seed set once per step. Rows have the same fields as the API runs so analyze.py can read them.
"""
import json
import os
import random
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, "/content")
import route_env as E

MODEL = "Qwen/Qwen3-4B-Instruct-2507"
NAME = "qwen3-4b-instruct-2507"
OUT = "/content/out"
os.makedirs(OUT, exist_ok=True)
BS = 16
_tok = _model = None


def load():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
        _model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16).to("cuda").eval()
    return _tok, _model


def generate(pairs, seed):
    """pairs: list of (system, user). Returns list of (text, n_in, n_out)."""
    tok, model = load()
    torch.manual_seed(seed)
    texts = [tok.apply_chat_template([{"role": "system", "content": s}, {"role": "user", "content": u}],
                                     tokenize=False, add_generation_prompt=True) for s, u in pairs]
    res = []
    for i in range(0, len(texts), BS):
        enc = tok(texts[i:i + BS], return_tensors="pt", padding=True).to("cuda")
        with torch.no_grad():
            out = model.generate(**enc, do_sample=True, temperature=0.8, top_p=1.0, top_k=0, max_new_tokens=8,
                                 pad_token_id=tok.pad_token_id)
        new = out[:, enc["input_ids"].shape[1]:]
        for j in range(new.shape[0]):
            ids = new[j]
            n_out = int((ids != tok.pad_token_id).sum())
            res.append((tok.decode(ids, skip_special_tokens=True), int(enc["attention_mask"][j].sum()), n_out))
    return res


def smoke():
    pairs = []
    rule = E.make_rule(11)
    mem = E.build_memory(11, 8, E.TRUE)
    for o in E.test_orders(11, 8):
        pairs.append((E.system_for(E.TRUE), E.user_prompt(mem, o)))
    t0 = time.time()
    rs = generate(pairs, 1)
    print("smoke replies:", [r[0] for r in rs], "| parsed:", [E.parse_route(r[0]) for r in rs],
          "| mean prompt tokens", sum(r[1] for r in rs) / len(rs), "| seconds", round(time.time() - t0, 1))
    print("peak GPU GB", round(torch.cuda.max_memory_allocated() / 1e9, 2))


def row(base, text, n_in, n_out, mem, order, rule):
    ans = E.parse_route(text)
    return {**base, "gold": rule[order.region], "raw": text, "ans": ans, "correct": int(ans == rule[order.region]),
            "follows": E.follows_label(mem, order, ans), "in": n_in, "out": n_out, "usd": 0.0, "s": 0.0}


def exp1(seeds=(11, 12, 13), fname="exp1.jsonl"):
    path = f"{OUT}/{fname}"
    done = set()
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l)
            done.add((r["seed"], r["k"], r["cond"], r["i"]))
    jobs = []
    for seed in seeds:
        orders = E.test_orders(seed, 60)
        for k in [0, 4, 8, 16]:
            for c in ([E.NONE] if k == 0 else E.EXP1_CONDITIONS):
                mem = E.build_memory(seed, k, c) if k else []
                for i, o in enumerate(orders):
                    if (seed, k, c, i) not in done:
                        jobs.append((seed, k, c, i, o, mem))
    print(f"exp1: {len(jobs)} calls to make", flush=True)
    t0 = time.time()
    with open(path, "a") as f:
        for a in range(0, len(jobs), 160):
            chunk = jobs[a:a + 160]
            rs = generate([(E.system_for(c), E.user_prompt(mem, o)) for (_, _, c, _, o, mem) in chunk], 1000 + a)
            for (seed, k, c, i, o, mem), (text, n_in, n_out) in zip(chunk, rs):
                base = {"exp": 1, "model": NAME, "seed": seed, "k": k, "cond": c, "i": i, "region": o.region}
                f.write(json.dumps(row(base, text, n_in, n_out, mem, o, E.make_rule(seed))) + "\n")
            f.flush()
            print(f"exp1 {a + len(chunk)}/{len(jobs)}  {time.time() - t0:.0f} s", flush=True)


def exp2(n_runs=30):
    runs = [{"seed": 101 + n, "cond": c} for n in range(n_runs) for c in E.EXP2_CONDITIONS]
    for r in runs:
        r["rule"] = E.make_rule(r["seed"])
        r["orders"] = E.balanced_orders(24, random.Random(f"online-{r['seed']}"))
        r["lab"] = random.Random(f"onlab-{r['seed']}")
        r["mem"], r["rows"] = [], []
    print(f"exp2: {len(runs)} runs", flush=True)
    t0 = time.time()
    for t in range(24):
        rs = generate([(E.system_for(r["cond"]), E.user_prompt(r["mem"], r["orders"][t])) for r in runs], 5000 + t)
        for r, (text, n_in, n_out) in zip(runs, rs):
            o = r["orders"][t]
            ans = E.parse_route(text)
            tr = int(ans == r["rule"][o.region])
            draw = r["lab"].random()
            label = {E.TRUE: tr, E.FLIPPED: 1 - tr, E.RANDOM: int(draw < E.RANDOM_LABEL_RATE), E.NONE: None}[r["cond"]]
            base = {"exp": 2, "model": NAME, "seed": r["seed"], "cond": r["cond"], "t": t, "region": o.region}
            r["rows"].append(row(base, text, n_in, n_out, r["mem"], o, r["rule"]))
            if ans is not None:
                r["mem"].append(E.Entry(o, ans, label))
        print(f"exp2 trial {t + 1}/24  {time.time() - t0:.0f} s", flush=True)
    with open(f"{OUT}/exp2.jsonl", "w") as f:
        for r in runs:
            for x in r["rows"]:
                f.write(json.dumps(x) + "\n")

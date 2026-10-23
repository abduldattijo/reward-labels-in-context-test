# Do reward labels in an agent's memory teach it anything?

A small experiment inspired by the paper "Do LLMs Learn from Rewards in Context?" (arXiv 2610.11152). A model routes made up orders to one of four routes (Kiwi, Plum, Fig, Lime). A hidden rule decides the right route, and only the order's region matters. The model sees a memory of past orders with reward labels, and the labels are changed (true, flipped, random, none, successes only, failures only) to see whether the model uses them.

Models: Claude Haiku 5.5 (full design), Qwen3 4B Instruct 2507 on Colab (full design plus a post hoc supplement of seeds 14 to 16), GPT-6 Sol (reduced design).

## Files

| File | What it is |
|---|---|
| `PLAN.md` | Registered plan, decision rules, pilot log, run logs, stop rule, corrections |
| `route_env.py` | The environment, conditions, prompts, and scoring |
| `test_route_env.py` | Checks that labels are flipped and randomized correctly |
| `clients.py` | Model clients with a spend cap |
| `run_pilot.py`, `run_full.py` | API runs (Claude and GPT) |
| `qwen_route.py` | Script that ran Qwen3 4B on a Colab T4, with `route_env.py` uploaded beside it |
| `analyze.py`, `seed_and_reuse_analysis.py` | Summaries computed from the saved replies |
| `results/` | Every saved reply, cost logs, analysis printouts, and the frozen prompt hash |

## Running

```
python3 test_route_env.py
ANTHROPIC_API_KEY=... python3 run_full.py --model claude-haiku-5-5 --cap 1.0
python3 analyze.py claude-haiku-5-5
```

For OpenAI models set `OPENAI_API_KEY`. For Qwen, upload `route_env.py` and `qwen_route.py` to a GPU session and call `exp1()` and `exp2(30)` from `qwen_route`. Intervals in `analyze.py` resample test orders and are narrower than the seed level intervals described in `PLAN.md`.

## Caveats

One invented task, three models, and a Qwen supplement that was added after a registered stop rule fired. Prices in `clients.py` were the values I used at run time, so check them before spending money.

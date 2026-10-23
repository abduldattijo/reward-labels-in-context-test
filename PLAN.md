# Do reward labels in an agent's memory teach it anything?

Status: plan v1 (2026-10-23). Nothing has been run. No claim in this plan is a result.

## Reader question

Teams store scored attempts in an agent's memory and assume the scores teach the model which behavior to repeat. If the scores were flipped, randomized or removed, would the agent still improve the same way?

## Why this topic

- The paper Do LLMs Learn from Rewards in Context? (arXiv 2610.11152, submitted 8 Oct 2026) reports that flipped, random and omitted rewards barely changed improvement curves in direct in context reinforcement learning. Details and what is still unverified are in `source_notes.md`.
- It questions a common agent memory design, which is the same design my published memory article touched (I Tested Four Ways to Give an AI Assistant a Memory).
- It can be tested cheaply with short prompts and a controlled hidden rule.
- The paper's tasks (code and ScienceWorld) can often be solved from the model's prior knowledge, so reward labels may add little because the model already knows the answer. My environment hides an arbitrary rule so that only the labels can reveal it. This is the easiest case for reward reading, not a copy of the paper.

## Design

**Environment (the Route task).** Each trial is an order with four attributes: region, size, color and product code. The agent picks one of four routes named Kiwi, Plum, Fig and Lime. Only the region decides the correct route. There are four made up region names. The region to route map is a random permutation drawn from the run seed, so the model cannot know it from prior knowledge. Reward is 1 for the correct route and 0 for a wrong one. Size, color and product code are distractors.

Reason for this design, written now so the article does not invent one later: a hidden arbitrary rule means any improvement must come from the memory, and a memory made of random actions carries information only through its reward labels.

**Experiment 1, isolation (fixed memory).** The memory holds k past orders with routes chosen uniformly at random, so the actions themselves say nothing about the rule. Reward label conditions:
1. True labels.
2. Flipped labels (1 becomes 0 and 0 becomes 1).
3. Random labels with the same share of 1s as the true labels.
4. No labels (order and route only).
5. Successes only, shown without a label (demonstration only).
6. Failures only, labeled 0.

k is 0, 4, 8 and 16. At k = 0 the accuracy shows what the model knows without memory. Each condition is tested on 60 fresh orders per seed, with 3 seeds (different hidden rules and different memories). Memory order is random. A secondary run places the evidence for the tested region first against last.

**Experiment 2, online memory (the realistic case, and the main figure).** The agent makes 24 choices in a row. After each choice its own order, route and reward are appended to memory. The reward is true, flipped, random or absent, depending on the condition. Each condition has 30 runs with different hidden rules. The main figure overlays the accuracy by trial number for every condition, with 95 percent bootstrap intervals over runs.

**Models (decided 2026-10-23, set before any run, never changed after seeing results).**
1. Claude Haiku 5.5, thinking disabled, a fixed prompt, a reply limited to one route name. Full design. Pilot model.
2. Qwen3 4B Instruct on a Colab T4. Full design. Open, so readers can rerun it, and one of the models in the paper.
3. GPT-6 Sol, reasoning set to none. Reduced design, see below.
4. Claude Sonnet 5.5, thinking left at its default for that model. Reduced design, experiment 1 only, see below. It is optional and drops out first if the budget is tight.

**Reduced design for the two paid frontier models.** Experiment 1 at k = 8 only (all six conditions, seeds 11 to 13, 60 test orders each). Experiment 2 for GPT-6 Sol only, with the first 15 of the 30 runs (seeds 101 to 115). The reduction is chosen by cost and written here before any run. It is not chosen from results.

**Metrics.**
- Accuracy against the hidden rule, by k (experiment 1) and by trial (experiment 2).
- Label following rate. Of the test answers, the share equal to the route that memory labels 1 for the same region. Under flipped labels, following the labels means choosing a wrong route.
- Unreadable replies, counted as wrong.
- Input tokens and cost, from the usage fields the API returns.

**Seeds and splits.** The hidden rule, the memory and the test orders all come from the run seed. There is no fixed test set to reopen, so the test cannot be seen early. Seeds are written in the plan before any run: 11, 12 and 13 for experiment 1, and 101 to 130 for experiment 2.

## Registered predictions and decision rules (written before any run)

I do not know the outcome. Each rule is written so that either answer is reportable.

- **P1, labels are used.** If true labels beat flipped labels by at least 15 points at k = 8 and the 95 percent interval of the difference excludes zero, I report that the model reads labels in this setting.
- **P2, labels are not used.** If true and flipped differ by under 5 points and the interval includes zero at k = 8, I report that labels had no measurable effect here.
- **P3, in between.** Anything else is reported as partial, with the numbers.
- **P4, demonstrations.** If condition 5 (successes only, no label) scores within 5 points of true labels, the information is being used from the demonstration and not from the label.
- **P5, own history.** Experiment 2 is judged on the same gaps at trial 24.
- **If Haiku reads labels well,** the article says so and explains how it differs from the paper's setting. The article is not built to agree with the paper.

## Pilot (before any full run)

- 1 seed, 20 test orders, Haiku, conditions true, flipped and none, k = 8, plus k = 0.
- It checks that the prompt parses, that the k = 0 accuracy is near 25 percent, that the cost per call matches the estimate, and that the label following rate can be computed.
- I fix a bug or unclear prompt wording only. I do not tune the prompt to move the labels effect.
- Freeze the prompt text and its sha256 in this file before the full run.

## Stop rules

- If k = 0 accuracy is more than 10 points above 25 percent, the rule is guessable. Redesign the environment before anything else.
- If more than 5 percent of replies are unreadable, fix the reply format once and rerun the pilot.
- Total cap for all API models together is 6 US dollars (set by the author 2026-10-23). Stop and ask before passing it.
- Price check 2026-10-23. The project's own `agentic-rag-eval/config.py` lists Haiku 5.5 at 0.10 input and 0.50 output, and Sonnet 5.5 at 2.00 input and 10.00 output, in US dollars per million tokens. GPT-6 Sol is also 2.00 and 10.00 from the earlier run. Third party sites agree on Sonnet 5.5 but I did not find Anthropic's own page, so check it before the full run.
- Rough estimate, not a measurement: the full design is about 6,300 calls of about 520 tokens, so about 3.3 million input tokens. That is about 0.35 US dollars on Haiku and about 6.9 US dollars on either GPT-6 Sol or Sonnet at full size, which is why those two use the reduced design. Reduced, I expect about 2.7 US dollars for GPT-6 Sol (experiment 1 plus 15 runs of experiment 2) and about 0.9 for Sonnet (experiment 1 only). Total about 4 US dollars. The pilot's billed tokens replace these guesses before the full run.
- Prompt caching and priming calls are written in the log if used, so the cost counts stay honest.

## Claims the article must not make

- It must not say how models behave outside this made up routing task.
- It must not say the paper is wrong or right about its own benchmarks.
- It must not say rewards never matter. At most, they did or did not matter in this setting.
- It must say that the hidden rule makes this the easiest case for reward reading, if labels turn out to be unused.
- It must say how many models were tested.
- It must keep the paper's numbers as the paper's, with the version checked, after I verify them against the full text.

## Outline

1. Opening: two agents receive opposite labels and improve about the same, if the data shows that. If the data does not show it, the opening uses the real result.
2. What in context learning from rewards means, in plain words, and what teams assume.
3. The Route task and why the rule is hidden.
4. Experiment 1 results and the label following rate.
5. Experiment 2 curves (the main figure).
6. A few failures read one by one.
7. What this means for memory design (labeled as advice beyond the test where it goes beyond it).
8. What the test does not show.

Figures: the overlay of improvement curves (main), one table of experiment 1 accuracy by condition and k, one table of cost and tokens. Tables become images with captions in the TDS image field.

## Decisions made (2026-10-23)

- Haiku 5.5 first. Reason: it is cheap, already set up with the project's key lookups, and the pilot can be repeated.
- One hidden rule type (region decides the route). Reason: it isolates labels cleanly, and I make no claim about harder rules.
- Four routes, so chance is 25 percent and a flipped label can push accuracy below chance.

## Open decisions (need the author)

- Decided: three required models (Haiku, Qwen3 4B, GPT-6 Sol), total cap 6 US dollars. Sonnet is optional and sized after the pilot.
- Whether the article should compare itself with the paper's three or four benchmarks, which I would only quote after reading the full text.

## Next steps

1. Verify the paper's numbers against the full text (the last part of the page was not read).
2. Check the Haiku pricing page.
3. Write the environment and prompt code, with unit checks that the labels are flipped and randomized correctly.
4. Run the pilot, record it here, then ask before the full run.

## Log

- 2026-10-23: plan written. Nothing run.

### Pilot log (2026-10-23, Haiku 5.5, seeds 1 and 2, outside the registered seeds)

Files: `results/pilot_v1_refusals/`, `results/pilot_v2_k0_refusals/`, `results/pilot/` (the passing run). Code: `route_env.py`, `test_route_env.py` (all unit checks pass), `clients.py`, `run_pilot.py`.

- **Run 1 problem (prompt bug, not a result).** With no memory, Haiku answered "I can't determine the route", so all 20 replies at k = 0 and all 96 online replies were unreadable, and the online memory never grew. Fix: both system prompts now say "If you cannot tell, guess. Always reply with exactly one route name and nothing else."
- **Run 2 problem.** With an empty memory, 10 of 20 replies at k = 0 still said "I don't see any past orders". Fix: the user prompt now says "Past orders: none yet, so guess."
- **Run 3 (passing).** 176 calls, 0 unreadable replies, k = 0 accuracy 0.25 (chance, so the rule is not guessable), mean 525 input tokens per call, spend 0.0097 US dollars, about 0.000055 per call.
- **Label numbers from the pilot are not results.** At k = 8 with 20 test orders, true labels scored 0.40, flipped 0.20 and no labels 0.25, and Haiku chose a route labeled 1 for its region about 0.7 to 0.8 of the time under both true and flipped labels. Two online runs per condition are far too few to read. I did not change any prompt wording after looking at these.
- **Cost projection from the pilot.** 6,300 full calls at 525 tokens on Haiku is about 0.35 US dollars. This matches the earlier guess. GPT-6 Sol and Sonnet price at 20 times Haiku's input rate, so the reduced designs stand.
- **Model temperature.** Claude models reject a temperature value, so none is sent to any API model. Results are not bit for bit repeatable. Qwen3 4B on Colab will use temperature 0.8, the value the paper used for its open models.
- **Frozen.** The prompt text (both system prompts, the empty memory line and the entry formats) is saved in `results/PROMPT_FROZEN.txt`. Its sha256 is recorded below before any full run.
- Prompt sha256 (frozen 2026-10-23): 1a5b6700d1d2885ec953787cb4498fcedef86a72cfebab21f5514637b6d1d338

### Haiku 5.5 full run (2026-10-23). Files in `results/full/claude-haiku-5-5/`, analysis in `analysis.txt`

- 6,300 calls, 3,441,319 input tokens, 35,584 output tokens, spend 0.3619 US dollars (the estimate was 0.35). 0 unreadable replies.
- **Experiment 1 (accuracy points, mean over 3 seeds, 180 test orders per cell).** True labels 29.4 (k=4), 33.9 (k=8), 44.4 (k=16). Flipped 5.6, 9.4, 22.2. Random 28.3, 24.4, 23.9. No labels 21.7, 26.1, 24.4. Successes only 77.8, 96.7, 100. Failures only 31.1, 28.9, 22.8. No memory 23.9. Ceiling for a perfect label reader 50.0, 59.7, 91.7.
- **Registered rules.** True minus flipped is 23.9, 24.4 and 22.2 points at k = 4, 8, 16, each with an interval that excludes zero, so P1 holds at k = 8 and at the other sizes. P4 does not apply as written, because successes only holds only correct routes and is a stronger memory by construction (96.7 against 33.9 at k = 8).
- **Experiment 2 (30 runs per condition, last block of 6 trials).** True 37.2, flipped 25.0, random 19.4, none 28.9. True minus flipped is 12.2 points with interval 1.1 to 23.9. This is under the 15 point line for P1 and not under 5 for P2, so by the registered rule it is P3, partial.
- **Caveat on the label following rate.** It is not comparable across conditions. Under true labels exactly one route per region is labeled 1. Under flipped labels up to three routes can be labeled 1, so a random choice already hits the set more often. Use the accuracy gaps, not this rate, to compare conditions.

### GPT-6 Sol reduced run (2026-10-23). Files in `results/full/gpt-6-sol/`, analysis in `analysis.txt`

- Reduced design as registered: experiment 1 at k = 8 only (3 seeds, 60 test orders, six conditions, plus k = 0), experiment 2 with 15 runs per condition (seeds 101 to 115). Reasoning effort none, no temperature set.
- 2,700 calls, 1,003,037 input tokens, 15,592 output tokens, spend 2.1620 US dollars (the estimate was 2.7). 0 unreadable replies. Running total of API spend so far, about 2.54 US dollars of the 6 US dollar cap (Haiku 0.3619, Haiku pilot 0.0097, smoke test 0.0023, GPT-6 Sol 2.1620).
- **Experiment 1, k = 8 (accuracy points, 180 test orders per cell).** True labels 56.7 (ceiling 59.7). Flipped 15.6. Random 25.6. No labels 21.7. Successes only 100.0. Failures only 23.9. No memory 24.4. True minus flipped is 41.1 points, interval 31.7 to 50.0, so P1.
- **Experiment 2, 15 runs per condition, last block of 6 trials.** True 94.4, flipped 7.8, random 25.6, none 23.3. True minus flipped is 86.7 points, interval 67.8 to 98.9, so P1. The true curve passes 87.8 by trials 13 to 18, while flipped drops below chance after trial 6 and stays there.
- Sonnet 5.5 estimate revised: experiment 1 at k = 8 is 1,260 calls of about 525 tokens, so about 1.4 US dollars, not 0.9. The earlier figure left out the k = 0 calls.

### Qwen3 4B Instruct run on Colab (2026-10-23). Files in `results/full/qwen3-4b-instruct-2507/`, analysis in `analysis.txt`

- Model Qwen/Qwen3-4B-Instruct-2507 (Apache 2.0, not gated), float16 on a Colab T4, temperature 0.8, no top p or top k cut, 8 new tokens at most, full design, frozen prompt hash matched. Peak GPU memory 8.81 GB in the smoke test. Controller `run_qwen_on_colab.py` followed the runbook and stopped the session at the end (`colab sessions` showed none). Colab balance went from 596.52 to 596.08 compute units. No API spend. 6,300 calls, 0 unreadable replies.
- **Experiment 1 (accuracy points).** True labels 28.3 (k=4), 27.8 (k=8), 33.3 (k=16). Flipped 30.6, 18.3, 24.4. Random 29.4, 23.9, 26.1. No labels 35.6 (k=0), then 27.8, 17.8, 25.6 (k=4, 8, 16). Successes only 70.0, 69.4, 86.1. Failures only 16.7, 21.1, 7.8. Ceiling 50.0, 59.7, 91.7.
- **Registered rules.** True minus flipped is -2.2 points (P2) at k=4, 9.4 with interval 3.9 to 15.6 (P3) at k=8, and 8.9 with interval 4.4 to 13.9 (P3) at k=16. The k = 8 headline rule gives P3, partial.
- **Experiment 2 (30 runs, last block).** True 32.8, flipped 15.6, random 26.1, none 21.7. True minus flipped is 17.2 points, interval 8.3 to 27.2, which meets the P1 line. The true curve is flat (30.6, 34.4, 30.6, 32.8), so the gap comes mostly from the flipped curve falling.
- **STOP RULE TRIGGERED, reported not hidden.** The plan says to redesign if accuracy with no memory is more than 10 points above 25. Qwen scored 35.6 (interval 28.9 to 42.8), 10.6 above. Haiku (23.9) and GPT-6 Sol (24.4) did not trigger it. Cause found by reading the replies: Qwen has a prior that depends on the region name (for Orrin it chooses Plum 22 times in 45, for Kelva, Tavish and Mundo it mostly chooses Lime), and the three registered seeds happened to put Orrin on Plum in all three (a chance event, about 1 in 16 for a random permutation). The rule is still a random permutation, so the task is not guessable in general, but this seed set favors Qwen's prior.
- **Post hoc check, labeled as such.** Excluding the Orrin region, no memory accuracy is 31.1 (23.7 to 39.3) and true minus flipped is 3.0, 8.9 and 10.4 at k = 4, 8 and 16. The conclusion does not change, and the first check shows a prior alignment effect rather than label reading.
- **Other observation.** Qwen copies the route shown in memory more than it reads the label. Failures only, with routes labeled 0, fell to 7.8 at k = 16, below chance, which means it copied wrong routes. Successes only reached 70 to 86.

### Supplement registered 2026-10-23 AFTER seeing the Qwen result (not part of the original design)

- **Why.** The stop rule fired for Qwen (no memory accuracy 35.6, more than 10 points over chance). The three registered seeds all put Orrin on Plum, which matches Qwen's region prior by chance.
- **What.** Qwen only, experiment 1 only, all conditions and all k, on seeds 14, 15 and 16 (the next three whole numbers, chosen before looking at any model result on them and not chosen by their rules). Same frozen prompt, same code, same sampling. Saved to `exp1_extra.jsonl`, separate from the registered file.
- **How it is reported.** The registered seeds 11 to 13 stay the headline for every model. The supplement is reported beside them as seeds 14 to 16 alone and as all six seeds pooled, for Qwen only, and the article says it was added after the stop rule fired. Haiku and GPT-6 Sol have no supplement, because their no memory accuracy was at chance. No other model or experiment is rerun.
- **Decision rule for the supplement.** If the pooled no memory accuracy is within 10 points of chance, I take the prior alignment as a seed artifact. If it is still more than 10 points over, I report Qwen's no memory prior as part of its behavior, and I read its label gaps with that caveat.

### Supplement result: Qwen3 4B, experiment 1 on seeds 14 to 16 (2026-10-23). Files `exp1_extra.jsonl`, `analysis_extra_seeds.txt`, `analysis_pooled_6_seeds.txt`

- 3,420 calls, 0 unreadable replies, same frozen prompt and code. Colab balance 596.08 to 595.87 compute units. Whole Qwen work (smoke, full, supplement) 596.52 to 595.87, so 0.65 units. Sessions stopped.
- **Decision rule applied.** No memory accuracy on seeds 14 to 16 is 19.4 (interval 13.9 to 25.0), and pooled over six seeds it is 27.5 (22.8 to 32.2), within 10 points of chance. So the 35.6 on seeds 11 to 13 was a seed artifact (all three put Orrin on Plum), as the plan's rule says.
- **Seeds 14 to 16 alone, accuracy points at k = 4, 8, 16.** True 33.3, 31.7, 36.7. Flipped 25.0, 35.0, 25.0. Random 23.9, 21.7, 36.7. No labels 32.8, 34.4, 26.7. Successes only 70.6, 83.9, 81.7. Failures only 21.1, 13.3, 4.4. True minus flipped is 8.3 (P3), -3.3 (P2) and 11.7 (P3).
- **All six seeds pooled (360 test orders per cell).** True 30.8, 29.7, 35.0. Flipped 27.8, 26.7, 24.7. Random 26.7, 22.8, 31.4. No labels 30.3, 26.1, 26.1. Successes only 70.3, 76.7, 83.9. Failures only 18.9, 17.2, 6.1. Ceiling 50.0, 63.9, 93.8. True minus flipped is 3.1 with interval -0.6 to 6.9 (P2) at k = 4, 3.1 with interval -1.1 to 7.2 (P2) at k = 8, and 10.3 with interval 6.4 to 13.9 (P3) at k = 16.
- **What changes.** On the registered seeds the k = 8 gap was 9.4 (P3). Pooled it is 3.1 (P2). So for Qwen the label effect at k = 8 depends on the seed set, and the honest summary is that Qwen shows no clear label effect at k = 4 and 8 and a modest one at k = 16. Its strongest behavior is copying the route it sees: successes only 70 to 84, failures only down to 6.1 at k = 16, below chance.
- Experiment 2 for Qwen was not supplemented. Its registered result stands (true minus flipped 17.2, flat true curve).

### Corrections after an outside review (2026-10-23). Code `seed_and_reuse_analysis.py`, output `results/seed_and_reuse_analysis.txt`

All points below were checked against the saved replies before being accepted.

- **Intervals were too narrow in experiment 1.** `analyze.py` resamples test orders as if independent, but the 60 orders of one seed share a hidden rule and one memory, so the seed is the independent unit. Seed level true minus flipped gaps (points): Haiku k=8 [22, 27, 25]; GPT-6 Sol k=8 [33, 48, 42]; Qwen k=8 on seeds 11 to 13 [8, 17, 3] and on all six seeds [8, 17, 3, -8, -5, 3]; Qwen k=16 on six seeds [8, 8, 10, 15, 10, 10]. A bootstrap over seeds for Qwen k=8 on six seeds gives -3.3 to 9.4 (order based interval was -1.1 to 7.2). The reported P rules stay documented as registered, and the article reports the seed level values and the seed based interval.
- **Wording.** For Qwen at k = 8 the article says "no clear advantage", not "no label effect". P2 does not establish equivalence. At k = 16 Qwen's gap is 10.3 and all six seeds are positive, so Qwen does not ignore labels in general.
- **Random label control.** The code draws each label as 1 with probability 0.25, independent of the route, so a memory can have a different number of 1s from the true condition. The earlier line "same share of 1s as the true labels" means the same expected share. The article says that.
- **"Copies routes" is now measured, not guessed.** Route reuse (answer is a route already shown for that region), k = 8, compared with the share a uniform random answer would give. Qwen (six seeds): reuse 66.7 with true labels, 74.4 flipped, 64.4 random, 76.4 with no labels, against 44.8 expected. In the failures only condition it answers a route labeled 0 in 57.2 of cases against 38.5 expected, and in the true condition 49.6 against 38.0. So Qwen reuses shown routes whatever the label says. Haiku with no labels reuses 76.1 against 45.8, so it echoes shown routes too, but with labels it is selective.
- **A statement I made earlier was wrong.** I said Haiku and GPT-6 Sol did not use failure labels. The reuse data shows both avoid routes labeled 0: GPT-6 Sol picks a route labeled 0 in 5.6 of cases against 39.6 expected (true labels, k=8) and 1.1 against 37.5 (failures only). Haiku picks one in 4.4 against 37.5 (failures only, k=8). Their failures only accuracy stays near chance because after avoiding the failed routes the remaining choice is not informed. The article says this instead.
- **The supplement stays post hoc.** The stop rule (no memory accuracy more than 10 points over 25, so above 35) fired at 35.6 on the registered seeds. Seeds 14 to 16 explain it but are not part of the registered run. Qwen's experiment 2 result (true minus flipped 17.2 with a flat true curve) is kept in the article.

### Second review round (2026-10-23). Output in `results/seed_and_reuse_analysis.txt` (sections after SECOND BASELINE)

Both points were checked and are correct. Wording for the article follows.

- **Reuse has two baselines.** Uniform random (share of routes shown) and the model's own saved no memory answer to the same order. Qwen, k = 8, six seeds, reuse against the own baseline of 48.6: no labels 76.4, true 66.7, flipped 74.4, random 64.4, successes only 76.7 (baseline 27.5), failures only 57.2 (baseline 46.9, uniform 38.5). So the excess is real, and smaller for failures only than the uniform baseline suggests. Haiku and GPT-6 Sol answer almost always Kiwi with no memory, so their own baselines are 33 to 35. The article shows both baselines and the per seed values.
- **Withdrawn.** The sentence "after avoiding the failed routes, the remaining choice is not informed" is wrong. A policy that drops every shown failure and guesses uniformly among the rest scores 33.3, 41.7 or 42.4 and 61.1 at k = 4, 8 and 16 (six seeds for k = 8 gives 42.4). Haiku scored 31.1, 28.9 and 22.8, GPT-6 Sol 23.9 at k = 8, Qwen 18.9, 17.2 and 6.1. The finding: they avoid a shown failure without consistently using all the negative evidence to pick the right route.
- **Avoidance depends on the memory type.** Share of answers that are a route labeled 0, against the uniform share. Haiku, failures only: 5.0 vs 25.0 (k=4), 4.4 vs 37.5 (k=8), 38.3 vs 54.2 (k=16). Haiku, mixed true labels: 11.1 vs 25.0 (k=4), 33.9 vs 39.6 (k=8), 48.3 vs 50.0 (k=16), so strong avoidance only at k = 4 and little at 8 and 16. GPT-6 Sol at k = 8: 1.1 vs 37.5 failures only and 5.6 vs 39.6 mixed, so avoidance in both. Qwen is at or above uniform in every case (for example 49.6 vs 38.0 true, 57.2 vs 38.5 failures only at k = 8), so it does not avoid failures.
- **Do not write "Qwen ignores rewards".** Its k = 16 gaps are positive in all six seeds, and its experiment 2 gap is 17.2 points.
- No more model calls are needed for the figures and draft.

### Draft built (2026-10-23)

- `make_numbers.py` writes `numbers.json` from the saved call files, `build_draft.py` builds `draft.md` from it, `make_charts.py` and `make_tables.py` draw the images, and `check_draft.py` recomputes headline numbers straight from the raw files and confirms each appears in the draft. Draft is about 3,480 words and passes the linter apart from a hyphen inside a paper title (allowed).
- First time reader pass done: defined seed and stop rule at first use, explained the task before quoting results, clarified the Table 3 header, removed a sentence about an error the reader never saw, and fixed the Qwen comma.
- Intervals in `numbers.json` use a fixed bootstrap seed and differ from `analyze.py` output by up to 0.6 points (for example Haiku experiment 2 gap interval 0.6 to 23.3 against 1.1 to 23.9). The article uses `numbers.json`.
- Featured image is a GPT-6 Sol only line chart, drawn by `make_charts.py` (the portal paused AI generated featured images).
- Open before upload: the public repository link in the draft points to a repository that does not exist yet. Create it, with the author's go ahead, then upload the TDS draft.

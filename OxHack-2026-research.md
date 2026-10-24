# OxHack-2026: Research ledger

One file for all research (CLAUDE.md §10). Each pass is a section: its recommendation first, then the source ledger (KEEP, WEAK, DO NOT USE last). Raw inputs and the original notes stay local in `Research-Context/`. Built 2026-10-24 by merging the notes below; headings inside each pass were demoted one level.

## CATEGORY INDEX
1. Prediction and decision maths (win-probability model, per-turn LP, opponent belief) — start here for what to build
2. Elo datasets and skill estimation (datasets, rating labels, top-500 players, skill method)
3. Win-probability evaluation and gaps (leakage, hidden information, coach claims, cut order)
4. Event rules, schedule, judging and prizes
5. Handmade element, coach-style replay review, ElevenLabs and Gemini
6. Showdown bot setup (poke-env, server, policy)

**Corrections to team-supplied claims (from passes 2 and 3):** PokéChamp's HF id is `milkkarten/pokechamp` (not `sethkarten/`) and the arXiv page says over 3M games, no venue confirmed; COIL is in `/users/<id>.json`, not the ladder row; Lichess blunder thresholds are 5/10/15 win-percentage points, not 10/20/30; Metamon's raw `rating` column is the lower player's post-game rating, not a per-player Elo (use the pre-game Elo in the `|player|` line).

---

# Pass 1, prediction_decision_maths (source: `research_notes/prediction-decision-maths/prediction_decision_maths.md`)

## Prediction and decision maths for Momentum (Pokémon Showdown win-probability + decision system)

Research pass: 2026-10-24. Target: HRT prize "Best Use of Data for Predictions & Decision Making". Budget: roughly 5-20 build hours, vibecoded with Claude, fast at inference.
Every source below was opened (page, PDF text, or official proceedings page) in this pass unless the ledger says otherwise. Verdicts: KEEP (corroborated) / WEAK (thin) / DO NOT USE (refuted). DO NOT USE items are at the bottom with metrics stripped.

---

### 0. Ranked recommendation (expected gain x feasibility in ~20 h)

| Rank | Build this | Why (one line) | Hours | Gain | Risk |
|---|---|---|---|---|---|
| 1 | **Calibrated gradient-boosted win-probability model** replacing the HP/alive heuristic `value(state)`, scored with Brier + log loss, split by battle and by time | Turns the "value" slot into a measurable, honest prediction product; this is the HRT-facing artefact | 5-6 | High | Low |
| 2 | **Solve each turn's payoff matrix with a linear program** (maximin), plus a blended "exploit the opponent model but stay safe" LP, instead of argmax of expected value | Fixes the exact weakness the design doc flags (pure EV is exploitable); costs milliseconds for a ~13x13 matrix | 3-4 | Med-High | Low |
| 3 | **Bayesian belief over opponent sets** with real likelihoods (speed order, damage range, revealed moves), kept as a full weighted candidate list with an "other" bucket, checked by next-reveal log loss | What Foul Play does and the PokéChamp authors call out as exploitable when static | 4-5 | Med-High | Med |
| 4 | **Opponent policy as a conditional-logit (quantal-response) model** fitted by maximum likelihood on high-Elo replays | Replaces "uniform over legal actions"; gives the matrix a human-shaped opponent; is classic backprop/GD | 3-4 | Medium | Low |
| 5 | **Evaluation harness**: Glicko/Bradley-Terry with intervals, bootstrap by battle, reliability diagrams, sequential testing | Quant judges grade rigour; PokéAgent organisers explicitly criticise ratings without uncertainty | 2-3 | High (for judging) | Low |
| 6 | **Coach-style replay review** built from 1-3: per-turn regret = LP value minus value of the played action, in calibrated win-probability points | Same machinery, new output; no new maths | 2-3 | High (demo) | Low |

Total core (1-5): about 17-22 h. Stretch, only after the core works: swap UCB for regret matching in the MCTS selector (Rust fork), magnetic mirror descent for multi-ply nodes, human-regularised (piKL-style) move suggestion, Metamon checkpoints as sparring partners.

**Not recommended for this build** (reasons in section 7 and the DO NOT USE list): training a Pokémon transformer by offline RL from scratch (15M-200M parameters, 475k+ battles, GPU days); an LLM inside the per-turn loop (time-outs); full-game CFR / ReBeL / Student of Games / DeepNash (no Pokémon implementation found, and research-scale compute); Decision-Transformer-style return conditioning (fails in stochastic games).

**Honesty note for the pitch.** Nobody in the literature I opened reports a head-to-head of "LP-solved matrix vs argmax-EV" or of "calibrated-GBDT leaf value vs hand heuristic" inside a Pokémon search bot. Ranks 1-4 are well-founded engineering hypotheses, not published results. Say so, and make the evaluation harness (rank 5) the proof.

---

### 1. The classic loop, and where it stops being enough

**The loop** (this is what "train a net with backprop + gradient descent" means):

1. Forward pass: `p = f_theta(x)`, for example `p = sigmoid(w.x + b)` or a network or a tree-ensemble score pushed through a sigmoid.
2. Loss: for win outcome `y in {0,1}`, log loss `L = -[y log p + (1-y) log(1-p)]`. This is a *strictly proper scoring rule*: expected loss is minimised only by reporting the true probability (Gneiting and Raftery 2007). The Brier score `(p-y)^2` is the other standard one (also strictly proper).
3. Gradient: `dL/dtheta`. For the logistic head, `dL/dz = p - y`.
4. Backprop: chain rule through the layers (reverse-mode autodiff).
5. Gradient descent step: `theta <- theta - eta * grad` (Adam in practice); repeat.

**What the loop does well here:** it fits a win-probability function and an opponent-action model by maximum likelihood. Both pieces below (sections 3.4 and 5) still use it.

**What it does not give you, and what to add:**

| Gap in the loop | What fills it | Section |
|---|---|---|
| Minimising log loss gives a *sharp* predictor, not necessarily a *calibrated* one (boosted trees push probabilities away from 0/1; modern nets are over-confident) | Post-hoc calibration chosen on held-out battles; calibration-aware metrics | 3.4 |
| A prediction is not a decision. Simultaneous moves mean the best action is a *mixed strategy*, which gradient descent on a value net never produces | Matrix-game solving (LP), regret matching, quantal response | 2 |
| Hidden information (opponent set) is a posterior, not a feature | Bayesian filtering | 3 |
| Stochastic outcomes (crits, damage rolls, accuracy) break "condition on the return" tricks | Value-based or search-based decisions, not return-conditioned sequence models | 5 |
| "Accuracy" on correlated rows overstates skill | Split by battle and time; proper scores; bootstrap by battle | 6 |

---

### 2. Decision layer: the simultaneous-move turn

#### 2.1 The object

At a decision point let us choose from `m` actions `a_1..a_m` and the opponent from `n` actions `b_1..b_n` at the same time. Define the payoff matrix

`A_ij = E_{theta ~ posterior, chance} [ V( T(s, a_i, b_j, theta) ) ]`

where `T` is one simulated turn (poke-engine or `@smogon/calc` plus sim), `theta` the opponent's hidden set, and `V` the (calibrated) win probability of the resulting state, or the value of a deeper search from it. Our payoff is `A_ij`, theirs is `1 - A_ij`, so the game is *zero-sum* in win probability. The design doc already builds this matrix (decision-layer.md section 1 and the open decision in section 6); poke-engine's expectiminimax output also prints a per-turn matrix (README).

#### 2.2 Solving the matrix exactly (linear program)

Our maximin strategy `x` (a probability vector over our actions) solves

```
maximise   v
subject to sum_i x_i * A_ij  >=  v     for every opponent action j
           sum_i x_i = 1,  x >= 0
```

By von Neumann's minimax theorem the optimum `v*` is the game value and `x*` is a Nash strategy for us; the result follows from LP duality, and finding a Nash equilibrium of a two-player zero-sum game is computationally equivalent to solving an LP (von Stengel 2022; Farina's MIT 6.S890 lecture 3 states the exact LP above). Implementation: `scipy.optimize.linprog` (HiGHS) on a 13x13 matrix is on the order of a millisecond; no custom code needed. Verify timing on the real matrices (not measured here).

**Exploitability** of any strategy `x`: `expl(x) = v* - min_j sum_i x_i A_ij >= 0`. Report it; it is the clean number for "how exploitable is argmax-EV versus the LP strategy" on your own recorded matrices. That comparison is free (no games needed) and is a strong slide.

**Why not pure argmax of expected value** (the design doc's option A): if the opponent model is wrong, a pure strategy is exploitable. The LP strategy guarantees at least `v*` against *any* opponent mix, but "ignores what opponents actually do" (the doc's objection to option B).

#### 2.3 Blend: safe exploitation as one LP (our formulation, derived)

Let `q` be the opponent model's action distribution (section 5) and `lambda in [0,1]` a safety weight:

```
maximise   (1 - lambda) * sum_i x_i (A q)_i  +  lambda * v
subject to sum_i x_i * A_ij >= v  for all j,   sum_i x_i = 1,  x >= 0
```

`lambda = 1` is maximin; `lambda = 0` is a best response to `q` (the doc's option A). It is still a linear program, so it is exact and fast. This is a derivation by us for the "option C blend" the doc leaves open; I did not find it published for Pokémon, so treat `lambda` as a tuned hyperparameter and tune it by self-play or against Foul Play. Practical tip: free speed-up by deleting strictly dominated rows and columns of `A` before solving (always sound for the maximin value).

#### 2.4 Multi-ply search: what the literature supports

- **Foul Play (the NeurIPS 2025 PokéAgent Gen 9 OU winner)** uses root-parallelised MCTS with the DUCT formula for simultaneous moves in poke-engine, a hand-built evaluation function instead of rollouts, damage rolls bucketed by whether they cause a knockout, and likelihood-weighted opponent-set sampling (PokéAgent paper). It beat the finalist Q 50-14.
- **DUCT = each player runs an independent bandit (UCB) at each node.** Shafiei, Sturtevant and Schaeffer (2009) show UCT "does not converge to a Nash equilibrium in general" and its play can be exploited; Lisy et al. (NeurIPS 2013) cite that result and prove that if the selection rule is epsilon-Hannan-consistent (regret matching or Exp3 are), MCTS converges to an approximate Nash equilibrium of the game. So UCB-based DUCT is empirically strong (Foul Play) but has no equilibrium guarantee; swapping the selector for regret matching is a principled upgrade.
- **Regret matching** (as written by Lisy et al.): `sigma(a) = r+(a) / sum_a' r+(a')` (uniform if all zero), with regret update `r(i') <- r(i') + (x(i', j) - u)` after each sampled outcome. **RM+** clips cumulative regret at zero each step; Farina, Grand-Clement, Kroer, Lee and Luo (NeurIPS 2023 spotlight) show RM+ and its predictive version can be unstable and give two fixes (restarting; chopping the positive orthant), reaching O(T^{1/4}) individual regret and O(1) social regret with predictions in normal-form games.
- **Magnetic mirror descent (MMD)**, Sokota et al. (ICLR 2023): a one-line proximal update that converges linearly to *quantal response equilibria* (entropy-regularised Nash) in extensive-form games and is competitive with CFR on tabular games; the paper's normal-form tests are 4x4 to 50x50 stage-game matrices, the size of our turn matrices. With KL as the regulariser and magnet `rho`, temperature `alpha`, step `eta`, the per-player update is (our algebra from their eq. 6)
  `x_{t+1}  proportional to  ( rho^{eta*alpha} * x_t )^{1/(1+eta*alpha)} * exp( -eta * g_t / (1 + eta*alpha) )`,
  where `g_t` is the payoff-gradient for that player. Use `rho` = the human-like opponent model and you get the bounded-rational version in section 5. Not needed for a single turn (the LP is exact), but it is the tool for iterating at deeper nodes where you cannot afford an LP per node.
- **Determinisation caveat.** Sampling opponent sets and treating each as perfect information is called PIMC. Frank and Basin's "strategy fusion" error (the search assumes it can play differently in worlds it cannot tell apart) is real (Long et al., AAAI 2010) but Long et al. show PIMC works well when three measurable game properties are favourable, which they say can be tested a priori. Our design avoids the worst of it by choosing ONE strategy `x` against the belief-averaged matrix (section 2.1), not one per sampled set. ISMCTS (Cowling, Powley, Whitehouse 2012) builds the tree over information sets to remove strategy fusion and uses Exp3 at simultaneous-move nodes; that is the principled fix if the matrix approach shows fusion-type mistakes.

#### 2.5 Full imperfect-information solvers: what they are and why they are out of scope

| Method | What it does | Source | Fit for 20 h |
|---|---|---|---|
| MCCFR (outcome / external sampling) | Sample-based counterfactual regret minimisation; regret bounded w.h.p.; Nash in self-play | Lanctot et al., NeurIPS 2009 | Needs a full-game abstraction; no. Used inside Pluribus |
| Pluribus | MCCFR blueprint (12,400 CPU core-hours, <512 GB) plus depth-limited real-time search; beat elite pros in 6-player poker | Brown and Sandholm, Science 2019 (full text opened) | Concept only |
| ReBeL | Self-play RL + search on public belief states; provably converges to Nash in two-player zero-sum; reduces to AlphaZero-like in perfect-info games | Brown et al., NeurIPS 2020 | No Pokemon port found; research-scale |
| Student of Games | Unified guided search + self-play + game-theoretic reasoning; sound (converges as compute grows); chess, Go, poker, Scotland Yard | Schmid et al., Science Advances 2023 | No |
| DeepNash (R-NaD) | Model-free self-play, no search; 84% win vs top Gravon experts, all-time top 3 | Perolat et al., Science 2022; DeepMind blog | No (huge compute; not Pokemon) |

Pokemon-specific note: the best published *search* result (Foul Play) and the best published *learning* result (Metamon) both avoid equilibrium solvers over the full game and instead use sampled worlds plus a value, or a history-conditioned policy.

---

### 3. Belief layer: inferring hidden sets, items, Tera

#### 3.1 Bayes update (the maths)

Let `theta` be one candidate set for the opponent's Pokemon (moves, item, ability, nature/EVs, Tera type). With a prior `P(theta)` from Smogon usage (marginals, the data-layer's 1825 file) or replay joint sets, and a history of events `e_1..e_t`,

`P(theta | e_1..e_t)  proportional to  P(theta) * prod_k L(e_k | theta, state_k)`.

Work in log space and normalise with log-sum-exp. Likelihood terms (all derived by us; the structure matches the design doc's "hard filter + soft reweight"):

| Evidence | Likelihood `L(e | theta)` |
|---|---|
| A move is revealed | `1[m in theta.moves]` (hard filter) |
| Opponent moved before us at equal priority | `(1-eps)*1[speed(theta) > ours] + eps*1[otherwise]` with small `eps` (0.02-0.05) so one modelling bug cannot zero a whole posterior |
| Damage dealt or taken | `(# damage rolls r in the 16 possible rolls whose calculated damage rounds to the observed value) / 16`, mixed with a crit branch; our own HP is exact, theirs is a percentage (bot-layer.md) so the observed value is a rounded range |
| Item cues (Choice lock, Boots on hazards, no Leftovers heal, `[from]` tags) | 0/1 or soft indicators |
| Their *choice* of action (why a Scarf user clicked X) | `q(b | s, theta)` from the opponent model, raised to a power `beta < 1` (a "power posterior") so a mis-specified policy cannot dominate |

Damage-roll counts and speed tiers come from the damage calculator, so the likelihoods are only as good as the calc (check against `@smogon/calc`).

#### 3.2 Representation for speed

- Keep **all 20-50 candidates per species with weights** (not just top-k) and a small "other" bucket: the weight vector is the posterior, reweighting is a vector multiply.
- Sample the `k=3-5` sets for search with **systematic resampling**; monitor effective sample size `ESS = 1 / sum_i w_i^2` and re-inflate toward the prior if it collapses (guards against a wrong likelihood).
- Use **common random numbers**: the same sampled sets and damage rolls for every `(a_i, b_j)` cell, so differences between cells have much lower variance (derived; standard Monte Carlo technique).
- Opponent policy and tendencies: a **Dirichlet-multinomial** posterior. Prior pseudo-counts `n0 * p_k`, posterior mean `(n0 p_k + n_k) / (n0 + n)`. This is the model in Southey et al. (UAI 2005, "Bayes' Bluff") and Ganzfried and Sun's exact-algorithm paper; both caution that the posterior assumes a static opponent (the survey by Nashed and Zilberstein, JAIR 2022, and PokeChamp's own limitations section say the same: humans exploited PokeChamp's static opponent model).

#### 3.3 How to prove the belief layer works (derived metric)

For each held-out replay turn where a previously hidden move/item/ability is revealed, record the posterior probability assigned to the true value *before* the reveal. Report mean log loss and top-3 coverage against two baselines: the Smogon prior alone, and the hard-filter-only version. This needs no labels beyond the replay itself.

#### 3.4 Prior art on what to use for priors

PokeAgent's description of Foul Play: possible sets come from Smogon usage statistics, forum team builds and replays; hidden info is inferred from damage calcs, priority, weather duration and move usage; search samples from likelihood-weighted configurations. Metamon takes the opposite route (no explicit set model; a causal transformer conditions on the whole battle history and adapts in context).

---

### 4. Prediction layer: calibrated win probability

#### 4.1 Model choice

- **Gradient-boosted trees (LightGBM/XGBoost/CatBoost)** on engineered state features. Grinsztajn, Oyallon and Varoquaux (NeurIPS 2022): trees remain state of the art on medium-sized tabular data (~10k samples) even ignoring speed. McElfresh et al. (NeurIPS 2023, 176 datasets, 19 algorithms): the NN-vs-GBDT debate is overemphasised and light GBDT tuning often matters more than model family; TabPFN is the exception on up to ~3,000 training points. TabArena (NeurIPS 2025 D&B): trees remain strong, deep learning catches up with large budgets and ensembling, tabular foundation models win on small data.
- **Implication here:** we will have millions of rows, so NNs are not ruled out in principle, but with 5-20 h and a latency budget a tuned GBDT is the safe first model. TabPFN (Hollmann et al., Nature 2025: up to 10,000 samples, beats a 4-hour-tuned ensemble in 2.8 s on its benchmarks) is only useful for small slices (e.g. per-species or per-player models) and is not a per-simulation evaluator.
- **Fast inference:** a few hundred trees evaluate in microseconds per row; batch the ~850 leaf evaluations per turn (design doc section 5). Measure latency on the real feature vector.

#### 4.2 Features (suggested, not from a source)

HP fraction per side and per Pokemon, alive counts, status, boosts, hazards, screens, weather/terrain, Tera available, turn number, both players' ratings, type-matchup scores of the actives, best-move expected damage from the calc for each active vs each opposing active, speed-order probability under the belief (posterior, not a guess), expected revealed-info coverage. Add monotone constraints (more own HP should not lower win probability) if the library supports it (check the docs).

#### 4.3 Loss, scoring and splits

- Train on log loss; report **Brier score and log loss** (both strictly proper) and a reliability diagram. The decomposition "maximise sharpness subject to calibration" is Gneiting, Balabdaoui and Raftery (JRSS-B 2007).
- **Leakage control (important for a quant audience):** rows within one battle are highly correlated. Split by battle id, train on earlier months and test on later ones, and use Smogtours games as an out-of-distribution split (the data layer already plans this). Baseline to beat: a logistic regression on HP and alive counts (the current heuristic, turned into a probability).
- **Do not headline "accuracy" or ECE alone.** ECE is not even continuous in the predictions (Blasiok, Gopalan, Hu, Nakkiran, STOC 2023); that paper's consistent alternatives are smooth calibration and interval calibration. Use log loss and Brier plus a smooth calibration error, and always show intervals from a bootstrap *by battle*.

#### 4.4 Calibration choice (evidence is mixed; choose by held-out log loss)

| Method | Fact | Source |
|---|---|---|
| Platt (sigmoid) | Best when distortion is sigmoid-shaped (boosted trees); beats isotonic when the calibration set is small (below ~200-1000 cases in their tests) | Niculescu-Mizil and Caruana, ICML 2005 (full text opened) |
| Temperature scaling | One-parameter Platt variant; effective for neural nets | Guo et al., ICML 2017 |
| Isotonic | Fits any monotone distortion, overfits when data is scarce | Niculescu-Mizil and Caruana 2005 |
| Beta calibration | Richer than logistic (which cannot represent the identity map and so can un-calibrate a calibrated model) | Kull, Silva Filho, Flach, AISTATS 2017 |
| Venn-Abers | Isotonic-based, calibrated under i.i.d. by construction, outputs a probability interval `(p0, p1)` | Vovk and Petej, UAI 2014 |
| Recent large benchmark | On 21 classifiers x 30 binary tasks, Platt and isotonic improve log loss in only ~50% / ~44% of runs; Venn-Abers gave the largest mean log-loss reduction and Beta calibration improved most often. Same group for both papers (Manokhin and Gronhaug), so counted as ONE source | PMLR v329 (COPA 2026); arXiv 2601.19944 |

Rule: fit all four on a held-out *battle-level* split, pick by log loss with a paired bootstrap, and report which won. With millions of rows isotonic is not data-starved, but effective sample size is closer to the number of battles than the number of rows (derived reasoning).

#### 4.5 Why calibration matters for decisions, not just plots

Hu and Wu (FOCS 2024) define the *Calibration Decision Loss*: the largest payoff gain available from recalibrating predictions, over all bounded-payoff downstream decision tasks, and show it can vanish at rate `O(log T / sqrt(T))` online. Plain reading: if `V` is well calibrated, a decision-maker who best-responds to it loses little, uniformly over tasks. That is the theory-level reason to calibrate `V` *before* it feeds the matrix of section 2. (From the abstract; I did not work through the proofs.)

#### 4.6 Conformal prediction: where it helps, where not

- Split conformal gives distribution-free finite-sample coverage under exchangeability (Angelopoulos and Bates, gentle introduction). For a binary outcome the prediction sets are `{win}`, `{loss}` or `{both}`, which is a weak product for a win-probability dashboard.
- **Conformal risk control** (Angelopoulos et al., ICLR 2024) controls the expected value of any monotone loss. Good fit for the coach feature: choose the regret threshold `tau` that flags a "blunder" so that the expected false-flag loss is at most a chosen level (our application; their examples are vision and NLP, not games).
- Exchangeability is violated by rows from the same battle; calibrate on whole battles.

---

### 5. Offline RL, imitation, and bounded-rational opponents

#### 5.1 Opponent action model as a quantal-response (conditional-logit) policy

Quantal response equilibrium (McKelvey and Palfrey 1995): players choose actions with probability increasing in expected payoff, commonly the logit form `q(b) = exp(lambda * u(b)) / sum_b' exp(lambda * u(b'))`; `lambda=0` is uniform, `lambda -> infinity` approaches Nash. Wright and Leyton-Brown (Games and Economic Behavior 2017) meta-analysed 10 human-subject datasets and found Nash often describes human play poorly; the QLk model had the best out-of-sample prediction among five behavioural models (QRE, level-k, cognitive hierarchy, QLk, noisy introspection).

**Build:** score each legal opponent action with a utility `u(b | s, theta)` (features: expected damage dealt, damage taken, switch-in matchup, Tera/no-Tera, is-it-a-predictable-set-up-move) and fit the weights and `lambda` by maximum likelihood on high-Elo replay decisions. This is a conditional-logit classifier trained with log loss and gradient descent (the classic loop), and it handles the variable number of legal actions that a fixed softmax head does not. Evaluate with NLL, top-1 and top-3 accuracy against "uniform over legal actions" (current v1) and a GBDT ranker. Maia (McIlroy-Young et al., KDD 2020) is the chess precedent: engines predict human moves poorly, models trained on human games predict them better and can be conditioned on skill; condition on rating here.

#### 5.2 Human-regularised decision (piKL-style, stretch)

Jacob et al. (ICML 2022): regularise search toward an imitation-learned policy `tau`; this improves human-move prediction in chess and Go and play over imitation alone. For one decision step the KL-regularised best response has the closed form (our algebra) `pi(a) proportional to tau(a) * exp(Q(a) / lambda)`: a "human-like but better" move suggestion and a natural coach baseline.

#### 5.3 Offline RL and sequence models (what exists, why not to retrain)

- **Metamon (Grigsby et al., RLC 2025):** offline actor-critic on AMAGO, with 15M / 50M / 200M-parameter transformers, ~475k human battles (~950k POV trajectories, ~38M timesteps) from Gens 1-4 plus self-play; imitation, then offline RL, then self-play fine-tuning. Reports GXE 79.9% (Glicko-1 1761 +/- 35 over 613 battles) in Gen 1 OU and "top 10% of active players"; beats PokeLLMon (GPT-4o) and draws/beats Foul Play in its test (300 battles per gen).
- **Decision Transformer** (Chen et al., NeurIPS 2021) recasts RL as return-conditioned sequence modelling. Paster, McIlraith and Ba (NeurIPS 2022) show that conditioning on the return fails in stochastic environments because a high-return trajectory may just have been lucky. Pokemon (crits, rolls, accuracy) is exactly that case. Metamon uses a TD-trained critic instead.
- **Conservative Q-learning** (Kumar et al., 2020) addresses the over-estimation of out-of-dataset actions in offline value learning; relevant background, venue not confirmed in my fetch.
- **Use, don't retrain:** the PokeAgent organisers released 30 Metamon checkpoints (compact RNNs to 200M transformers); use them as sparring partners and as an external baseline for your Elo/GXE curve. Licence and download terms must be checked by the data agent (Nate's CC BY-NC claim is unverified).

#### 5.4 Pokemon prior art in one table

| System | Method | Reported | Source quality |
|---|---|---|---|
| PokeChamp (Karten, Nguyen, Jin; ICML 2025) | Minimax; LLM for action sampling, opponent modelling and leaf value; Gen 9 OU | 76% vs PokeLLMon (GPT-4o), 84% vs strongest rule-based bot; 64% for an 8B Llama; projected ladder Elo 1300-1500 (a projection, not a measured rating); ~1/3 of ladder games lost to the turn timer; static opponent model exploited by humans | KEEP (ICML + PMLR page + used as a baseline by PokeAgent) |
| Metamon (Grigsby et al., RLC 2025) | Offline RL + transformers (above) | GXE 79.9% Gen 1 OU, top 10% | KEEP |
| PokeAgent Challenge (NeurIPS 2025 competition; arXiv 2603.15563) | 100+ teams; baselines: PokeChamp-based LLM harness, Metamon RL, heuristics; ratings: Full-History Bradley-Terry, Glicko-1, GXE | Gen 1 OU winner PA-Agent (Metamon-based, no search, iterative offline RL, 6 rounds, human data share 100% to 10%) beat 4thLesson 50-28; Gen 9 OU winner FoulPlay (MCTS) beat Q 50-14; all top participants used RL or search; LLM agents underperformed mostly from time pressure; 13 of 16 qualifiers extended public RL baselines | KEEP for qualitative claims; individual team numbers are single-source (this paper) |
| Foul Play (pmariglia) | poke-engine Rust; MCTS with DUCT; set sampling from usage stats | Per PokeAgent: >90% GXE Gen 9 random battles (peak 2341), >80% GXE Gen 9 OU (peak 1879) | WEAK for the numbers (self-reported inside one paper); the repo README is sparse and does not name the algorithm |
| PokeLLMon (Hu, Huang, Liu, 2024) | GPT-4 agent with in-context RL, knowledge-augmented generation, consistent action generation | 49% ladder, 56% invited battles | WEAK (arXiv only, no venue) |

---

### 6. Evaluation that a quant judge will respect

- **Ratings.** PokeAgent compared Bradley-Terry, Elo, Glicko-1 and GXE on 1.6M+ matches: top-3 rankings agree with 250+ games each, ranks 4+ disagree systematically, Elo diverges from BT even with non-overlapping error bars, and Glicko-1 is the best online/convergence trade-off. They note most LLM arenas report BT without uncertainty. So: report Glicko-1 or FH-BT with intervals, plus GXE (expected win probability against a random opponent).
- **A/B tests of bot variants.** For a win-rate difference `delta` between two arms at `p ~ 0.5`, `alpha = 0.05`, power 0.8: `n ~ 2 (z_{0.975} + z_{0.8})^2 p(1-p) / delta^2 = 1568` games per arm for `delta = 0.05`; against a fixed opponent testing `p > 0.5`, `n ~ 784`. (Our arithmetic from the standard two-proportion formula.) At a few seconds per turn on a local server this is feasible only if turns are fast, so budget the games before promising a number. Use a sequential probability ratio test to stop early (classical, Wald; not re-opened in this pass).
- **Prediction quality.** Brier, log loss, reliability diagram, smooth calibration error, all with bootstrap-by-battle intervals; skill score versus the heuristic baseline. Report on the time-split test set and on Smogtours.
- **Decision quality without games.** Exploitability of the played strategy over recorded matrices (section 2.2), and regret of the replay's played moves under the model (section 8).

---

### 7. Why the "obvious big" methods lose the ranking

| Option | Expected gain | Feasibility in 20 h | Verdict |
|---|---|---|---|
| Offline RL transformer from scratch | High ceiling (top 10% of ladder) | No: 15-200M params, ~38M timesteps, GPU days | Use released checkpoints instead |
| LLM minimax (PokeChamp style) | Medium | Latency: ~1/3 of ladder games lost to the clock | No |
| CFR / ReBeL / SoG on Pokemon | Theoretically best | No implementation found; research-scale compute | No |
| ISMCTS / RM-selector MCTS | Medium | Needs Rust changes to poke-engine; 6-10 h | Stretch |
| **LP on the turn matrix + calibrated GBDT leaf value + Bayesian belief** | Med-High | 12-18 h | **Build** |

---

### 8. Coach-style replay review (the optional feature, from the same maths)

For each turn `t` of a past game: compute `A_t` under the belief at that time, `v_t* = value(A_t)` and our Nash strategy `x_t*`. For the played action `a`, ex-ante regret `r_t = v_t* - min_j A_t[a, j]` (worst-case) or `v_t* - A_t[a,:] q_t` (versus the opponent model); report in calibrated win-probability points, so "this switch cost you 11 points of win probability" is a calibrated statement. Flag blunders with a threshold chosen by conformal risk control (section 4.6). Narrate from the matrix: the best alternative, the opponent move it was strong against, the move that punished the choice. Ex-post hindsight (the opponent's actual move) should be shown separately from ex-ante regret so luck is not blamed on the player. ElevenLabs voice remains an optional add-on, outside this research.

---

### 9. Improvements per layer (tied to the current design drafts)

All items are proposals for the team; per CLAUDE.md section 2 they are the user's calls where they touch data, contracts or dependencies.

#### 9.1 Data layer (`design/data-layer.md`)

| Planned | Improvement |
|---|---|
| Sources: Metamon raw replays, replay API, ladder snapshots, Smogtours, chaos JSON | Keep. Add a **per-turn feature table** (one row per turn, labelled with the final winner) built once from the logs; this is the training set for the value model (data-layer 5b) |
| 5a set candidates + priors (top 20-50) | Store **counts, not just weights**, so the Dirichlet prior strength `n0` is explicit; store the "other" bucket mass; keep teammate correlations as pairwise priors |
| 5b training sets | Make the **split rules part of the contract**: by battle id, then by upload month, plus Smogtours as the OOD test; never random rows. Store rating fields on every row (also a model feature) |
| Eval split Smogtours | Keep; also hold out a **belief test set**: turns where a hidden fact is revealed (section 3.3) |
| Storage: ClickHouse proposed, 🟠 open | Research did not test storage. The need is scans over millions of per-turn rows and grouped splits; any columnar store (Parquet files read with DuckDB/pandas) satisfies it with no service to run. Your call |
| Bot filtering 🟠 open | No source found for bot detection; keep it an open decision, and record the rating and source of each replay so a filter can be applied later |
| Ratings (data-layer 2) | The ladder only gives the top 500; use start Elo from the log as the rating feature, and compute your own Glicko/BT for bot evaluation (section 6) |

#### 9.2 Decision layer (`design/decision-layer.md`)

| Planned | Improvement |
|---|---|
| Loop: score = sum over opp policy x sampled sets, then argmax | Keep the matrix `A`; **replace argmax with the LP or the blend LP** (2.2, 2.3). It resolves the open decision "how to choose under simultaneous moves" without changing interfaces, which is what the doc's recommendation already anticipates (keep the full matrix so C can be added) |
| Belief: hard filter, then soft Bayes later | Implement the likelihood table in 3.1 on the **full weighted list**, with ESS, `eps`-noisy speed evidence, tempered action evidence, and common random numbers when sampling `k=5` |
| Opp policy: uniform over legal actions, later trained on high-Elo replays | Go straight to a **conditional-logit/QRE policy** (5.1), conditioned on rating; keep uniform as the ablation baseline |
| Value: HP + Pokemon remaining, later trained win probability | Train the **calibrated GBDT** (section 4) and make it `value(state)`. Keep the heuristic as the baseline model in the evaluation harness |
| Cost per turn ~850 simulate calls; 🟠 pruning | Delete strictly dominated rows and columns of `A` before the LP (free); prune by the opponent model's top-n once it is trained, as the doc suggests |
| Selector tie-break on worst case | The LP value `v*` and exploitability replace the ad-hoc tie-break |
| Special cases: Tera is a variant of each move; forced switch has no opponent action | Matrix doubles columns/rows for Tera variants; forced switch collapses to a one-sided choice (maximise over our row values against the belief) |

#### 9.3 Bot layer (`design/bot-layer.md`)

| Planned | Improvement |
|---|---|
| `BattleState` + `Choice` contract | Add to `BattleState`: the **per-turn event list** (move order, integer HP percentages, `[from]` tags), both ratings, turn number, Tera availability, and the opponent's **action history**; the belief and policy models need events, not only snapshots (this is the decision doc's Q7 and the research agrees: speed and damage evidence only exist in this turn's lines) |
| Output `Choice` | Return `Choice` **plus diagnostics**: calibrated win probability, the matrix, our mixed strategy, posterior top-k. Log every decision. This feeds the evaluation harness, the coach feature, and future training data |
| Stochastic play | The LP gives a probability vector; the bot must **sample** from it, not take argmax (mixing is the point) |
| Time | Fix a per-turn budget early (decision doc 🟠 open). PokeChamp lost ~1/3 of ladder games on time; PokeAgent says LLM agents lose to time pressure. A GBDT + LP loop is milliseconds; spend the budget on simulation count |
| Format 🟠 | Research does not decide this; note that the published bots are strongest on Gen 1 OU (Metamon, PA-Agent) and Gen 9 (Foul Play), and random-battle results are separate |
| Local server / ladder 🟠 | Use local games for the A/B counts in section 6; the ladder adds rate limits and rule constraints (bot-layer 4) |

---

### 10. Community consensus (Reddit / HN / StackExchange / Smogon)

Honest result: several targeted searches (HN, Reddit, StackExchange, Smogon forums) returned **no on-topic threads** that the search tool surfaced, and none that I could open and quote. What I can say:

- **Competitive community (the strongest community signal found):** the PokeAgent Challenge had 100+ teams and 650+ researchers on its Discord; **13 of 16 qualifiers extended the public Metamon RL baselines**, the Gen 9 OU winner was the MCTS bot Foul Play, and the RL/search entrants beat the LLM entrants. Consensus in practice: search with a sampled-set belief (Gen 9) or history-conditioned offline RL (Gen 1), not pure LLM play.
- **Smogon/Showdown policy:** per search result, Smogon states bots are inevitable and prefers to work with bot developers (page not opened in full; WEAK).
- **Practitioner write-ups on calibration:** consistent with the papers (isotonic overfits small calibration sets; Platt/isotonic can fail on strong models) but they are blogs (metricgate, Substack): WEAK, not used for any claim.
- **Final call (professional + community):** both point the same way: calibrated tabular value model, explicit hidden-information belief, a simultaneous-move-aware decision rule, and honest ratings with uncertainty; avoid LLM-in-the-loop and from-scratch deep RL for a 25-hour build. Where the two disagree there is nothing to resolve: no community source contradicted a professional one.

---

## SOURCE LEDGER

Year tags: [in-window] = Oct 2023 or later (3 years); [edge] = 2023 but earlier than Oct; [older] = foundational, kept because recent equivalents do not exist for that specific result. Game-solving theory in the 3-year window is thin for this application, so the window was extended (protocol allows 3-4 years when scarce) and foundational papers are labelled.

### KEEP

| # | Source | Venue / year | Supports | Corroboration |
|---|---|---|---|---|
| K1 | Karten, Nguyen, Jin. PokeChamp: an Expert-level Minimax Language Agent [in-window] | ICML 2025 (PMLR v267) | LLM minimax numbers; timeouts and static-opponent limits | arXiv HTML + PMLR page + used as baseline in K3 |
| K2 | Grigsby, Xie, Sasek, Zheng, Zhu (UT Austin). Human-Level Competitive Pokemon via Scalable Offline RL with Transformers [in-window] | RLC 2025 (per arXiv comments field) | Offline actor-critic; 475k battles; GXE 79.9%, top 10%; compared to Foul Play, PokeLLMon | K3 (baselines, 13/16 qualifiers) |
| K3 | The PokeAgent Challenge: Competitive and Long-Context Learning at Scale (arXiv 2603.15563; NeurIPS 2025 competition) [in-window] | NeurIPS 2025 competition track; arXiv 2026 | Winners, baselines, rating methodology, LLM time-out finding | NeurIPS competition page + K1/K2 as baselines |
| K4 | Grinsztajn, Oyallon, Varoquaux. Why do tree-based models still outperform deep learning on typical tabular data? [older, 2022] | NeurIPS 2022 D&B | GBDT strong at ~10k samples | K5, K6 |
| K5 | McElfresh et al. When Do Neural Nets Outperform Boosted Trees on Tabular Data? [in-window] | NeurIPS 2023 D&B | NN-vs-GBDT overemphasised; TabPFN exception at ~3,000 points | K4, K6 |
| K6 | Erickson et al. TabArena [in-window] | NeurIPS 2025 D&B | Trees strong; NN catch up with ensembling; foundation models win small data | K4, K5 |
| K7 | Hollmann et al. Accurate predictions on small data with a tabular foundation model (TabPFN) [in-window] | Nature 2025 | Up to 10k samples; 2.8 s vs 4 h tuned ensemble | K5 (TabPFN result), K6 |
| K8 | Niculescu-Mizil, Caruana. Predicting Good Probabilities with Supervised Learning [older, 2005] | ICML 2005 (full PDF text read) | Boosted trees' sigmoid distortion; Platt vs isotonic data needs (200-1000) | K9, K10 |
| K9 | Guo, Pleiss, Sun, Weinberger. On Calibration of Modern Neural Networks [older] | ICML 2017 | Nets miscalibrated; temperature scaling | K8 |
| K10 | Kull, Silva Filho, Flach. Beta calibration [older] | AISTATS 2017 | Logistic family excludes identity; beta alternative | K8, K13 |
| K11 | Gneiting, Raftery. Strictly Proper Scoring Rules, Prediction, and Estimation [older] | JASA 2007 (full text read) | Proper scores; Brier (Brier 1950 lineage) | Gneiting et al. JRSS-B 2007 (K12) |
| K12 | Gneiting, Balabdaoui, Raftery. Probabilistic forecasts, calibration and sharpness [older] | JRSS-B 2007 | Maximise sharpness subject to calibration | K11 |
| K13 | Vovk, Petej. Venn-Abers predictors [older] | UAI 2014 | Calibration guarantee under i.i.d.; interval output | W2 (benchmark) |
| K14 | Blasiok, Gopalan, Hu, Nakkiran. A Unifying Theory of Distance from Calibration [edge] | STOC 2023 | ECE discontinuous; smooth/interval calibration | K15 |
| K15 | Hu, Wu. Calibration Error for Decision Making (formerly Predict to Minimize Swap Regret for All Payoff-Bounded Tasks) [in-window] | FOCS 2024 | Calibration Decision Loss; O(log T/sqrt T) | K14 (calibration measures) |
| K16 | Angelopoulos, Bates, Fisch, Lei, Schuster. Conformal Risk Control [in-window] | ICLR 2024 spotlight | Controls expected monotone loss | K17 |
| K17 | Angelopoulos, Bates. Gentle introduction to conformal prediction [older, arXiv monograph, Berkeley] | arXiv 2107.07511 | Distribution-free coverage, any model | K16 |
| K18 | Lisy, Kovarik, Lanctot, Bosansky. Convergence of MCTS in Simultaneous Move Games [older] | NeurIPS 2013 (ar5iv text read) | Hannan-consistent selection converges to approx Nash; RM formula; UCB caveat | K19 |
| K19 | Shafiei, Sturtevant, Schaeffer. Comparing UCT versus CFR in Simultaneous Games [older] | IJCAI GIGA workshop 2009 | UCT does not converge to Nash in general; exploitable | K18 |
| K20 | Cowling, Powley, Whitehouse. Information Set Monte Carlo Tree Search [older] | IEEE TCIAIG 2012 (full text read) | ISMCTS; Exp3 at simultaneous nodes; MCTS often fails to find Nash | K21 |
| K21 | Long, Sturtevant, Buro, Furtak. Understanding the Success of PIMC Sampling [older] | AAAI 2010 (full text read) | Strategy fusion; when PIMC works | K20 |
| K22 | Sokota et al. A Unified Approach to RL, QRE, and Two-Player Zero-Sum Games (MMD) [edge] | ICLR 2023 (PDF text read) | MMD update; QRE convergence; 4x4-50x50 matrix tests | Sokota ICLR page + NeurIPS 2022 workshop version |
| K23 | Farina, Grand-Clement, Kroer, Lee, Luo. Regret Matching+: (In)Stability and Fast Convergence in Games [in-window] | NeurIPS 2023 spotlight | RM+ instability and fixes | NeurIPS page + author pages (abstract level) |
| K24 | Lanctot, Waugh, Zinkevich, Bowling. Monte Carlo Sampling for Regret Minimization in Extensive Games [older] | NIPS 2009 | MCCFR | NeurIPS page + Pluribus (K25) |
| K25 | Brown, Sandholm. Superhuman AI for multiplayer poker (Pluribus) [older] | Science 2019 (full text read) | MCCFR blueprint, 12,400 core-hours | K24 |
| K26 | Brown, Bakhtin, Lerer, Gong. ReBeL [older] | NeurIPS 2020 | Nash convergence in 2p0s; AlphaZero-like in perfect info | proceedings + arXiv |
| K27 | Schmid et al. Student of Games [edge] | Science Advances 2023 | Sound unified algorithm | arXiv + journal |
| K28 | Perolat et al. DeepNash [older] | Science 2022 | R-NaD; Gravon top 3 | arXiv + DeepMind blog (84%) |
| K29 | von Stengel. Zero-Sum Games and LP Duality [in-window] | Math. of Operations Research 2022 | Minimax theorem from LP duality | MIT 6.S890 lecture 3 (LP formulation, full PDF read) |
| K30 | McKelvey, Palfrey. Quantal Response Equilibria for Normal Form Games [older] | Games and Economic Behavior 1995 | Logit QRE | K31, K22 |
| K31 | Wright, Leyton-Brown. Predicting Human Behavior in Unrepeated, Simultaneous-Move Games [older] | Games and Economic Behavior 2017 | QLk best out-of-sample; Nash poor | K30 |
| K32 | Jacob, Wu, Farina, Brown et al. Modeling Strong and Human-Like Gameplay with KL-Regularized Search (piKL) [older] | ICML 2022 | Regularise search toward human policy | arXiv + ICML page |
| K33 | McIlroy-Young, Sen, Kleinberg, Anderson. Aligning Superhuman AI with Human Behavior (Maia) [older] | KDD 2020 | Human-move prediction needs human-trained models | MSR page + arXiv |
| K34 | Southey et al. Bayes' Bluff: Opponent Modelling in Poker [older] | UAI 2005 | Dirichlet posterior over opponent strategy | Ganzfried-Sun (W3) |
| K35 | Nashed, Zilberstein. A Survey of Opponent Modeling in Adversarial Domains [older, 2022] | JAIR 73 (2022) | Opponent modelling taxonomy | JAIR + DOI |
| K36 | Chen et al. Decision Transformer [older] | NeurIPS 2021 | Return-conditioned sequence modelling | proceedings |
| K37 | Paster, McIlraith, Ba. You Can't Count on Luck [older] | NeurIPS 2022 | DT/RvS fail in stochastic envs | proceedings + arXiv |
| K38 | Danihelka et al. Policy improvement by planning with Gumbel [older] | ICLR 2022 | Few-simulation planning (background for stretch search work, not used in the plan) | ICLR page |
| K39 | Antonoglou et al. Stochastic MuZero [older] | ICLR 2022 | Planning with afterstates in stochastic envs (background only) | ICLR page |

### WEAK

| # | Source | Why weak | What it was used for |
|---|---|---|---|
| W1 | Foul Play repo (pmariglia/foul-play) and poke-engine README | README is sparse: does not name the search algorithm or the belief method | Existence, language (Rust), expectiminimax / iterative deepening / MCTS options. Algorithm and numbers come from K3 only (single source) |
| W2 | Manokhin, Gronhaug. When Post-Hoc Calibration Hurts (PMLR v329, COPA 2026) and Classifier Calibration at Scale (arXiv 2601.19944) | One research group for both; practitioner-leaning; but a peer-reviewed symposium, large benchmark (21 classifiers, 30 tasks, 3,150 runs per calibrator) | Evidence that Platt/isotonic can hurt and Venn-Abers/Beta often help; counted as one source, partly corroborated by K8, K10, K13 |
| W3 | Ganzfried, Sun. Bayesian Opponent Exploitation in Imperfect-Information Games | arXiv only (v6, 2018), venue not verified | Dirichlet posterior, exact algorithm; supported by K34 |
| W4 | Hu, Huang, Liu. PokeLLMon | arXiv only, no venue | 49% / 56% numbers; superseded as baseline by K1 |
| W5 | Radboud BSc thesis, "Nash equilibrium estimation in competitive Pokemon using search and supervised learning" (2022) | Could not be opened (403 / host not found); only search-result summary; BSc level | Pointer only: reports 0.295 win rate vs an expectiminimax heuristic and attributes the shortfall to evaluation accuracy. Do not cite numbers without opening it |
| W6 | Kumar et al. Conservative Q-Learning (arXiv 2006.04779) | The page opened does not name a venue | Background on offline-RL over-estimation |
| W7 | Erdos Institute Pokemon battle project (2024); Firefox "Pokemon Battle Predictor" extension | Student/hobby projects; no calibration metrics reported | Only to show that no calibrated Pokemon win-probability benchmark was found |
| W8 | Hodge et al. Win Prediction in Multi-Player Esports (IEEE Trans. Games) | Peripheral domain (Dota 2); year differs across sources | Not used for any claim |
| W9 | McGuffey, Columbia article on Pokemon game theory (2017); Smogon bot-policy forum post; metricgate / Substack calibration blogs | Not opened (search summaries) or blogs | Not used for claims |

### DO NOT USE (refuted or unsupported; metrics stripped)

| Claim | Why dropped | Refuting sources |
|---|---|---|
| "UCB / UCT-style DUCT converges to a Nash equilibrium in simultaneous-move games, so it is a safe equilibrium solver" | Tombstone: UCT does not converge to Nash in general and can be exploited; only Hannan-consistent selectors (regret matching, Exp3) carry the guarantee. Foul Play's strength is empirical, not guaranteed | K19 Shafiei et al. 2009; K18 Lisy et al. 2013 |
| "Expected Calibration Error (or accuracy) is a sufficient headline for win-probability quality" | Tombstone: ECE is not continuous and can mislead; use proper scores plus smooth calibration and decision-relevant loss | K14 Blasiok et al. STOC 2023; K15 Hu and Wu FOCS 2024; K11 (proper scores) |
| "Return-conditioned Decision Transformer will give a reliable Pokemon policy" | Tombstone: fails in stochastic environments; Metamon uses a TD critic instead | K37 Paster et al. NeurIPS 2022; K2 Metamon design |
| "LLM-in-the-loop bots are competitive with RL/search bots under real clocks" | Tombstone: ~1/3 of PokeChamp ladder games lost to the timer; LLM entrants underperformed because of time pressure; all top PokeAgent participants used RL or search | K1 PokeChamp limitations; K3 PokeAgent |
| "Over 80% accuracy" for the Firefox Pokemon Battle Predictor extension | Tombstone: marketing claim with no methodology; do not use as a benchmark | W7 itself (no method given); K11 and section 4.3 (accuracy is the wrong metric) |
| "Isotonic regression is always the best calibrator when data is plentiful" | Tombstone: on a 21-model, 30-task benchmark isotonic improved log loss in only ~44% of runs and worsened it on average | W2 (one group) with K8 (isotonic overfits) and K10 (calibrator choice must be checked) |

---

# Pass 2, elo_datasets_skill (source: `research_notes/elo-skill-estimation/elo_datasets_skill.md`)

## Elo datasets + skill-from-decisions: research note (2026-10-24)

Scope: (1) datasets of Showdown replays with ratings at all skill levels, (2) getting top-~500 ladder players' replays legitimately, (3) estimating a player's skill from decisions. Plus verification of teammates' claims (research-inputs.md section G).
"Measured" = we downloaded the data and computed it ourselves today (reproducible; scripts not shipped). Everything else was opened and read on the page cited.

---

### 0. RECOMMENDATION (read this first)

**Data.** Use **`HolidayOugi/pokemon-showdown-replays`** (HF) as the main source, with **Metamon raw** as the cross-check.
- HolidayOugi: 34,325,933 replays, 47 formats, `[Gen 9] OU` = 2,506,142 replays (13 parquet parts, ~6.1 GB). **Usernames are raw (not pseudonymised)**, so you can join them to ladder names. Card dated 5 Oct 2026. No licence stated.
- Metamon raw (`jakegrigsby/metamon-raw-replays`): 2,681,841 rows, 5.7 GB, gen9ou-dominant, pseudonymised names. Cleaner provenance and a fixed cutoff (2026-05-19), but you cannot link a name to the ladder.
- Both cover **all skill levels** (measured: ratings 1000 to ~2100, median ~1250-1310; see 1.4).

**Label.** Do NOT use the row-level `rating` column as a player label. Use the **per-player pre-game Elo in the log's `|player|p1|name|avatar|ELO` line** (present in ~96-98% of ladder logs, measured). The row `rating` is a single number per game that equals the **lower player's post-game rating** (measured exactly, see 1.3).

**Top-500 players.** Cheapest legitimate route: take the 500 names from `pokemonshowdown.com/ladder/gen9ou.json` (one request), then filter HolidayOugi offline by name. Top up with `replay.pokemonshowdown.com/search.json?user=<name>&format=gen9ou` (51 rows/page) only for gaps. Showdown publishes no crawl rule or rate limit; be polite (about 1 request/s, cache, identify yourself).

**Skill model.** Skill-conditioned human-policy likelihood (Maia-2 idea ported to Pokemon) plus decision-regret features, aggregated per player with a Bayesian/Gaussian posterior and **conformal (CQR) intervals**. Baselines: global mean; team-only model; length/outcome-only model; Showdown's own Elo shown in log (as an oracle upper bound, not a feature).

**Headline numbers to quote for the judges (all verified):** per-game chess MAE of a learned estimator is ~182 Elo (Omori & Tadepalli); Go rank-group accuracy 80% from 10 games for the best method but only ~60-63% for individual players at 15 games (Kuboki et al.); so expect weak per-game skill estimates and honest wide intervals. That is the point: report calibration, not just MAE.

**Licence in one line:** Metamon *parsed* = CC BY-NC 4.0 (fine for a non-commercial hackathon demo with attribution; risky if the team later monetises). Metamon *raw*, PokeChamp and HolidayOugi: **no licence stated** on the cards. Underlying replays are public, user-uploaded Showdown content. Not legal advice.

---

### 1. Datasets (all opened on the HF card / API)

#### 1.1 Comparison

| Dataset | Size (verified) | Formats | Fields | Rating? | Usernames | Licence | Download |
|---|---|---|---|---|---|---|---|
| **HolidayOugi/pokemon-showdown-replays** | 34,325,933 rows, 72.2 GB, 310 files. gen9ou 2,506,142 (card table) | 47 (all gens, OU/UU/VGC/Random...) | id, format, players, log, uploadtime, views, formatid, rating (float, nullable) | `rating` nullable; per-player Elo in log `\|player\|` line (97.6% of 8k sampled gen9ou logs, measured) | **raw** | none stated | `hf download`, one parquet per format/part e.g. `[Gen 9] OU_part1..13.parquet` (~480 MB each) |
| **jakegrigsby/metamon-raw-replays** (v6, 2026-05-19) | 2,681,841 rows, 5.7 GB download / 22.6 GB uncompressed, 46 parquet shards | mostly gen9ou; also gen1-4 OU/NU/UU/Ubers | id, format, players, log, uploadtime, formatid, rating (string) | row `rating` + per-player Elo in log (95.8% of 3,000 sampled) | pseudonymised, consistent across games | none stated | `load_dataset` / parquet shards |
| **jakegrigsby/metamon-parsed-replays** | 28.5 GB tar.gz archives per format | gen1-4 nu/ou/uu/ubers, gen9ou | RL trajectories (states, actions, rewards) | Elo in **filename** | pseudonymised | **CC BY-NC 4.0** | Metamon `ParsedReplayDataset` or tar.gz |
| **milkkarten/pokechamp** (PokeChamp) | 2,130,224 rows (train 1,916,868 + test 213,356), 5.57 GB | 37+ formats, 39 gamemode values | text (log), month_year, gamemode, elo (5 bins), battle_id | **binned** `elo` 1000-1800+ (bin edges not listed in card) | log text | none stated | `load_dataset` / `battle_translate.py load_filtered_dataset` |
| **milkkarten/pokemon-showdown-replays-merged** | 29,057,184 rows, 38.7 GB (merge of sethkarten + metamon + holidayougi) | 18 format values | adds `source`, `turns`; drops games <=4 or >=96 turns | `rating` = "average rating of players (if available)" per card (see 1.3: unverified definition) | raw | none stated | `load_dataset` |

Notes:
- PokeChamp card says "2 million clean battles" but its YAML splits total 2,130,224 (1,916,868 + 213,356). The paper says "over 3 million" battles of which "more than 500,000 high-Elo (>1600)". The public HF set is the cleaned subset.
- No Kaggle dataset found (Kaggle search page returned no readable results; web search found none). Erdos Institute VGC scrape (14,474 battles) is an unpublished class project: WEAK, ignore.
- The Metamon raw README states its purpose is partly "to save the Showdown API some download requests", i.e. the maintainers themselves treat API load as something to minimise.

#### 1.2 Coverage holes and selection (important)
- Metamon card: 2021-2024 replays are sparse (Showdown database failure); surviving ones are mostly tournament/Smogtours. Measured in shard 0 of 46 (58,301 gen9ou rows): upload years 2022: 15, 2023: 1,001, 2024: 23,536, 2025: 25,571, 2026: 8,178. So the hole is not uniform by shard; verify by year on the full set before relying on 2024 balance.
- HolidayOugi part 13 (measured, 106,142 gen9ou rows): 99.4% were uploaded Aug-Oct 2026, i.e. parts are roughly time-ordered, so the full 13 parts give the history.
- **Selection bias:** only replays a player chose to save (or auto-save) are public (Metamon README: players "choose to upload"; Showdown code has `replaySaved`/`autosavereplays` and hidden/private rooms via `setPrivate('hidden')`). Replays are therefore biased to wins, memorable games and players who like saving. Private/hidden battles are excluded. Mitigation: report results by rating band and note the limitation (Section 4).

#### 1.3 What the `rating` column actually is (measured)
- **HolidayOugi gen9ou (part 13):** in 7,758 replays whose log contains both `|raw|NAME's rating: a -> b` lines, row `rating` **equals the lower of the two post-game ratings in 100.0%** of rows (and the higher in 0.5%).
- Example (verified on the live API for `gen9ou-2690692096`): `|player|` lines show 1860 and 1761 pre-game; log end shows 1860 -> 1874 and 1761 -> 1747; replay `rating` = 1747.
- **Metamon raw shard 0:** logs have the `|raw|` rating-change lines stripped (0 of 5,000), so we cannot test exactly. Consistency check on 19,038 rows: `rating - min(pre-game p1,p2)` has median -16, 99.4% within +/-40 (what you expect from a ~16-22 point loss for the lower-rated player), mean |p1+p2|/2 - rating = 26.8. Conclusion: same definition (lower post-game rating), strongly suggested but not directly proved for Metamon.
- Consequence: **`rating` is a game-level, mildly biased proxy, not a per-player label.** It can be 10-25 points below the weaker player's pre-game Elo and is uninformative about the stronger player. For a per-player label use the log's `|player|` Elo (pre-game, available before the first move, so label is not affected by this game's result).
- Pseudonymised Metamon names are consistent, so per-player aggregation works inside Metamon (measured in 20,000 rows of shard 0: 26,459 distinct pseudonyms, max 74 games each; most players appear once per shard, so aggregate across all 46 shards before judging player-level sample sizes).
- Floor: Showdown Elo cannot go below 1000 (ladder help: "If your rating would fall below 1000, it is set to 1000"). Measured: 0.9% of Metamon pre-game ratings equal exactly 1000, 573 of 58,301 `rating` rows are <=1000 in shard 0. Treat as **left-censored** (Tobit) or exclude the lowest bin from MAE.

#### 1.4 Rating distribution (measured; corroborated by the PokeChamp paper)
- Metamon shard 0 (55,496 rated gen9ou rows): mean 1331, median 1313, 25%/75% = 1149/1479, max 2043. Counts per 100-bin: <=1000: 573; 1000-1100: 7,927; 1100-1200: 10,118; 1200-1300: 7,822; 1300-1400: 9,123; 1400-1500: 7,453; 1500-1600: 5,705; 1600-1700: 3,996; 1700-1800: 1,965; >1800: 814.
- HolidayOugi part 13 (102,222 rated): mean 1305, median 1254, min 1000, max 1994; >1800: 1,159.
- PokeChamp paper (Fig. 5): "two primary modes at approximately 1150 and 1350 Elo". Our two samples show a bump ~1100-1200 and another ~1300-1400, consistent.
- Takeaway: ~1.5% of games are >1800, so high-Elo data is thin per shard but huge in absolute terms across the full set (HolidayOugi gen9ou 2.5M; at 1.1% that is ~25-30k).
- Smogtours (tournament) games: `rating` is **null in 100% of 530 smogtours rows** (measured); ladder rows 2.7% null. So tournament games are an eval split with no Elo label, as the team guessed.

---

### 2. Top-500 players and the Showdown endpoints

#### 2.1 Endpoints (all fetched live today)
| Endpoint | What we verified |
|---|---|
| `pokemonshowdown.com/ladder/gen9ou.json` | keys `formatid, format, toplist`. Per row: `userid, username, w, l, t, gxe, r, rd, sigma, rptime, rpr, rprd, rpsigma, elo, first_played, last_played`. Last row of the list: elo 1636.43, gxe 70.2 (tail of a 140,309-char document, about 280 chars/row, consistent with 500 rows; exact count not machine-counted because our shell could not reach this host). Top row elo 1976.99. |
| `pokemonshowdown.com/users/<userid>.json` | keys `username, userid, registertime, group, ratings`; per format `elo, gxe, rpr, rprd, w, l, coil`. Works for any user (not only top 500). So you can pull a known player's rating one request at a time. |
| `pokemonshowdown.com/ladder/gen9ou.json?prefix=zz` | returned an empty `toplist`: a name-prefix filter exists in effect, but it does **not** expose ranks 501-1000 as a list. We found no endpoint for ranks 501+. |
| `replay.pokemonshowdown.com/search.json?format=gen9ou` | JSON array, **51 rows** (50 + 1 to signal a next page); fields `uploadtime, id, format, players[2], rating (int or null), private, password`. |
| `.../search.json?format=gen9ou&sort=rating` | sorted by rating descending (top row 2116). Gives a cheap "highest-rated replays ever" list without names. |
| `.../search.json?user=<name>&format=gen9ou` | every row contains that user: the user filter works. Newest first. |
| `.../search.json?...&before=<uploadtime>` | returned 51 rows all older than the cutoff; works as a cursor, but it is not in the official client code (the client uses `page`). Treat `before` as undocumented. |
| `replay.pokemonshowdown.com/<id>.json` | keys `id, format, players, log, uploadtime, views, formatid, rating, private, password`. Log has real names and `|player|` lines with Elo, and the final rating changes. |
| Client source (`replays-index.tsx`) | search uses `/api/replays/search` with `username`, `format`, `page`, `sort=rating`; "sort by rating only when a format is set and no user"; 50 shown/51 fetched. |

#### 2.2 Ladder facts that matter for labels (ladder help page, read verbatim)
- Elo starts at 1000, K = 50 (1100-1299), K = 40 (>=1300), K scales linearly 1000-1100, **floor 1000**.
- Daily decay above 1400 (>5 games in the period: no decay; 1-5 games: lose 1 per 100 over 1500; 0 games: 1 per 50 over 1400). **This corrects research-inputs line 89**, which says "1 point/day + 1 per 50 over 1400" (that is only the 0-games case).
- GXE = "estimate of your win chance against an average ladder player", built on Glicko-1 (start 1500, RD 130, RD range 25-130, 24 h rating period).
- Smogon's "Elo Hell-o" (The Smog issue 43): "inherent randomness" makes any rating uncertain; Glicko updates only after two days or fifteen battles; GXE is the preferred skill estimate.
- Smogon forum (Aug 2025, rejected proposal): Doubles OU players matched against +300-400 Elo opponents; the reply consensus was that GXE is not biased by such losses, but win-loss ratio is a weak skill stat. So `elo` is progression-oriented and path-dependent; **GXE or Glicko `r`/`rpr` with `rd` is the better skill target for players with many games.**

#### 2.3 Terms, bots and rate limits
- `pokemonshowdown.com/rules` and `/privacy`: **no statement on scraping, bots, APIs or rate limits**; the privacy policy only says Showdown "reserve[s] the right to keep text logs of all chatting in chat rooms, battles, and private messages" and shares no analytics data. So: **no explicit permission and no explicit prohibition found**.
- Smogon "Initial policy on bots" (Django, 9 Oct 2026; registry update 12 Oct): unregistered **bots that play** are "a bannable offense" (enforcement undecided); bots must register via `/ht` in chat; **AI assistance in tournaments is ghosting and gets an immediate ban**; battles against bots do not affect humans' ratings. The thread does not mention scraping, APIs or rate limits. Implication for the team: reading public replays is not what the policy targets; **do not log in a bot or use the model as live assistance in a ladder/tour**, and don't claim it as a play-assist for tours.
- No official rate limit is documented (we did not test throttling). The conservative plan: one request at a time, ~1 req/s, exponential back-off on non-200, local cache keyed by replay id, a descriptive User-Agent. Prefer offline filtering of HolidayOugi/Metamon.
- Feasibility in ~3 hours: offline join of the 500 ladder names against HolidayOugi gen9ou parts needs one ladder request plus ~6 GB of downloads (HF files, not Showdown). Spot check: of 5 top-ladder userids tested against just one of the 13 gen9ou parts (part 13, 106k replays), 3 appeared (c0ldsn0w 112 games, relicstone 14, fadingstrawberry 13). Full coverage across all 13 parts is likely higher but unmeasured. API top-up for 500 players x 2-3 pages = ~1,500 requests at 1 req/s = ~25 minutes.
- Ranks 501-1000 are not available from any endpoint we found; they can only come from repeated top-500 snapshots (names drift in and out) or from names harvested from high-rated replays plus `/users/<id>.json`. Start the snapshotter now; it cannot be back-filled.

---

### 3. Estimating skill from decisions: methods and evidence

#### 3.1 What the literature says (verified)

1. **Move-quality ratings (centipawn-loss analogue).** Regan & Haworth, *Intrinsic Chess Ratings*, AAAI-11 (2011): two parameters (sensitivity s, consistency c) fitted to engine evaluations map smoothly to Elo; claim also applies to "other rational-choice settings where options have well-defined utilities". Di Fatta, Haworth & Regan, *Skill Rating by Bayesian Inference*, IEEE CIDM 2009 (existence confirmed by four listings; abstract not opened). Both are old (13-17 yrs; scarce for this exact idea, so extended). **Pokemon analogue:** regret of the chosen action against a solver/expectimax value, which our decision layer already needs.
2. **Learned skill-conditioned human policy.** McIlroy-Young et al., *Aligning Superhuman AI with Human Behavior* (KDD 2020, Maia): policies trained per rating band predict human moves better than engines. Tang et al., *Maia-2* (NeurIPS 2024): one model with **skill-aware attention**, rating bins as categorical embeddings (128-d), trained on 169M games; top-1 move matching 53.25% vs 51.39% for the best Maia-1 and ~44% for Leela; changing own skill alters the predicted move up to 22% of the time. **Maia-2 does not predict ratings** (it consumes them); using it for skill estimation by maximum likelihood over skill bins is *our* inference, not a result of the paper. Limits stated by the authors: no search, strongest players in one bucket, no error bars.
3. **Direct rating regression from games.** Omori & Tadepalli (CG 2024 / arXiv 2409.11506): CNN+BiLSTM on moves and clock times, >1M Lichess games, **MAE 182 Elo** per game. Clock times helped (Pokemon analogue: none exists; the turn timer is not in replay logs except implicitly).
4. **Multi-game strength estimation (the closest to our need).** Chen, Shih, Wu, *Strength Estimation and Human-Like Strength Adjustment in Games* (ICLR 2025): Bradley-Terry strength score per state-move pair; Go >80% rank-group accuracy from 15 games vs 49% for the earlier method at 100 games. Kuboki et al. (arXiv 2505.00279, May 2025, preprint): adds policies at 10 skill levels (KataGo HumanSL, Maia-1100..1900) + score-loss statistics + LightGBM: Go 80% at 10 games (vs 71%), 92% at 20 games (vs 84%); chess 86.2% at 20 games. **Individual-player test (100 players x 20 games): 60.4% chess, 63.2% Go at 15 games, and the authors say it was "lower than randomly sampling from the same rank group"**, and that loss features "contributed quite limited". This is the sample-size evidence: per-player estimates are far harder than per-game-pool estimates.
5. **Style/identity embeddings.** McIlroy-Young et al., behavioral stylometry (NeurIPS 2021): 98% identification among thousands of players with 100 games. Embeddings carry identity as well as skill: a player-embedding will leak identity, so use grouped splits.
6. **Bayesian rating from outcomes.** Glickman (1999, JRSS-C 48(3), 377-394) Glicko; Herbrich, Minka, Graepel, TrueSkill (NeurIPS 2006). Old but foundational; Showdown *is* Glicko-1/Elo, so these give the outcome-only baseline. PokeAgent Challenge (NeurIPS 2025 Competition Track, arXiv 2603.15563): calls Showdown's Elo "too noisy for our purposes", fits Bradley-Terry with bootstrapped uncertainty above **250 battles**, and found Elo diverging from BT "even when error bars did not overlap".
7. **Item response theory.** Used in the chess skill literature (Haworth/Regan line) and in education; we found **no peer-reviewed Pokemon/IRT or esports-IRT paper**. Treat IRT as a modelling choice (positions as items, ability theta) not as validated for Showdown: WEAK for this domain.
8. **Calibrated intervals.** Romano, Patterson, Candes, *Conformalized Quantile Regression* (NeurIPS 2019) and Angelopoulos & Bates, *Gentle Introduction to Conformal Prediction* (arXiv 2107.07511, v6 2022): finite-sample coverage, distribution-free, wraps any model. Fast to implement (split-conformal on a held-out calibration set).
9. **No published paper estimates Pokemon player rating from decisions.** Searches (web, extended) returned only PokeChamp, Metamon, PokeAgent and Smogon community tools (win-probability predictor, replay analyser). This is a genuine gap: one fair framing for judges is "first calibrated skill estimator on Showdown logs" but state it as "we found none", not as proven novelty.

#### 3.2 Sample size per player (what the evidence supports)
- Outcome-only: Bradley-Terry needs ~250 games for stable ordering (PokeAgent); Showdown's own Glicko RD floor is 25 (ladder help).
- Decision-based, other games: ~10-20 games for 80-92% rank-group accuracy *when pooled across many players*; ~15 games gives only ~60% for individual players (Kuboki).
- Our plan: report accuracy-vs-n-games curves for n = 1, 5, 15, 30, 100; the knee is the real finding.

---

### 4. Recommended pipeline, metrics, baselines, pitfalls

#### 4.1 Pipeline
1. **Filter** gen9ou ladder replays (not Smogtours: no rating), both players have `|player|` Elo, 6 <= turns.
2. **Labels:** per-player pre-game Elo from the log. Optional second target: GXE/Glicko `r` from `/users/<id>.json` (needs names; raw dataset only).
3. **Split:** by **player** (hold out entire players), then by **time** (train on older months, test on newest). For the top-500 test: hold out all of the 500 names, train on the rest.
4. **Features per game and side:** (a) regret of chosen move/switch vs the decision-layer value function (the same win-probability model the product uses); (b) match rate to a skill-conditioned policy at each band; (c) behaviour stats (switch rate, hazard use timing, over-prediction of switches, forfeits/timeouts).
   **Exclude** team-composition features from the main model, or train a separate "team-only" model for the baseline (see pitfalls).
5. **Game-level model:** gradient boosting or small transformer -> predicted Elo + log-variance. **Player-level:** combine games by precision-weighted average (Gaussian posterior) or a hierarchical model; add Showdown RD-style shrinkage toward the pool mean.
6. **Calibration:** split-conformal / CQR on a held-out calibration set, stratified by rating band; report empirical coverage of 80% and 90% intervals.
7. **Censoring:** Tobit or clip at 1000.

#### 4.2 Metrics
- **MAE in Elo** and RMSE, overall and per 100-Elo band (regression-to-the-mean will show as bias at the tails; report it).
- **Spearman / Kendall rank correlation** between predicted and true Elo per player.
- **Coverage and width** of 80/90% intervals, plus a reliability plot (nominal vs empirical coverage).
- **n-games curve**: MAE and coverage vs number of games per player.
- Binned accuracy only as a secondary, comparable-to-literature metric.

#### 4.3 Baselines (all cheap)
- B0: predict training mean (MAE ~= 0.8 x SD, SD ~207-217 from our samples, so ~165-175 Elo for the dumbest baseline; compute exactly on your split).
- B1: team-only / usage-only model (shows how much "skill" is actually team strength).
- B2: outcome + game-length model (win, turns, forfeit).
- B3: previous-games Elo (oracle on the same player's earlier log lines): an upper bound, since it reads the label history; use only to show headroom, never as a feature.
- Literature anchors: 182 Elo MAE per game (chess CNN-LSTM).

#### 4.4 Leakage and bias pitfalls
1. **Elo is in the log.** The `|player|` line and `|raw|` rating lines contain the label. Strip both before computing features; assert in a test.
2. **Team strength vs decision skill.** Better players run more meta-optimal teams; a model on team features alone will "predict Elo". Include B1 and report skill gain over it. Rating bands correlate with team composition and sets (Metamon's `replay_stats` already shows band-specific sets).
3. **Row `rating` is the lower player's post-game rating** (1.3): using it as a per-player target biases labels and leaks outcome (the loser's post-game rating is below their pre-game Elo; winner's rating never appears).
4. **Selection into public replays** (win-biased, memorable games, saving habit). Estimates are for *saved* games. Check by comparing win rate of p1 in saved replays vs 50%.
5. **Matchmaking and Elo gaps.** Opponents are near-rated, so game outcomes are ~50/50 regardless of skill; outcome features carry little information; decisions are what differs.
6. **Floor at 1000 and decay >1400** mean Elo is not a pure skill measure (floor censors, decay drags inactive high players).
7. **Alts/smurfs and bots** (Smogon thread Dec 2024-May 2025, no resolution): one human, several accounts; a high-skill smurf on a fresh account has low Elo. Label noise is asymmetric (lower than true skill). Also some accounts may be bots after the Oct 2026 policy; unregistered bots are bannable but not filtered in the datasets.
8. **Metamon pseudonyms vs player grouping.** Group splits by pseudonym id; players also appear across formats; a player with 74+ games in one shard would dominate a random split.
9. **Time drift and meta shifts**: new Pokemon/sets each season; use time-based test.
10. **Per-game vs per-player evaluation mix-up** (Kuboki shows the gap). Always state which.
11. **2021-2024 hole and thin high-Elo mass** (1.5% > 1800): evaluate by band, don't average.
12. **Interval coverage under shift:** conformal guarantees assume exchangeability; time/player split breaks it a little. Report empirical coverage on the real test split.

---

### 5. Verification of section G claims (research-inputs.md)

| # | Claim (source) | Verdict | Evidence / correction |
|---|---|---|---|
| G1 | Metamon parsed: HF `jakegrigsby/metamon-parsed-replays`, GitHub `UT-Austin-RPL/metamon` | KEEP | HF card read; GitHub repo API: "Pokemon Showdown RL Agents and Datasets", MIT, 147 stars, last push 2026-07-23. |
| G2 | parsed ~28.5 GB, per-format archives | KEEP (adjust) | Card: 28.5 GB; archives for gen1ou, gen1nu, gen1ubers, gen1uu... gen2-4, gen9ou, plus `revealed_teams` and `replay_stats`. "Gen 1-4 OU/UU/NU/Ubers + Gen 9 OU" is right in spirit. |
| G3 | licence CC BY-NC 4.0 | KEEP for parsed only | Card + API: `cc-by-nc-4.0` on **parsed**. Raw replays, teams and others: **no licence stated** (HF API `license: None`). Code repo is MIT. The **paper** is CC BY 4.0 (arXiv). Don't conflate. |
| G4 | "latest batch adds Feb-May 2026" | KEEP | Changelog: v5 2026-01-18, v6 2026-05-19 ("replays as of May 19, 2026"). |
| G5 | usernames pseudonymised consistently with raw set | KEEP | Raw README: "Usernames have been replaced by a unique randomly generated pseudonym that is consistent across battles." Parsed card: "anonymized pseudonyms". |
| G6 | "40+ pretrained checkpoints" | WEAK (unverified) | HF model search shows only `jakegrigsby/metamon` (one repo). Count of checkpoints inside it not checked. Irrelevant to this task. |
| G7 | Replays only those users chose to upload | KEEP | Metamon README: players "choose to upload". Showdown code has `replaySaved` / `autosavereplays`. |
| G8 | Patchy after Showdown data loss (2021-2024) | KEEP (nuance) | Card says low 2021-2024 volume due to DB failure, mostly tournament/Smogtours survive. Shard 0 had 24,552 rows in 2023-2024 so the hole is partial. |
| G9 | smogon.com/stats monthly from ~late 2014; Tera data only from Sep 2024 | KEEP first half; Tera claim unverified | Directory index: 2014-11 to 2026-09. Tera timing not checked. |
| G10 | Raw: 2.68M rows, ~5.7 GB parquet, fields id/format/players/log/uploadtime/formatid/rating | KEEP | Card: 2,681,841 rows; 5.7 GB; 46 parquet shards. |
| G11 | v3 backfilled 1.2M Gen 9 OU to 2025-06-16; v6 cutoff 2026-05-19 | KEEP | Version table on card. |
| G12 | "recovered ladder replays set private, mostly Smogtours remain" | WEAK | Card only says low volume, "database failure", survivors mostly tournament. "Set private" not on the card. |
| G13 | Metamon names pseudonymised, "cannot join to real ladder names; re-pull by replay id for player work" | KEEP | Replay ids are preserved (e.g. `gen9ou-2254484296`); the live API returns the real-name log for an id (verified for `gen9ou-2690692096`). Replays that were later deleted/privated cannot be re-pulled. **Better route: HolidayOugi has raw names offline.** |
| G14 | **Rating in Metamon rows usable as an Elo label?** (coordinator question) | **Qualified: not as per-player label** | Row `rating` = lower player's post-game rating (exact on HolidayOugi, consistent on Metamon). Use the log `|player|` pre-game Elo instead (95.8% coverage in Metamon sample). Pseudonymised names do not block player-level estimation inside Metamon (consistent pseudonyms), only the join to the ladder. |
| G15 | PokeChamp: `sethkarten/pokechamp`, ICML 2025, 2M battles (1.9M train/213K test), 37+ formats, Elo ~1000-1800+ | CORRECT the id; KEEP numbers | HF id is **`milkkarten/pokechamp`** (`sethkarten/pokechamp` returns 401). Splits are 1,916,868 train + 213,356 test = 2.13M total (README says "2M clean"). Paper (arXiv 2503.04094) says >3M battles, >500k Elo>1600; ICML poster page exists; arXiv page lists no venue. Elo is **binned** (5 bins, edges not listed), not a continuous label. |
| G16 | Replay API `/search.json?format=gen9ou`, paginate with `before`=uploadtime, `/{id}.json`, `/{id}.log` | KEEP (nuance) | `search.json` returns 51 rows; `before` works empirically but is undocumented; official client uses `page`. `/{id}.json` verified. `/{id}.log` not tested. |
| G17 | Ladder JSON `/ladder/{format}.json` caps at rank 500; rows carry Elo, GXE, Glicko-1 +/- RD, COIL | KEEP (COIL nuance) | Fields verified: `elo, gxe, r, rd, rpr, rprd, w, l`... **COIL is in `/users/<id>.json`, not in the ladder row.** 500-row count inferred from document length, not counted. |
| G18 | `/users/{name}.json` | KEEP | Verified: `ratings.<format>.{elo,gxe,rpr,rprd,w,l,coil}`. Note path is `pokemonshowdown.com/users/<userid>.json`. |
| G19 | Ranks 501-1000 must be built from hourly snapshots / harvested names | KEEP | No endpoint found (prefix filter returned empty list). `rptime` shows rating periods are hourly-ish in the JSON. |
| G20 | Elo decays for inactive >1400 | KEEP (precision) | Help page: 0 games: -1 per 50 over 1400 (per day); 1-5 games: -1 per 100 over 1500; >5 games: none. research-inputs line 89 is imprecise. |
| G21 | Smogtours replay ids `smogtours-gen9ou-N` | KEEP | Seen in live `search.json` output. Smogtours rows have `rating` null in 100% of 530 rows (HolidayOugi part 13). |
| G22 | Tooling by FullLifeGames | WEAK | `FullLifeGames/BattleHelper` exists (MIT, 1 star, last push 2023-07-20, "analyzes replays and reviews teams posted on Smogon"); no Smogtours-scraper mention. |
| G23 | "GSC OU precedent 19,194 replays" | WEAK / unverified | Not found on any page we opened. HolidayOugi card shows Gen 2 OU = 51,627 replays total; so 19,194 may be a Smogtours-only subset; unverified. |
| G24 | `Looyyd/pokebot-meta-chaos` mirrors Smogon chaos JSONs | KEEP (scope) | HF dataset exists (126 downloads, modified 2026-08-25): 41 files, `gen9ou-1500-YYYY-MM.json` x20 and `gen9ou-1825-YYYY-MM.json` x19 for 2025-01..2026-07; "mirrored unmodified, with attribution"; no licence field. Source is Smogon's public stats directory. |
| G25 | Suggestion: Metamon raw v6 for history + API top-up after 2026-05-19 + snapshotter now + Smogtours eval | KEEP, with a change | Prefer HolidayOugi as main (raw names, newer: to 2026-10-05, 2.5M gen9ou); keep Metamon raw for cross-check. |

**Showdown terms for crawling (answer to the coordinator):** nothing in `/rules` or `/privacy`; Smogon's Oct 2026 bot policy covers playing bots, not scraping. No rate limit documented. Use the offline datasets first and keep any live crawling polite. The 2026 HolidayOugi dataset and Metamon both were built by pulling the public replay API at scale and publish openly, which is community precedent, not permission.

**Licence implication for a hackathon demo:** keep the demo and repo non-commercial and attribute Metamon (CC BY-NC 4.0) if you use the parsed set; if you use raw replays, either derive your own parse (no stated licence to violate; replays are user-generated public content) or ask the maintainers. Do not redistribute HolidayOugi raw usernames in the product UI beyond public ladder names (privacy hygiene; usernames are public on Showdown but Metamon deliberately pseudonymised them).

---

### 6. Community consensus vs professional consensus

- **Professional (papers):** skill is estimable from decisions but per-player accuracy is limited with ~15-20 games (Kuboki; Chen); move-quality models trace back to Regan/Haworth; skill-conditioned policies are the current best human model (Maia-2); calibration (conformal) is the right wrapper; Showdown Elo is considered noisy by the PokeAgent authors (BT with 250+ games).
- **Community (Smogon forums/articles, read today):** consistently treat **GXE** as the better skill measure than Elo (Elo Hell-o; forum replies); acknowledge ladder randomness; disagree on how bad Elo/floor/matchmaking distortions are (Chains of Markov: "impurities of Elo are vastly overstated"; Oculars: the floor is the real issue); smurfing/alts is a recognised problem; Zarel (PS creator) was only "weakly in favor" of Glicko-based matchmaking. Reddit/HN/StackExchange: searches returned nothing usable on scraping or rating noise (a PokemonDB Q&A page on GXE was seen only as a search snippet).
- **Final call:** professional and community views agree on the key design choice: **do not treat raw ladder Elo as ground truth skill.** Use pre-game per-player Elo as the practical label (what exists at scale), prefer GXE/Glicko `r` with `rd` for top players, say so openly, and make calibration the headline contribution.

---

### 7. Source ledger

#### KEEP
| Source | Verified how | Used for |
|---|---|---|
| HF `HolidayOugi/pokemon-showdown-replays` (card + file tree + datasets-server stats + part 13 downloaded) | opened; downloaded 261 MB part | size 34,325,933; gen9ou 2,506,142; raw names; rating null rates; rating definition |
| HF `jakegrigsby/metamon-raw-replays` (card, README, API, shard 0 downloaded) | opened; downloaded 120 MB shard | size, fields, versions, pseudonyms, rating distribution |
| HF `jakegrigsby/metamon-parsed-replays` (card + API) | opened | CC BY-NC 4.0; 28.5 GB; Elo in filenames |
| HF `milkkarten/pokechamp` (card + README + API) | opened | 2.13M rows, binned Elo |
| HF `milkkarten/pokemon-showdown-replays-merged` | opened | 29.06M rows; rating = avg if available (definition unverified, see 1.1) |
| Showdown ladder JSON, users JSON, replay search/replay JSON, replay client source | fetched live | Section 2 endpoints |
| pokemonshowdown.com/pages/ladderhelp | read | Elo/Glicko/GXE/decay/floor |
| Smogon "Initial policy on bots" (forums thread 3789528) | read | bot policy, registry, AI ghosting |
| Smogon "Elo Hell-o" (The Smog issue 43) | read | rating uncertainty, GXE |
| Smogon thread "Rating uncertainty in PS ladder matches" (3756168) | read | alts, floor, Zarel stance |
| Smogon post 10665090 "Rejected Elo Gaps in DOU Ladder" | read | GXE robust to gap matches, W/L weak |
| Regan & Haworth, Intrinsic Chess Ratings, AAAI-11 (ojs.aaai.org/index.php/AAAI/article/view/7951) | opened | move-quality -> Elo |
| McIlroy-Young et al., Aligning Superhuman AI with Human Behavior, KDD 2020 (arXiv 2006.01855) | opened abs | Maia |
| Tang et al., Maia-2, NeurIPS 2024 (arXiv 2409.20553; HTML v2 read) | opened | skill-aware conditioning; numbers in 3.1 |
| McIlroy-Young et al., Behavioral stylometry (arXiv 2208.01366, NeurIPS 2021) | opened abs | identification 98% at 100 games |
| Omori & Tadepalli, arXiv 2409.11506 (CG 2024) | opened abs | MAE 182 |
| Chen, Shih, Wu, ICLR 2025 (arXiv 2502.17109) | opened abs | strength estimation, >80% at 15 games (Go) |
| Kuboki et al., arXiv 2505.00279 (preprint) | opened abs + html | corroborates Chen; individual-player gap |
| PokeAgent Challenge, NeurIPS 2025 Competition Track (arXiv 2603.15563) | opened abs + html | Showdown Elo too noisy; BT 250 games |
| Karten, Nguyen, Jin, PokeChamp (arXiv 2503.04094) | opened abs + html | >3M battles, Elo modes 1150/1350 |
| Grigsby et al., Metamon (arXiv 2504.04395, RLC 2025) | opened abs | dataset provenance |
| Romano et al., CQR (arXiv 1905.03222, NeurIPS 2019); Angelopoulos & Bates (arXiv 2107.07511) | opened abs | calibrated intervals |
| Smogon stats index; HF `Looyyd/pokebot-meta-chaos`; GitHub API for Metamon and BattleHelper | opened | G9, G22, G24 |

Corroboration: the rating-label definition and distribution claims are backed by two independent measured datasets plus the PokeChamp paper; sample-size claims by Chen + Kuboki + PokeAgent; terms-of-service claim by rules page + privacy page + Smogon policy (all silent on scraping).

#### WEAK
- Di Fatta, Haworth, Regan, Skill Rating by Bayesian Inference, IEEE CIDM 2009 (Buffalo/Reading/IEEE listings; PDF text did not load, abstract not read).
- Glickman 1999 and Herbrich et al. 2006 (existence confirmed by RePEc/NeurIPS/Microsoft listings; older than 3-4 years; foundational only).
- IRT-for-game-skill: only chess/soccer snippets from search, no Pokemon or esports paper; method-level suggestion only.
- Erdos Institute VGC scrape (14,474 battles): unpublished class report, not downloaded.
- Metamon "40+ checkpoints", "recovered ladder replays set private", "GSC OU 19,194 replays", "Tera data only from Sep 2024": unverified teammate claims.
- `search.json?...&before=` cursor: works empirically, undocumented.
- merged dataset's `rating` = "average rating of players": card text, contradicted for the other datasets (it is the lower player's post-game rating); not tested on the merged set.
- Kuboki et al. is a preprint (no venue on arXiv page).
- Moonlight/Liner/glama/other aggregator pages seen in search results: not used.

#### DO NOT USE (tombstones)
- **"Row `rating` in Metamon/HolidayOugi is each player's (or the average) Elo."** Refuted by: HolidayOugi logs (100.0% of 7,758 rows: rating = min post-game rating), Metamon shard 0 (median diff to min pre-game -16, mean absolute gap to average 26.8), live API replay `gen9ou-2690692096` (rating 1747 = loser's post-game). Do not use as a per-player label or as "average Elo".
- **`sethkarten/pokechamp` as the PokeChamp HF id.** HF API returns 401; the dataset is `milkkarten/pokechamp`.
- **"Elo decays 1 point/day + 1 per 50 over 1400" for all inactive players** (research-inputs line 89). Ladder help page: decay depends on games played; 1 per 50 over 1400 is only the 0-games case.
- **"COIL is in the ladder row."** It is in `/users/<id>.json`; the ladder JSON rows have no `coil` key.
- **"PokeChamp is 2M battles 1.9M/213K"** as an exact total: splits sum to 2,130,224.
- **Any claim that a published paper predicts Pokemon player rating from decisions:** none found in extended search (PokeChamp, Metamon, PokeAgent, Smogon tools only).

---

# Pass 3, winprob_evaluation_gaps (source: `research_notes/winprob-evaluation-gaps/winprob_evaluation_gaps.md`)

## Momentum: weaknesses, gaps and the evidence that defends it (research pass, 2026-10-24)

Scope: Momentum as a *prediction + decision* submission (HRT "Best Use of Data for Predictions & Decision Making", plus Best Handmade).
Method: CLAUDE.md §10. Every source below was opened this session (access notes in the ledger). "Derived" = my own reasoning, no external source; treat as a hypothesis the team can test.
Recency note: the stats foundations (Gneiting 2007, Guo 2017, Roberts 2017) are older because nothing newer replaces them; I paired each with a 2021-2026 source where one exists. The Pokémon, chess-LLM and win-probability-uncertainty sources are 2024-2026.

CATEGORY INDEX
1. Bottom line · 2. Ranked gaps + cheapest fix · 3. The one evaluation story for HRT judges (5-20 h) · 4. Gaps per layer (data / decision / bot) · 5. Cut order · 6. Evidence: evaluation · 7. Evidence: coach claims · 8. Evidence: LLM explanations · 9. What a quant-firm track likely rewards · 10. Risks (licence, compute, time, demo) · 11. Community consensus + final call · 12. Ledger (KEEP / WEAK / DO NOT USE) · 13. Open questions

---

### 1. Bottom line

- The idea is not weak because of the model. It is weak where a quant judge will poke: **leakage, honest baselines, calibration, error bars, and "what does 18% actually mean?"**. Every one of those is cheap to fix and cheap to show in one figure each.
- The biggest *conceptual* hole is specific to Pokémon, not chess: **a win-probability drop mixes the player's decision with dice (crits, misses, damage rolls, secondary effects) and with hidden information**. Chess coaches (Lichess, chess.com) never face this. If Momentum says "this turn cost you 18%" and the cause was a 1-in-16 crit, a Smogon-literate judge will say so in 5 seconds.
- Second hole: the replay coach reads **the future into the past** if it uses Metamon's *parsed* replays, because Metamon back-fills never-revealed team details from the end of the battle (verified, §7.3). Train and score on raw spectator-view features, or the numbers are look-ahead-contaminated.
- Strongest honest pitch: "a calibrated, uncertainty-aware win-probability model, tested forward in time on games that did not exist when we froze it, beating three named baselines by a stated margin with game-level bootstrap intervals; the coach only states numbers the model computed, with intervals; here is where it is wrong."

---

### 2. Ranked gaps and the cheapest fix for each

Rank = (chance a judge hits it) x (damage if they do) / (cost to fix).

| # | Gap | Why it hurts | Cheapest fix (hours) |
|---|---|---|---|
| 1 | **Leakage via split design.** Turn-level random split puts turns of one game (and one player, one team) in both train and test. | Inflates every metric. Dependent data makes random CV under-estimate error (Roberts 2017; Kapoor & Narayanan 2022; sklearn GroupKFold docs). Turns of one game share one outcome, so effective sample size is far below the row count (Brill et al. 2025). | Split **by battle id, by time, and by player** (pseudonyms are consistent in Metamon raw). Freeze split table first, commit it. Test set touched once. (1 h) |
| 2 | **No honest baselines.** "Our model gets 7x% accuracy" means nothing. | A quant judge asks "versus what?". The only public prior art (Smogon Battle Predictor, 2020) reported *accuracy* and was criticised by its own users for nonsense probabilities (§6.7). | Baseline ladder: constant; Glicko/Elo-only pre-game; HP + mons-alive logistic regression; gradient-boosted trees; then anything fancier. Report log loss and Brier skill vs each. (2 h) |
| 3 | **Wrong or single metric.** Accuracy is not a proper scoring rule. | Rewards confident wrong answers or hides miscalibration. | Report **log loss + Brier** (both strictly proper), plus a **reliability diagram** and ECE only as a secondary number. (0.5 h) |
| 4 | **Calibration not shown by turn and by skill.** | A pooled-calibrated model can be miscalibrated in the first 5 turns or at high Elo; chess.com explicitly makes win chances rating-dependent. | Reliability diagram per turn-bucket and per rating-bucket, with CORP bands. (1 h) |
| 5 | **No uncertainty on "18%".** Point estimates of win probability are high-variance. | Brill et al. 2025: win-probability estimators from play-by-play data are high-variance, CIs must be substantially wide. A coach sentence with no interval overclaims. | Bootstrap-ensemble (5-10 models, resampled by game); report mean and interval; **only call a "blunder" if the interval of the drop clears the threshold**. (1.5 h) |
| 6 | **Luck vs decision.** The drop includes dice. | Not present in chess; unique to Pokémon. | Tag luck events from the log (crit, miss, full-para, flinch, secondary-effect proc) and either exclude those turns from blame or compute the drop on the *expected* post-state (average over RNG) when the simulator is available. State this in the pitch. (1-2 h) *(derived; see §7.5)* |
| 7 | **Hindsight / hidden information.** The replay (and Metamon's parsed version) shows or infers things the player did not know. | Blaming a player for not knowing a hidden set is look-ahead bias, and the same bug is a leakage bug in the model. | Features strictly from the public spectator log up to turn t. Ablation: train once on public-only features, once on Metamon-style back-filled features; the gap is the size of the leak. Coach copy says "with what you had seen" vs "in hindsight". (1 h) |
| 8 | **"A stronger line was X" is unvalidated.** Counterfactual states are off the data distribution and argmax over noisy estimates is biased up. | Offline-RL distribution shift (Levine et al. 2020) and the optimizer's curse (Smith & Winkler 2006). Simultaneous moves also make "best move" depend on what the opponent does (Lisý et al. 2013). | Only suggest alternatives that (a) the one-step simulator can score, (b) the ensemble agrees on, and (c) are ranked by a *lower confidence bound*, not the mean. Phrase as "best against the opponent's likely action (p = ...)", keep the payoff matrix. (2 h) |
| 9 | **Coach validity has no external anchor.** "Blunder" is just the model's own drop. | Circular. | Three cheap proxies, none ground truth: (i) flagged-blunder rate falls with rating; (ii) blind check of 30 flagged turns by a Smogon-literate teammate, report agreement and kappa; (iii) match Lichess/chess.com-style thresholds and say they are borrowed. (2 h) |
| 10 | **LLM invents rationale.** | Un-tooled GPT-5.4 gets 22.0% of chess-commentary sub-claims wrong; small open models >40% (Hebbar et al. 2026). CoT explanations can misrepresent the real reason (Turpin et al. 2023). | Template first: every sentence is filled from computed fields. LLM (if used at all) only paraphrases and must not add numbers; a regex check rejects any number not in the input. Fall back to the template. (1.5 h) |
| 11 | **Concept drift / time.** Showdown metagame changes (suspect tests, bans, new Pokémon). | HRT's own ML page says models "must be robust to distributional shifts". Train-on-past, test-on-future is the only honest test. | Out-of-time test set (§3). Report metric by month to show decay. (0.5 h once split exists) |
| 12 | **Selection bias in replays.** Only battles whose players chose to upload; post-2020 ladder replays were rebuilt as *private by default*; 2021-2024 coverage is thin. | The sample is not "all games". | State it as a limit; compare base rates (p1 win share, rating gap distribution) with the ladder; do not claim population-level numbers. (0.5 h) |
| 13 | **Multiple-comparison / tuning on test.** | Quant culture: backtests overfit with many tried configs (Bailey et al. 2017; Wiecki et al. 2016). | Pre-register metrics in a commit; tune on validation only; report how many configs were tried. (0.5 h) |
| 14 | **Latency / "fast" claim unmeasured.** | ~850 simulator calls per turn before pruning (design/decision-layer.md §5). | Report p50/p99 ms per prediction and per full decision. (0.5 h) |
| 15 | **Licence / ToS.** | See §10: low risk for a hackathon, but state it. Parsed replays are CC BY-NC 4.0 (attribution required). | One "Data & licence" line in README. (0.2 h) |

---

### 3. The single most convincing evaluation story for HRT judges (given 5-20 h)

**Title: "Forward-tested, calibrated, with error bars, against honest baselines."** One page, four figures, one sentence each.

**Protocol (write it before looking at the test set; commit it):**
1. **Data.** Gen9 OU replays from Metamon raw (2,681,841 rows verified; fields id, format, players, log, uploadtime, formatid, rating). Use a few hundred thousand games, not all.
2. **Split.** By `uploadtime`: train (oldest) / validation / **test = games uploaded after the Metamon v6 cutoff (2026-05-19), pulled by us from the Showdown replay API** (so no dataset, ours or anyone's, had them when we trained). Within each split group by battle id; also drop test players seen in train as a sensitivity run (pseudonyms are consistent). Remove forfeit/disconnect games (outcome not decided by play; derived).
3. **Targets and features.** Outcome = winner. Features only from public log up to turn t (+ both players' start ratings from the `|player|` line). Exclude `|win|` and the post-game `|raw|` rating-change lines (they encode the result; derived from design/data-layer.md §2).
4. **Baseline ladder:** (B0) constant base rate; (B1) Glicko expected score from the two start ratings, E = 1 / (1 + 10^(-g(RD)(r - r_j)/400)) (Glickman's Glicko paper, formula verified) or plain Elo; (B2) logistic regression on HP-sum and mons-alive difference; (B3) B2 + ratings + field state; (M) gradient-boosted trees (optionally a small sequence model if time). Complexity has to *earn* its keep: say where it does not.
5. **Metrics:** log loss and Brier (strictly proper), Brier skill score vs B0, per-turn curves (turn 1 up to the end), CORP reliability diagrams with confidence bands (Dimitriadis, Gneiting, Jordan 2021), ECE reported secondarily. **Intervals by resampling whole games** (cluster bootstrap), and *paired* game-level differences between model and each baseline.
6. **Uncertainty:** ensemble / bootstrap-trained models; show mean and interval for every number the coach speaks.

**Figures:**
- **F1:** log loss vs turn number, all rungs of the ladder, bootstrap bands. The model should win late in the game; early turns should sit near the rating-only baseline (honest: little information at turn 1).
- **F2:** reliability diagrams for turns 1-5 / 6-15 / 16+ and for rating bands. Show the bad bins, say so.
- **F3:** coach validity: share of flagged blunders per 100 turns by rating band (expect decreasing; chess caveat: Lichess says higher-rated players do not always have higher accuracy because their games are more complex), plus the 30-turn blind human check (agreement, kappa, N stated).
- **F4:** decision evidence. Preferred: model-guided bot vs a max-damage heuristic over >= 200 local games (one-sample test vs 50%: about 194 games for 80% power to detect 60%, normal approximation, derived), Wilson interval. Fallback if the bot is not ready: on held-out replay states, how often the model's top action matches strong players' actual action, by rating band (a Maia-style human-move-prediction test; McIlroy-Young et al. 2020).

**Three honest sentences to close with:** (1) what it cannot see (hidden sets, dice); (2) where calibration is worst; (3) what we would test next. HRT's own pages stress a "rigorous scientific approach" and warn that market data "contains very little signal, making it easy to overfit to noise" (§9): admitting limits is the pitch, not a weakness.

**Q&A card for the 4-5 minute judge visits (derived):** "Is it just HP?" -> B2 vs M. "Leakage?" -> split by game/time/player, features list, public-only ablation. "How many games?" -> N and effective-N. "Did you tune on test?" -> test touched once, commit hash. "Calibrated at turn 3 for 1500-Elo?" -> F2. "Luck or skill?" -> luck tags. "What does 18% mean?" -> mean and interval.

---

### 4. Gaps and improvements per layer (as designed in design/*.md; all still DRAFT, not team-agreed)

#### 4a. Data layer
| Gap | Fix |
|---|---|
| ClickHouse is a new service to run for a 5-20 h build (it is already an open 🟠). | Parquet + Polars/DuckDB on the 5.7 GB raw download (download_size 5,699,542,013 bytes verified). Save ClickHouse for "later". |
| No canonical split table. | First artefact: `battles(battle_id, uploadtime, p1, p2, r1, r2, winner, split, forfeit_flag)`. Everything else reads it. |
| Using Metamon *parsed* replays for features would import back-filled hidden info. | Parse raw yourself, spectator-view only. Optionally keep parsed as the "leaky" ablation. |
| Set priors from Smogon monthly chaos stats: stats for month M are computed from games that include your month-M test games. | Use priors from months strictly before the evaluation game (derived). |
| Selection and coverage bias (upload is voluntary; private-by-default after the 2023 database rebuild; 2021-2024 sparse). | Document; compare base rates; do not claim population results. |
| `rating` is a string field in the dataset schema; missing/unrated games unknown. | Count missing rate first; drop or model separately. |
| Bots, forfeits, near-empty games (open 🟠 "how bots are detected"). | Simple filters (turn count, forfeit flag, rating present); report how many removed. |
| Ladder snapshotter (top-500 only; cannot backfill). | Only worth it if "Elo from decisions" survives the cut; otherwise cut. |
| "Dataset card" missing. | n games, date range, format, rating distribution, filters, licence: Kapoor & Narayanan's "model info sheet" idea. |
| Claims in research-inputs §G not all verified. | Verified: raw 2.68M rows, fields, v6 cutoff 2026-05-19, replay-DB failure note, parsed set licence CC BY-NC 4.0. **Not verified:** "28.5 GB" parsed size; Derrick's "PokéChamp 2M clean battles, 1.9M/213K split, ICML 2025": the arXiv abstract says >3M games incl. >500k high-Elo and I saw no venue or split on that page. |

#### 4b. Decision layer
| Gap | Fix |
|---|---|
| Value model starts as "HP + Pokémon remaining" with no calibration step; EV maths assumes probabilities. | Make the calibrated win-probability model *the* value function; calibration is a feature, not polish. |
| Argmax over noisy value estimates is optimistically biased. | Lower confidence bound from the ensemble; or Bayesian shrinkage (Smith & Winkler remedy). |
| Simultaneous moves: "best move" is not defined without an opponent model. | Keep the payoff matrix (decision-layer.md recommends A pure EV, keep matrix); report EV under the opponent policy *and* worst case. Do not claim equilibrium play; MCTS-style equilibrium results (Lisý 2013) are asymptotic. |
| Belief layer (hard filter + Bayes reweight) is the most expensive component. | Cut for v1; use chaos priors (lagged) as features only. |
| Off-support counterfactuals. | Restrict to one-ply simulated outcomes; flag when ensemble disagrees. |
| Luck not modelled in attribution. | Luck tags or expected-post-state (gap #6). |
| No sanity tests on the value model. | Cheap metamorphic tests (mirror the sides -> p becomes 1 - p; remove an opponent's HP -> p must not fall; derived, motivated by Fluri et al. 2023, who found engines assigning opposite values to equivalent boards). |
| Speed claim. | Measure p50/p99 latency; prune with calc first (design option C). |

#### 4c. Bot layer
| Gap | Fix |
|---|---|
| The review feature does **not** need the bot; the bot is only needed for the decision A/B (F4). | Build the replay coach first; bot second. |
| Train/serve skew: training on reconstructed spectator logs, serving on live `request` JSON. | Parity test: replay logs through the bot parser and diff the feature vectors. |
| Format: gen9ou with team building, a public ladder, rate limits, unknown ToS. | Local server only; fixed team; no ladder. Showdown's rules page has no stated bot/scraping rule (checked), but the privacy policy says logs may be kept; stay polite and cache. |
| Framework choice is open (own parser vs `@pkmn/*`). | `@pkmn/*` (fewer parser bugs); any parser bug silently lowers the bot, and nobody will notice. |
| Demo risk (live server, API, wifi). | Pre-compute reviews for 3 chosen replays; run offline; template text is the always-on path; voice is optional. |

---

### 5. Realistic cut order (first to cut at the top)

1. ElevenLabs voice (optional add-on by the user's own words).
2. LLM paraphrase layer (template text is safer and cheaper; reinstate only if time).
3. Physical Handmade piece beyond a small display, unless the organisers confirm it is needed (event doc Q: "from scratch" undefined).
4. "Elo-from-decisions" estimator and the ladder snapshotter beyond top-500 (hard to validate; no ground truth for decision-Elo; derived).
5. Belief / Bayes reweight; Nash or mixed-strategy selection; look-ahead beyond one ply.
6. Sequence model / transformer value net (GBM + ensemble is enough; quants like simple strong baselines).
7. ClickHouse (use Parquet + DuckDB/Polars).
8. Public-ladder bot play; keep local server only.
9. The bot A/B (F4) falls back to the offline human-agreement test. **Do not cut:** the split protocol, baseline ladder, proper scores, reliability diagrams, intervals, luck tags, public-only features, and the "limits" slide. Those are the submission.

Rough hours (derived estimates, vibecoding): data + split 2-3 h; features + baselines 2 h; model + calibration 1-2 h; intervals + figures 2 h; coach templates + blunder logic 2 h; validation proxies 1-2 h; polish/README/demo 2 h => 12-15 h, so 5-7 h gets items up to F1/F2 only. If only 5-7 h exist, ship F1, F2 and the template coach with intervals, and say F3/F4 are future work.

---

### 6. Evidence: how to evaluate a win-probability model

#### 6.1 Splits and leakage (KEEP; 4 independent sources)
- Roberts et al. (Ecography 2017): ignoring temporal/hierarchical structure in cross-validation "leads to serious underestimation of predictive error"; block CV nearly always more appropriate for predicting new data.
- Kapoor & Narayanan (arXiv 2022): leakage affects 329 papers in 17 fields; an ML-vs-logistic-regression comparison in civil-war prediction disappears once leakage is fixed; proposes "model info sheets".
- scikit-learn docs: GroupKFold ensures "the same group is not represented in both testing and training sets"; TimeSeriesSplit tests on "future" observations. (Official docs, opened by curl.)
- Brill, Yurko, Wyner (arXiv 2406.16171, accepted to JQAS): in play-by-play data the dependence "substantially inflates the bias and variance" of win-probability estimators, shrinks effective sample size, and CIs must be substantially wide for valid coverage.
- Application: group by battle id (each Metamon battle yields two POV trajectories, so group on battle id, not trajectory); also by player and by time.

#### 6.2 Proper scoring rules (KEEP)
- Gneiting & Raftery, JASA 2007: strictly proper rules reward honest probabilities; logarithmic and quadratic (Brier) are examples. (Abstract confirmed via two repository records; PDF not decodable.)
- Dimitriadis, Gneiting, Jordan, Vogel (arXiv 2023, "triptych"): reliability diagram (calibration) + ROC (discrimination) + Murphy diagram (overall performance; area = mean Brier); decomposition of the score into miscalibration, discrimination, uncertainty.
- Community: Cross Validated, "Is accuracy an improper scoring rule?" (score 35 and 31 on the two top answers): accuracy "is not even a scoring rule... Don't use it". "Choosing among proper scoring rules" (score 32): log loss is the usual default, Brier is bounded and less punishing.
- Use log loss as the headline, Brier for robustness, Brier skill score for readability.

#### 6.3 Calibration (KEEP)
- Guo et al. (ICML 2017): defines reliability diagrams and ECE; shows temperature scaling (single parameter) fixes most miscalibration cheaply. (Opened PDF text.)
- Nixon et al. (2019): ECE depends on binning; adaptive binning more stable; ranking of recalibration methods "is drastically impacted by the choice of calibration measure".
- Dimitriadis et al. (PNAS 2021): CORP reliability diagrams via pool-adjacent-violators, reproducible, with resampling-based uncertainty. **Use CORP instead of equal-width bins.**
- Cheap recalibration: Platt/temperature scaling or isotonic on the validation split only.

#### 6.4 Intervals
- Cameron & Miller (J. Human Resources 2015): when errors are correlated within clusters, default standard errors overstate precision; use cluster-robust inference; the number of clusters (games) matters, not rows.
- Angelopoulos & Bates (2021; Found. Trends ML 2023): conformal prediction for distribution-free uncertainty sets on any pretrained model (optional, likely over budget).
- Practical: cluster bootstrap over games; ensemble spread for per-turn intervals.

#### 6.5 Drift and time (KEEP-ish)
- Gama et al. (ACM Computing Surveys 2014): relation between inputs and target shifts over time in online learning; evaluation and adaptation methods surveyed.
- HRT machine-learning page: models "must be robust to distributional shifts caused by a rapidly evolving world".
- Smogon runs a continuous stream of suspect tests in 2026 (e.g. ZU, PU, Shared Power pages opened). I did **not** find a verified Gen 9 OU ban inside the test window, so "the OU meta shifted in your window" is **unconfirmed**; check the Smogon Gen 9 OU tiering thread before saying it.

#### 6.6 Baselines
- Glicko expected score (Glickman, glicko.net): E = 1/(1 + 10^(-g(RD_j)(r - r_j)/400)), formula verified in the PDF. Showdown ladders expose Elo/GXE/Glicko-1 (research-inputs §G, unverified by me; Metamon paper confirms Glicko-1 and GXE are used for evaluation).
- Smogon forum proposal uses the Glicko formula as "who was favoured" for luck estimation (a proposal, not a standard).
- I found **no published log-loss or Brier benchmark for Showdown win prediction**, so there is no number to beat; the baseline ladder *is* the benchmark.

#### 6.7 Prior art on Pokémon win prediction (WEAK, student/forum quality)
- Smogon "Pokemon Battle Predictor" (aed3, 2020, Gen 8 OU): TensorFlow.js models on 10k+ battles; claimed "95% confidence interval of 8%", later "all 84 models at least 75% accuracy"; the author admits the win-chance model "favors lower percent chances of winning as doing so makes the chance more accurate"; users reported 90%+ for the side that was clearly behind, values stuck above 99%, and a probability that rose after a key KO. This is the failure pattern Momentum must visibly avoid, and a good "why proper scores" example.
- Erdős Institute boot-camp project (2024, VGC): random forest 61% (4 starting mons) to 76% (all mons, all turns) on 10k battles. Student report.
- No peer-reviewed Pokémon win-probability paper found. Metamon (RLC 2025) and PokéAgent (NeurIPS 2025 competition, arXiv March 2026) are about agents, not calibrated win probability. **Novelty claim is safe but narrow: "calibrated, uncertainty-aware, forward-tested" is the new part, not "win probability".**

---

### 7. Evidence: validating the coach claims

#### 7.1 Chess analogues (published formulas)
**Lichess (official page + source code, KEEP):**
- Win% = 50 + 50 * (2 / (1 + exp(-0.00368208 * centipawns)) - 1).
- Move accuracy% = 103.1668 * exp(-0.04354 * (WinBefore - WinAfter)) - 3.1669 (code adds +1 "uncertainty bonus (due to imperfect analysis)", clamps to [0, 100]; 100 if the move does not lower win%).
- Move labels (lila `tree/Advice.scala`): drop in "winning chances" >= 0.1 inaccuracy, >= 0.2 mistake, >= 0.3 blunder. **Scale check:** `winningChances` runs from -1 to +1 (scalachess `eval.scala`), so these are **5 / 10 / 15 win-percentage points** from the mover's point of view. (A forum thread quoted them as 10/20/30%; a user measuring sample games saw blunders as roughly >15 win% points. The code reading agrees with the user.) Mate cases are handled separately.
- The curve was fitted by one contributor on about 75k positions from a June 2022 database (described as 2300+ rapid; training code filter was 1000 < Elo < 4000), with hard-coded anchor points; a reviewer said they could not find the data or full method (lila PR #11148). **So the formula is a pragmatic fit, not a validated law.**
- Lichess's own caveats: accuracy "is flawed to compare to a test grade"; complex positions lower it; lopsided positions inflate it; game accuracy is a blend of volatility-weighted and harmonic means; no universally accepted method.

**chess.com (official support page, KEEP):** expected points lost per move: Best 0; Excellent 0-0.02; Good 0.02-0.05; Inaccuracy 0.05-0.10; Mistake 0.10-0.20; Blunder 0.20-1.00. Win chances depend on **player rating and engine eval**; the eval needed to call a position winning/equal/losing "varies according to the player's rating". Two major products disagree on thresholds and on whether rating enters: so Momentum's thresholds are a *choice* to justify, not a standard to cite.

**Stockfish WDL model (official repo, KEEP):** win rate is a logistic function of the evaluation, additionally conditioned on material or move count, fitted on fishtest self-play so that "100 centipawns" = 50% win at LTC self-play; README gives no transfer guarantee to other opponents or strengths.

**Take-aways for Momentum:** (1) a logistic map is the standard bridge, but yours is *learned*, so you can do better: test it; (2) a rating-conditioned model matches chess.com's design; (3) use thresholds in **win-probability points**, pick 5/10/15 (Lichess-like) or 5/10/20 (chess.com-like), say which, and show how flags move if you change them (sensitivity table); (4) accuracy-style scores need a position-difficulty caveat (below).

#### 7.2 Is "win-prob drop" a valid blunder definition? Critiques
- Same-position difficulty: HN thread on Lichess's "most accurate world champion" post (169 points, 58 comments): accuracy depends on how complicated positions are; engine evaluations have wide error bars ("majority of the draws [in TCEC] saw at least one position with an evaluation higher than +/-1.0"); engine-best is not human-practical. Lichess's own page says the same.
- Engines can be inconsistent: Fluri, Paleka, Tramèr (arXiv 2023) found a chess engine assigning opposing valuations to semantically identical boards, i.e. the "oracle" is itself noisy. Momentum's oracle is a statistical model, so test consistency (§4b).
- Human-relevant error: Maia (KDD 2020) shows engines predict human moves poorly and that a model trained on human games predicts human moves best at the matching skill level, and can predict when a player is about to make a large mistake. Relevance: judge "blunder" relative to the player's level, not only to a perfect player.
- No Pokémon-specific validation of win-probability-drop blunders exists in the literature I could find. **This is an open-ground claim; label it a proxy-validated heuristic.**

#### 7.3 Hindsight and hidden information (KEEP; 2 independent sources + 1 psychology source)
- Showdown replays are the **spectator view**: Metamon (RLC 2025) describes the dataset as spectator logs ("a third-party spectator who has access to information about neither team") and builds a pipeline that converts them to each player's perspective.
- **Metamon back-fills.** Appendix D: "By the end of the battle, some details may still be missing and are inferred with Pokémon Showdown statistics. We then backfill the inferred team through the trajectory." The Metamon replay-parser README repeats that it "infers missing information". Therefore any feature from the parsed dataset can encode information from after turn t. (Fine for imitation learning; wrong for scoring "what was knowable at turn t".)
- Fischhoff (1975): once people know an outcome they overestimate how predictable it was. Replication record is mixed (one 2021 success, one 2025 preregistered failure per the replication atlas), so use it only as a framing for coach copy, not as an empirical claim.
- Fix: public-state features + wording "with what you had seen". Optional ablation to quantify the leak.

#### 7.4 Cautions on the 'hidden info' direction
The coach can also be *unfair in the other direction*: it knows both teams' revealed sets at turn t but the player does not know what the opponent holds. Use the same public state the player saw (their own side fully, the opponent's revealed only). (Derived; this is exactly Metamon's POV split.)

#### 7.5 Luck vs skill (derived + weak community evidence)
- Lichess/chess.com compute accuracy from the *next position's* evaluation, valid because chess has no dice. In Pokémon the realised next state includes crits, misses and damage rolls, so a realised-state win-prob drop partly measures luck. (Reasoning from the Lichess code, `AccuracyPercent.fromWinPercents(before, after)` on realised evals.)
- Smogon community articles treat luck as a first-class concept ("Playing with Loaded Dice"; a forum "hax" proposal that scores luck with Glicko win expectancy) but offer no accepted metric. **WEAK**; the design choice (tag luck events) is ours to defend with an example.

---

### 8. Evidence: LLM-generated explanations (hallucination, faithfulness) and mitigation

- **Tool-augmented chess commentary study** (Hebbar, Sheng, Oh, Viswanath, arXiv 2608.04240, Aug 2026): splits commentary into atomic claims and checks each against engine tools and expert gold; GPT-5.4 without tools has incorrect sub-claims 22.0% of the time, smaller open models >40%; tool augmentation "substantially improves" correctness; coverage of expert ideas stays limited. 325 position-move pairs, 125 with expert gold. *(arXiv preprint, no venue stated; very recent; strong fit.)*
- **Faithfulness of chess explanations** (Parfenova, arXiv 2609.22245, BlackboxNLP at EMNLP 2026): explanations barely help beyond the board state once move hints are masked; irrelevant explanations still shift predictions; fluency, consistency and correctness are separate properties.
- **CoT can misrepresent the true reason** (Turpin et al., NeurIPS 2023): biasing features change answers (accuracy down to 36% lower on 13 BIG-Bench Hard tasks) and are not mentioned in the explanation. Lanham et al. (2023): faithfulness varies by task and gets *worse* with larger models on most tasks studied. Jacovi & Goldberg (ACL 2020): faithfulness is a property to be evaluated, graded rather than binary.
- **Data-to-text hallucination:** Ji et al. (ACM Computing Surveys, arXiv 2202.03629) survey includes data-to-text; Wiseman, Shieber, Rush (EMNLP 2017) found neural models fluent but not convincingly matching humans on a records-to-document task and that **templated baselines beat neural models on some metrics**.
- **PokéLLMon** (Hu et al., arXiv 2402.01118, 2024, not peer-reviewed per the page): names knowledge-augmented generation as an anti-hallucination measure in Pokémon battles; the abstract does not quantify its effect. **WEAK** as evidence for the mitigation, KEEP as evidence that the problem exists in this exact game.
- **Mitigation that is both cheap and defensible:** every sentence is generated from a typed record `{turn, action, p_before ± ci, p_after ± ci, delta, luck_flag, known_info, alt_action, alt_gain}`. The LLM, if used, only rephrases; a validator extracts all numbers/Pokémon/move names from the output and rejects any not in the record (this is the atomic-claim idea of Hebbar et al. in miniature). Show one failure case in the demo ("the LLM said X; the validator caught it").
- Honest limit: faithfulness papers study the *model's own reasoning*. A template that quotes computed numbers is faithful by construction to those numbers; it is not evidence the numbers are *right*, which is what §6 is for.

---

### 9. What a quant-firm track likely rewards

Facts (event rules, local note `event_rules_prizes.md`): the HRT prize has **no published criteria** beyond the title and "Use your creativity to make the best use of data"; no HRT judge is listed on Devpost; judging is science-fair style, 4-5 minutes per judge, Sunday 13:00-15:45 GMT. "Prediction + decision + backtest" is the team's reading, not an HRT rule (WEAK in the local ledger).

HRT public statements (KEEP as statements of what the firm says; the mapping to judging is my inference, WEAK):
- ML page (hudsonrivertrading.com/machine-learning): "Market data contains very little signal, making it easy to overfit to noise"; "Our models must be robust to distributional shifts caused by a rapidly evolving world"; heading "Join a Rigorous Research Culture".
- HRT Beat, "Applying Artificial Intelligence to Trading" (Dunning, 15 Sep 2021): "In markets, the past is critical for forecasting the future"; progress needs "a rigorous scientific approach"; simulating AIs against each other is "a poor proxy for the rich complexities and interactions of the real world" (an argument against over-trusting self-play/sim-only results).
- Home page: "HRT is first and foremost a math and technology company."

Independent evidence of what quant practice distrusts:
- Bailey, Borwein, López de Prado, Zhu (J. Computational Finance 2017): standard hold-out is often unreliable for backtests; they estimate the probability of backtest overfitting.
- Wiecki et al. (Quantopian, SSRN 2016, 888 strategies): the Sharpe ratio on the backtest had R^2 < 0.025 for predicting out-of-sample performance; more backtesting went with a larger backtest/live gap.

**Likely rewarded (inference):** out-of-time evidence; baselines; uncertainty; stated limits; a decision rule that is tested, not just a prediction; speed numbers. **Probably not rewarded (inference):** model size, a transformer for its own sake, voice features. The coach and voice serve Handmade/Presentation, not HRT.

---

### 10. Risks: licence, compute, time, demo

| Risk | What I verified | Mitigation |
|---|---|---|
| **Data licence** | Metamon parsed replays card: `license: cc-by-nc-4.0`. Metamon raw replays card: no licence declared in its metadata; it says battles "are publicly available from the Showdown replay API" and usernames are pseudonymised. Metamon code: MIT. Showdown code: MIT. Showdown rules page: nothing on bots/scraping/data use. Privacy policy: Showdown reserves the right to keep chat/battle text logs; says nothing about replays. | Hackathon use is non-commercial; attribute Metamon and Showdown; do not redistribute raw logs in the repo; do not publish de-pseudonymised player data; cache and rate-limit API calls; ask Showdown/organisers if anything goes beyond a demo. Not legal advice. |
| **Replay coverage** | Smogon "Re: Replays" thread: a database upgrade lost data; ladder/Smogtours replays from Sept 2020 rebuilt from chat logs **default to private**; challenge matches after the 2020 backup may be permanently missing. | State sample limits (gap #12). |
| **Compute** | Raw download 5.7 GB; parse a subset; GBM/logistic train in minutes on a laptop (derived). A transformer needs a GPU the team may not have. | Cut the sequence model (§5). |
| **Time** | See §5 estimate. | Ship F1+F2+template coach first. |
| **Demo failure** | Live Showdown, API keys, venue wifi are all single points of failure. | Pre-compute reviews for 3 replays, run offline, template text default, voice optional. |
| **Misleading demos** | A model that sounds confident but is wrong (see the Smogon predictor's user reports). | Show intervals on screen; show a case where the model is uncertain. |

---

### 11. Community consensus and final call

**Professional consensus:** evaluate with proper scoring rules, group/time-aware splits, reliability diagrams with uncertainty (CORP) and cluster-aware intervals; treat win-probability estimates from correlated play-by-play data as high-variance; treat LLM rationales as unfaithful unless every claim is checked against a tool; treat backtests as overfit-prone.

**Community consensus** (weight by agreement and repetition):
- Cross Validated: strong, repeated agreement (top answers 31-35 points) that accuracy is not a proper scoring rule and that log loss/Brier are the right family; ECE-specific threads were not found, so the ECE-criticism comes from the papers (Nixon; Dimitriadis) and the "calibration needs more than one number" view from blogs (WEAK).
- Hacker News: the top Lichess-accuracy thread (169 points) agrees that engine-based accuracy depends on position difficulty and engine error bars; a minority view that centipawn-based accuracy ignores human practical chances. Two other Lichess-accuracy HN submissions have 1-2 points and no comments (no signal). A May 2026 "Show HN: I trained a chess engine to play like humans" (14 points) is adjacent, not used.
- Lichess forum/TalkChess (search summaries only, not opened in full): complaints that harmonic-mean game accuracy punishes one blunder, that Lichess and chess.com numbers differ on the same game (48% vs 69.7% in one report), that +9 to +5 is called a blunder; proposals for position-difficulty weighting. Direction agrees with the HN thread.
- Smogon: the Battle Predictor thread shows users distrusting win probabilities that jump after key KOs or stick above 99%; a separate Smogon article frames luck as hard to separate from skill. No consensus method for luck in replays.
- Reddit: not reachable (the JSON endpoint returned an HTML page), so **no Reddit evidence is included**.

**Final call (professional + community, aggregated):** agree that (1) the metric stack in §3 is right; (2) a win-probability-drop "blunder" is a *useful heuristic with known biases* (difficulty, engine error, rating-dependence), not ground truth; (3) in Pokémon the dice and hidden information are the two things a credible judge will probe, and the fix is to model/flag them openly; (4) LLM commentary must be tool-grounded. Disagreement that remains: whether to use rating-dependent thresholds (chess.com yes, Lichess no): choose and justify; and whether there is a "right" luck metric: there is not, so flag luck rather than subtract it.

---

### 12. Source ledger

Format: verdict · what I opened · what it supports. All opened 2026-10-24 unless noted. Where a tool could not open a page, I say how I verified.

#### KEEP (corroborated or official)
| Source | Opened | Supports |
|---|---|---|
| Lichess, "Accuracy metric" (lichess.org/page/accuracy), official | yes | Win% and accuracy formulas, caveats |
| lila source: `modules/tree/src/main/Advice.scala`, `modules/analyse/src/main/AccuracyPercent.scala`; scalachess `core/src/main/scala/eval.scala` (raw GitHub) | yes | thresholds 0.3/0.2/0.1 on [-1,1] winning chances; +1 uncertainty bonus; winningChances range |
| chess.com support, "How are moves classified" | yes | expected-points thresholds; rating-dependent |
| official-stockfish/WDL_model README | yes | logistic eval-to-win map, depends on material/move count, fitted on fishtest |
| Gneiting & Raftery, JASA 102(477), 2007 | abstract via two repository records; PDF undecodable | strictly proper scoring rules |
| Dimitriadis, Gneiting, Jordan, Vogel, "Evaluating probabilistic classifiers: the triptych" (arXiv 2301.10803) | yes | reliability/ROC/Murphy; score decomposition |
| Dimitriadis, Gneiting, Jordan, PNAS 118(8) 2021, "Stable reliability diagrams..." (CORP) | PMC/KIT/arXiv records via search | CORP diagrams with uncertainty |
| Guo, Pleiss, Sun, Weinberger, ICML 2017 (arXiv 1706.04599) | abstract + PDF text | ECE and reliability-diagram definitions, temperature scaling |
| Nixon et al. 2019 (arXiv 1904.01685) | abstract | ECE binning pitfalls |
| Roberts et al., Ecography 40(8) 2017 | via search summary of abstract (Dryad, Freiburg PDF listed) | block CV vs random CV |
| Kapoor & Narayanan, arXiv 2207.07048 (2022) | yes | leakage taxonomy, info sheets |
| scikit-learn CV docs (GroupKFold, TimeSeriesSplit) | yes (curl) | grouped and time splits |
| Brill, Yurko, Wyner, arXiv 2406.16171 v5 (2025; "Accepted to JQAS") | yes | dependence inflates bias/variance; wide CIs |
| Cameron & Miller, J. Human Resources 50(2) 2015 | abstract via search | cluster-robust inference |
| Grigsby et al., "Human-level competitive Pokemon" (Metamon), arXiv 2504.04395, RLC 2025 + PDF text (Appendix D) | yes | spectator logs; back-filling; reconstruction caveats |
| Metamon repo README + replay-parser README; HF dataset cards (raw, parsed) | yes (curl) | dataset facts, licence, upload-by-choice |
| Smogon thread "Re: Replays" (3732031) | yes | replay DB loss; private-by-default |
| Showdown rules + privacy pages; Showdown LICENSE (MIT) | yes | no scraping rule stated; logs may be kept |
| Fluri, Paleka, Tramèr, "Evaluating superhuman models with consistency checks", arXiv 2306.09983 (2023) | abstract | engine inconsistency; metamorphic tests |
| McIlroy-Young et al., KDD 2020 (Maia), arXiv 2006.01855 | abstract | skill-level human-move prediction; blunder predictor |
| Levine, Kumar, Tucker, Fu, arXiv 2005.01643 (2020) | PDF text | "distributional shift, one of the central challenges with offline RL" |
| Lisý et al., NeurIPS 2013 (MCTS in simultaneous-move games) | via NeurIPS abstract page search | asymptotic convergence to approximate Nash; simultaneous moves |
| Smith & Winkler, Management Science 52(3) 2006 (with 2007 correction to Fig. 3) | abstract via search | optimizer's curse; Bayesian adjustment |
| Hebbar et al., arXiv 2608.04240 (Aug 2026) | yes | 22.0% / >40% incorrect sub-claims; tool augmentation |
| Parfenova, arXiv 2609.22245, BlackboxNLP@EMNLP 2026 | yes | explanations vs decisions |
| Turpin et al., NeurIPS 2023 (arXiv 2305.04388) | yes | unfaithful CoT |
| Lanham et al., arXiv 2307.13702 (2023) | yes | CoT faithfulness varies |
| Jacovi & Goldberg, ACL 2020 (arXiv 2004.03685) | yes | graded faithfulness |
| Ji et al., ACM Comput. Surv. (arXiv 2202.03629) | yes | hallucination in NLG incl. data-to-text |
| Wiseman, Shieber, Rush, EMNLP 2017 (arXiv 1707.08052) | yes | neural vs templated data-to-text |
| Bailey, Borwein, López de Prado, Zhu, J. Computational Finance 2017 | via search records | probability of backtest overfitting |
| HRT pages: /machine-learning/, /hrtbeat/ai-trading/, home | yes | HRT public statements (statements, not criteria) |
| Cross Validated: Q359909 and Q126965 answers (API) | yes | accuracy improper; log vs Brier |
| HN thread 29414065 ("Who is the most accurate world chess champion?") | yes (Algolia API) | accuracy depends on difficulty; eval error bars |
| Glickman, "Glicko system" PDF (glicko.net) | yes | expected-score formula |
| Gama et al., ACM Comput. Surv. 46(4) 2014 | abstract via search | concept drift |

#### WEAK (thin, indirect, or not peer-reviewed)
| Source | Why WEAK |
|---|---|
| PokéAgent Challenge, arXiv 2603.15563 (Mar 2026, NeurIPS 2025 competition track) | abstract only; no metrics read. Use for context only |
| PokéChamp, arXiv 2503.04094 | abstract: >3M games incl. >500k high-Elo; Gen 9 OU; no split on the page. Conflicts with the team's "2M clean, 1.9M/213K" which I could not confirm; venue "ICML 2025" not on the page |
| PokéLLMon, arXiv 2402.01118 | not peer reviewed per page; mitigation effect not quantified |
| Wiecki et al., Quantopian SSRN 2016 | working paper; seen via search summaries; no journal found |
| Smogon Battle Predictor thread; Erdős boot-camp report | forum/student; useful as prior art and failure pattern only |
| Fischhoff 1975 | existence verified via replication atlas; replications mixed (2 of 3 failed) |
| Lichess forum threads, TalkChess, Smogon luck article ("Playing with Loaded Dice") | search summaries only |
| Blogs on ECE/Brier (metricgate etc.) | glossary-level; used only for "pair ECE with a proper score" |
| Smogon suspect-test pages 2026 | show tiering churn in other formats; Gen 9 OU change inside the window unverified |
| "Luck tags / expected post-state" and the leakage-line list (`|win|`, `|raw|`) | derived by me; no source |

#### DO NOT USE (refuted or unsafe) with tombstones
- **"Lichess blunder = 30% / mistake = 20% / inaccuracy = 10% win-chance drop"** (as stated on a forum thread and repeated in search summaries). *Refuted as stated:* lila `Advice.scala` thresholds are on the [-1, +1] winning-chances scale (scalachess `eval.scala`), i.e. 15 / 10 / 5 win-percentage points; a user measurement of sample games agrees. Use 5/10/15 points, cite the code.
- **arXiv 1408.1159** as a "backtest overfitting" source: I opened it; it is Carr & López de Prado, "Determining optimal trading rules without backtesting", not the Bailey et al. overfitting paper. Do not cite for PBO.
- **Smogon Battle Predictor's "95% CI of 8%" and "75-95% accuracy"**: self-reported, accuracy-based, contradicted by users in the same thread; do not quote as performance.
- **"Replays = full information"** (implicit in treating parsed Metamon trajectories as what the player knew): refuted by Metamon Appendix D (back-filled inference). Do not use parsed trajectories for scoring hindsight-free decisions.
- **Reddit-sourced claims**: none used; endpoint unreachable.

---

### 13. Open questions for the team

1. Do we get a real out-of-time test set? Needs a Showdown API pull of Gen 9 OU replays uploaded after 2026-05-19; confirm the API returns them and the rate limit.
2. Is a Smogon-literate teammate available for the 30-turn blind check?
3. Which blunder thresholds (5/10/15 vs 5/10/20 win-probability points)? Pick, then publish a sensitivity table.
4. Are "from scratch" and TIME requirements for Handmade settled with the organisers? (Event doc open question; decides how much effort the physical piece takes from the HRT evidence.)
5. Confirm HRT criteria in the L4 room: does a bot-vs-baseline test count as the "decision" part?
6. Any Gen 9 OU ban/suspect inside the training window? (Check the Smogon Gen 9 OU tiering thread; I found none verified.)

---

# Pass 4, event_rules_prizes (source: `research_notes/OxHack HRT strategy gaps/event_rules_prizes.md`)

## OxHack 26: event rules, schedule, judging and prizes (checked against the team brief)

Researched 2026-10-24 (event day 1). Every time below is UK local time. Saturday is **BST (UTC+1)** and Sunday is **GMT (UTC+0)** because the clocks go back at 02:00 BST on Sunday 25 Oct.

### 1. Summary

- **Hard deadline: hacking finishes 12:00 GMT Sunday 25 Oct** (opening slides, slide 81). Hacking started 12:00 BST Saturday, so that is 25 elapsed hours, which matches the "25 hours of hacking!" slide.
- **Devpost's own deadline is mislabelled.** Devpost shows submissions open "October 24 at 12:00pm EDT" and close "October 25 at 12:00pm EDT", with winners "October 25 at 4:00pm EDT". These are the UK clock times entered under the US Eastern timezone. Taken literally, Devpost opens at 17:00 BST Saturday and closes at 16:00 GMT Sunday. **Plan to submit before 12:00 GMT** and ask the organisers to confirm.
- **Judging runs 13:00–15:45 GMT Sunday in all hacking spaces**, science-fair style, with 4–5 minutes per judge. Closing ceremony is 16:00–16:45 GMT in L1. The Devpost Submission Workshop is 09:00–10:00 GMT Sunday in C1. The brief's three Sunday times are all correct; they just need "GMT" added.
- **Submission requirements (Devpost rules):** "Submit your project on devpost and provide a GitHub link to your project." No video requirement is published. Teams of up to 4. Enrolled university students aged 18+, or within a year of graduating. The Devpost form asks which AI tools you used.
- **The HRT prize has no written criteria** beyond its title and the line "Use your creativity to make the best use of data." The brief's "prediction AND decision plus a backtest" is the team's own reading of the title, not an HRT rule (verdict WEAK). Ask the HRT team in L4.
- **Best Handmade** ("Best Handmade Prize" on Devpost, "Best Handmade Project (With Thanks to Citadel)" on the slides) is **judged by Tom 7 (Tom Murphy VII)**, not by Citadel and not by a "professor". The full criterion is "Get creative and build something from scratch." It never says the build must be physical. Per the organisers' Discord, the TIME theme does apply to it.
- **Unpublished:** how many prizes one project can enter or win, the reward for First, Runner Up, Handmade, HRT and Delta, and OxHack's rules on pre-existing code. MLH's default rules (allow libraries, open source and AI tools if disclosed; all code written during the event) are the only written guide, and OxHack has not said it adopts them.
- **MLH Hardware Lab:** the generic MLH inventory lists **Raspberry Pi Pico / RP2040** (microcontrollers, not a full Linux Pi), Grove sensors, a Grove servo, a Grove LED kit, an LCD, a 7-segment display, and so on. Raspberry Pi devices are collected from the MLH table. The inventory at this event is unconfirmed.

**Source key** (used in the tables below):
- **DP** = Devpost overview https://oxhack-2026.devpost.com/. WebFetch returned 403; curl with a browser user-agent returned the static HTML, which was read in full.
- **DPR** = https://oxhack-2026.devpost.com/rules
- **DPD** = https://oxhack-2026.devpost.com/details/dates
- **ICS** = https://oxhack-2026.devpost.com/calendar
- **DPG** = https://oxhack-2026.devpost.com/project-gallery
- **MLHE** = https://www.mlh.com/events/oxhack-26
- **MLHP** = https://www.mlh.com/events/oxhack-26/prizes (the target of mlh.link/oxhack)
- **OX** = https://26.oxhack.net/
- **SL n** = Opening Ceremony Slides.pdf, page n. Read locally; slide 81 (schedule) and slide 86 (map) are images and were extracted and viewed.
- **DC** = organisers' Discord announcement (research-inputs.md §D)
- **GOV** = https://www.gov.uk/when-do-the-clocks-change
- **HW** = https://www.mlh.com/resources/hardware (the target of mlh.link/hardware)
- **MLHR** = https://github.com/MLH/mlh-policies/blob/main/standard-hackathon-rules.md
- **DEV** = https://dev.to/mlh-hackathon
- **WIKI** = https://en.wikipedia.org/wiki/Tom_Murphy_VII
- MLH partner pages (the mlh.link/X short links redirect here): https://www.mlh.com/partners/elevenlabs, /gemini, https://mlh.com/partners/tigerdata, /snowflake, /solana, /presage, /vultr. hack.mlh.com redirects to the generic https://www.mlh.com/events/prizes.

### 2. Schedule (official)

All rows come from the schedule slide (SL 81) unless a different source is named.

| Day | Time (local) | Timezone | Item | Location | Source / note |
|---|---|---|---|---|---|
| Sat 24 Oct | 09:00–11:00 | BST (UTC+1) | Registration | n/a | SL 81. OX also has `eventDate = 2026-10-24T09:00:00+01:00` and "Registration will open at 9 AM". |
| Sat | 11:00–12:00 | BST | Opening Ceremony | L1 | SL 81 |
| Sat | **12:00** | BST | **Hacking begins** | Open hacking space | SL 81. OX has `hackingDate = 2026-10-24T12:00:00+01:00`. |
| Sat | 12:00–12:15 | BST | Team Building | n/a | SL 81 |
| Sat | 13:00–14:00 | BST | Lunch | Food Collection Point | SL 81 |
| Sat | 14:00–15:00 | BST | Citadel Bubble Tea Drop | Food Collection Point | SL 81 |
| Sat | 15:00–16:00 | BST | HRT talk from Matt Godbolt, "What 25 Days of Optimizations Taught Me About Compilers" | L1 | SL 81 |
| Sat | 17:00 | BST | Devpost submissions technically open (12:00 EDT) | Devpost | DPD, ICS. At 12:42 UTC Saturday DP still said "Submissions open soon". |
| Sat | 17:30–18:00 | BST | MLH Workshop 1 (Intro to Google AI Studio) | C1 ("Classroom 1") | SL 81, SL 43 |
| Sat | 18:00–19:00 | BST | Dinner | Food Collection Point | SL 81 |
| Sat | 19:00–19:30 | BST | MLH Workshop 2 (Hacking with GitHub Copilot) | C1 | SL 81, SL 44 |
| Sat | 20:30–21:00 | BST | Hackathons UK mini event (cup stacking) | C1 | SL 81; SL 75 says "Saturday 20:30 BST". |
| Sun 25 Oct | 00:00–00:30 | BST | HRT Midnight Pizza | Food Collection Point | SL 81. 00:00 BST is 23:00 UTC Saturday. |
| Sun | **02:00 BST → 01:00 GMT** | change | **Clocks go back 1 hour.** Local 01:00–02:00 happens twice. | n/a | GOV: "back 1 hour at 2am on the last Sunday in October", 25 October 2026. SL 82: "25 hours of hacking!" |
| Sun | 08:00–09:00 | GMT (UTC+0) | Breakfast | Food Collection Point | SL 81 |
| Sun | 09:00–10:00 | GMT | **Devpost Submission Workshop** | C1 | SL 81 |
| Sun | **12:00** | GMT | **Hacking finishes** (the planning deadline) | n/a | SL 81. 12:00 BST Sat to 12:00 GMT Sun is 25 h, which matches SL 82. |
| Sun | 12:00–13:00 | GMT | Lunch | Food Collection Point | SL 81 |
| Sun | **13:00–15:45** | GMT | **Judging**, science fair, 4–5 min per judge | All hacking spaces | SL 81 for time and place; DC for format |
| Sun | 16:00 | GMT | Devpost submissions technically close (12:00 EDT) | Devpost | DPD, ICS. This conflicts with SL 81 and is almost certainly a timezone mistake; see §4. |
| Sun | 16:00–16:45 | GMT | Closing ceremony | L1 | SL 81. DPD's "Winners Announced October 25 at 4:00pm EDT" is the same clock time with the wrong zone. |
| Sun | 16:45–17:00 | GMT | Final group photo | n/a | SL 81. OX's "finish by 4:30 PM Sunday" is stale. |
| Sun | 20:00 | GMT | Devpost "Winners Announced" if read literally (16:00 EDT) | Devpost | DPD. Do not use. |

Day One is BST and Day Two is GMT. The only zone written on the slides is "Saturday 20:30 BST" (SL 75). The Sunday times are taken to be GMT because the "25 hours of hacking" slide only adds up if 12:00 Sunday is GMT.

Practical notes:
- Phones and laptops change automatically. Any script that logs timestamps (for example bus or replay data) should store **UTC**, or the repeated 01:00–02:00 hour will produce duplicate or out-of-order local times.
- The ICS file sets `TZID:America/New_York` with US daylight saving ending 1 Nov 2026. So Devpost's EDT really is UTC−4 this weekend: 12:00 EDT = 16:00 UTC (ICS).

Venue: Oxford Mathematical Institute (DP: "Mathematical Institute"; ICS: "Radcliffe Observatory Quarter, 35 Woodstock Rd, Oxford OX2 6GG, UK").
- Rooms (SL 86): L1 ceremonies & talks; C1 mini events & workshops; C2–C3 hacking; C4–C5 sleeping/resting; C6 organiser room; **L4 HRT dedicated room**; L5 quiet hacking; L6 hacking; café area = hacking and food collection.

### 3. Prizes, judging and submission rules

#### 3a. Prize table

DP lists "13 non-cash prizes", each with "1 winner". The DEV Writing Challenge is listed by MLH (MLHE, MLHP) but is **not** on Devpost, so it makes 14 in total.

| Prize | Exact criteria (verbatim) | Requirements / notes | Reward | Source |
|---|---|---|---|---|
| **First Place** | "This is a general prize catergory. Awarded by OxHack Committee and friends." | TIME theme applies (DC). Judged on the Devpost criteria: Creativity, Technicality, Completeness, Presentation/Hackathon Spirit (no weights published). | **Unknown** (non-cash) | DP, DC |
| **Runner Up** | "This is a general prize category. Awarded by OxHack and friends." | Same as First Place. | **Unknown** | DP, DC |
| **Best Handmade Prize** (slides: "Best Handmade Project" (With Thanks to Citadel)) | "Judged by Tom 7! Get creative and build something from scratch. This challenge is with thank to Citadel." | Judge: **Tom Murphy VII (Tom 7)** (DP judges list), described as "a computer scientist and YouTuber" known for playful CS projects such as NES AI, "reverse-emulation" and SIGBOVIK papers (WIKI). The TIME theme applies (DC lists it as a general prize). There is **no** stated requirement that the build be physical. Appears under "Sponsor Prizes" in the gallery filter (DPG), so it is probably an opt-in tick-box on Devpost (inference). | **Unknown** | DP, SL 85, DC, WIKI |
| **[HRT] Best Use of Data for Predictions and Decision Making** | "Use your creativity to make the best use of data." | That line is the only written criterion. The HRT slide is title-only (SL 21). Judges are not named on DP. HRT does not need to fit TIME (DC). The HRT recruiting slides stress latency, big data and ML for roles (SL 14–18); those are **not** prize criteria. | **Unknown** | DP, SL 21, DC |
| **Built with Delta** (Zed, per DC) | "Show off how you worked together in Delta. Extra points for projects that solve real problems." Weights: **Speed & Performance 30%** ("Does it feel fast? Is the UX snappy and responsive?"), **Technical Implementation 25%** ("Clean code, smart architecture, good use of Rust or collaboration features"; SL 29 omits "Rust or"), **Innovation 25%** ("Fresh idea. Real problem. New angle."), **Polish & Usability 20%** ("Would you actually use this? Does it delight?") | "Use Delta from brainstorming/ideation, building, all the way through testing. **Share your Delta threads** to show examples of how you collaborated." Download from delta.dev; use OpenRouter tokens. | **Unknown** | DP, SL 27–30 |
| **[Hackathons UK] Hackiest Hack** | "Build something over-the-top over engineered and held together with string. Use your imagination." | Judge Holly Packer (Hackathons UK) is on DP's judge list. Which prize she judges is inferred. | "Shark Plushes for each team member" | DP, SL 74 |
| **[MLH] Best Use of Gemini API** | "push the boundaries of what's possible with AI using Google Gemini. Check out the Gemini API to build AI-powered apps that make your friends say WHOA." | Must use the Gemini API. API key from mlh.link/aistudio (SL 43). MLH workshop Sat 17:30 C1. | DP/MLHP: "MLH Swag Kits"; SL 47: "MLH + DEV Swag Bags" | DP, MLHP, SL 47 |
| **[MLH] Best Use of ElevenLabs** | "Deploy natural, human-sounding audio with ElevenLabs… Integrate fully autonomous audio experiences into your hack with ElevenLabs and give your project a voice" | Credits: the week of the event, MLH emails registered hackers a promo code for "a free 1-month ElevenLabs Creator subscription" (partner page). | DP/MLHP: "Wireless Earbuds"; SL 48: "Beats Solo Earbuds" | DP, MLHP, SL 48, partners/elevenlabs |
| **[MLH] Best Use of Tiger Data** | "The team that demonstrates the most innovative, impactful, and performance-driven use of Tiger Data will take home some great prizes!" The pitch mentions time-series metrics, Continuous Aggregates, compression, and "financial prediction engines". | New signups get "$1,000 in complementary credits, valid for 30 days" via mlh.link/tigerdata-quickstart (partner page). Tiger Data extends PostgreSQL. | "Stream Deck Mini" | DP, MLHP, SL 49, partners/tigerdata |
| **[MLH] Best Use of Snowflake API** | "Play with industry-leading LLMs on a single account using the Snowflake APIs… Build customized applications, RAG powered chat bots, or embed AI-powered features into your app" | 120-day free student trial (mlh.link/snowflake-signup). The Devpost wording centres on **LLM/AI features via the Snowflake REST API**. SL 50's tagline is "Turn big data into big ideas". | DP/MLHP: "Arduino Student Kit"; SL 50: "Arduino Kits" | DP, MLHP, SL 50, partners/snowflake |
| **[MLH] Best Use of Solana** | "Create a game, social app, or consumer product that relies on instant, high-frequency transactions. Design a sophisticated trading, lending, or decentralized exchange (DEX)…" | "Integrate Solana into your next hack to qualify for the Best Use of Solana prize category"; build on DevNet using the faucet (partner page). | DP/MLHP: "Unruggable Hardware Wallets" ("for you and each member of your team"); SL 51: "Assorted Prizes" | DP, MLHP, SL 51, partners/solana |
| **[MLH] Best Use of Presage** | "Use any of the Presage SDKs to integrate capabilities like real-time heart rate, breathing rate, engagement levels, and facial expressions into your hack" | SDKs for iOS, Android and C++ (partner page). Perks: free development-credit refills for 3 months, and 30% off usage for the first year after going live (DP). | "Fitbit Inspire & Presage Perks" (SL 52: "Fitbit Inspires") | DP, MLHP, SL 52, partners/presage |
| **[MLH] Best Use of Vultr** | "push the limits of what can be built when infrastructure is no longer the bottleneck… Take your next hack to the cloud with Vultr" | $100 credits via a promo code at mlh.link/vultr-signup (partner page). | DP/MLHP: "**M5Stack Official Tab5**"; SL 53: "Portable Screens" | DP, MLHP, SL 53, partners/vultr |
| **DEV Writing Challenge** (MLH × DEV, monthly) | "Publish a post during the current challenge window explaining what you built, how it works, and what you learned. Include #mlhacks." Selection weighs "technical substance, originality, clear storytelling, and community popularity." | Not on Devpost and not judged at OxHack. The DEV editorial team picks "at least one favorite project" each calendar month (Eastern Time). | "$100 Per selected project" | DEV, MLHP, SL 54 |

**Judges listed on Devpost (DP):** OxHack Committee & Volunteers; Holly Packer (Hackathons UK); Oscar Ryley (MajorLeagueHacking); Tom Murphy VII.
- **No HRT judge is listed**, and neither is a Zed/Delta judge.
- No source maps judges to prizes, except that Tom 7 is named as the Handmade judge.

**General judging criteria (DP):** Creativity · Technicality · Completeness · Presentation/Hackathon Spirit. No weights are published. These presumably apply to the general prizes; no source says so.

**MLH default judging criteria (MLHR, if adopted):** Technology, Design, Completion, Learning, weighed equally. These are used "for MLH digital events or MLH categories at an in person event". MLHR explicitly does *not* judge code quality, pitch quality, idea quality, or how well the project solves a problem, and says "Pitches and presentations are discouraged". OxHack has not said it adopts MLHR; OX and SL 88 only cite the MLH **Code of Conduct**.

**Judging format:**
- Science fair, "4–5 minutes per judge to explain the project (demo, presentation, anything)" (DC).
- 13:00–15:45 GMT, "All hacking spaces" (SL 81).
- MLH "I Demoed" stickers for showing off on Sunday (SL 56).

#### 3b. Submission, eligibility and conduct rules

| Topic | Official position | Source |
|---|---|---|
| What to submit | "Submit your project on devpost and provide a GitHub link to your project." The "What to Submit" heading on DP is empty. | DPR, DP |
| Demo video | **Not required** by any OxHack source. MLH's 2-minute video rule applies only to "fully digital hackathons that MLH hosts". Whether the Devpost form makes a video mandatory is unknown; ask at the 09:00 workshop. | DPR, MLHR |
| Delta threads | Required only for Built with Delta: "Share your Delta threads". | DP, SL 27 |
| AI tool disclosure | The Devpost gallery filter asks "Which of the following AI tools did you use this weekend?" (OpenAI, Anthropic, Hugging Face, Gemini, OpenRouter, ElevenLabs, … "I did not use GenAI"). It is therefore a question on the submission form. MLHR allows AI coding tools if teams are "honest and transparent… listing them in their project submissions". | DPG, MLHR |
| Selecting prizes | DPG lists 11 "Sponsor Prizes" as filters, including Best Handmade and Hackiest Hack but not First or Runner Up. This suggests teams **opt in** to each of those prizes on the form (inference). DC: "You can combine to be judged for both [general + sponsor], or skip the main track and submit only to sponsor prizes." | DPG, DC |
| Max prizes entered / won per project | **Not published anywhere.** | DP, DPR, DC (silent) |
| Team size | "Teams can have up to 4 people!" Solo is allowed ("welcome to work independently"). | OX |
| Eligibility | "enrolled university students across the UK, aged 18+, or within a year of having graduated". Non-UK university students should contact committee@oxhack.net. DPR: "Enrolled university student (18+)." DP sidebar: "Above legal age of majority in country of residence; Students only; Only specific countries/territories included." | OX, DPR, DP |
| Devpost registration | Teams must "Join hackathon" on Devpost. Only 3 participants were registered when fetched on Saturday. | DP |
| Pre-existing code / ideas | **OxHack and Devpost say nothing.** MLHR defaults: "All work on a project should be done during the period of the hackathon"; "Teams can use an idea they had before the event"; "Teams can use libraries, frameworks, or open-source code"; pre-building code and open-sourcing it for the event "is not allowed"; small bug fixes are allowed after time is up, but not new features. | MLHR |
| Pre-existing data / pretrained models | No rule in any source. Public datasets and libraries look consistent with MLHR's open-source allowance (inference). Confirm with the organisers before relying on pretrained models or data you processed before 12:00 BST Saturday. | n/a |
| Public code | MLHR: "Your code must be available publicly" and "must remain public post event to be eligible for prizes". This is the MLH default; DPR only asks for a GitHub link. | MLHR, DPR |
| Code of Conduct | MLH Code of Conduct. Incidents: incidents@mlh.io, +44 (0) 800 808 5675. | OX, SL 62, SL 88 |
| Theme | TIME (SL 84). Applies only to First, Runner Up and Best Handmade; sponsor prizes "don't have to fit TIME" (DC). DP's "There's no required theme" is older and superseded for the general prizes. | SL 84, DC, DP |

#### 3c. MLH Hardware Lab

- **Slide (SL 42):** "Check out some hardware for your project. Arduino, Raspberry Pi, and much more! Get Started: mlh.link/hardware". The MLH event page lists a "Digi-key Hardware Lab" sponsor (MLHE).
- **Inventory on the generic MLH page (HW), not specific to this event:**
  - **Raspberry Pi Pico and RP2040** ("Visit the MLH table to pick up your device")
  - Arduino IDE guidance ("Picking up any Arduino hardware at the MLH hardware lab"); no specific Arduino board is named
  - Google Home Mini, Logitech webcam, JBL Go 3 speaker
  - Grove modules: buzzer, touch, **LED Socket Kit**, temp/barometer, button, **rotary angle**, sound, accelerometer, light, colour, **LCD screen**, **stepper motor**, ultrasonic, moisture, **Motor/Servo Driver Board**, air quality, micro switch, joystick, UV, NFC/RFID, IR reflective, **7-segment display**, stepper + driver, **Grove Servo**, cables
  - Brushless DC motors, jumper wires, capacitors, resistor kit, breadboards
  - Tools (wire stripper, cutter, tweezers, pliers, multimeter): "This stays at the hardware lab for the duration of the event"
- **How to borrow:** collect from the MLH table or hardware lab. HW gives no ID or deposit rules, and no UK-specific inventory was found.
- **Implication for a "hand-built Raspberry Pi dial":** the listed Pi is a **Pico** microcontroller. No full Pi and no "Pico W" (Wi-Fi) is listed. A networked dial may need to be driven from a laptop over USB serial, or use the team's own hardware (inference). Check stock at the MLH table (Oscar Ryley, MLH coach, SL 36).

### 4. Claim ledger

Ordered KEEP first, then WEAK, then DO NOT USE.

| Claim (where it appears) | Verdict | Sources | Correction / note |
|---|---|---|---|
| Hacking ends 12:00 Sunday (brief A) | **KEEP** | SL 81; SL 82; OX `hackingDate` 12:00+01:00 | It is **12:00 GMT** (UTC+0), 25 h after the 12:00 BST start. Treat it as the Devpost deadline too (see the DO NOT USE row on the Devpost EDT deadline). |
| Devpost Submission Workshop 09:00–10:00 Sunday (brief A) | **KEEP** | SL 81 | 09:00–10:00 **GMT**, room **C1**. |
| Judging 13:00–15:45 "at your table" (brief A) | **KEEP** | SL 81 ("All hacking spaces"); DC (science fair) | 13:00–15:45 **GMT**, in all hacking spaces. Closing ceremony 16:00–16:45 L1. |
| Judging is science fair, 4–5 min per judge (DC) | **KEEP** | DC; consistent with SL 81 | Only the Discord states the per-judge length; it is the organisers' own word. Expect several judges per table over 2 h 45 min. |
| TIME applies only to First, Runner Up, Best Handmade; sponsor prizes needn't fit (DC) | **KEEP** | DC; SL 84; no sponsor prize text on DP mentions TIME | Supersedes DP's "no required theme" for the general prizes. |
| UK clocks go back Sunday 25 Oct 2026, 02:00 BST → 01:00 GMT; 25 hours of hacking (SL) | **KEEP** | GOV; SL 82 | Saturday times are BST and Sunday times GMT. Log data in UTC. |
| HRT dedicated room is L4 (SL) | **KEEP** | SL 86 | n/a |
| Zed "Built with Delta" weights 30/25/25/20; share Delta threads (SL, DC) | **KEEP** | DP; SL 27–30 | DP's Technical Implementation line adds "good use of **Rust** or collaboration features". |
| Prize list (DC) | **KEEP** | DP (13 prizes); MLHE/MLHP (8 MLH incl. DEV) | DEV Writing Challenge is not on Devpost; DEV editors choose it monthly, not OxHack judges. DC's "Best of Data…" is a typo for "Best **Use** of Data…". |
| Matt Godbolt's HRT talk is on optimisation (brief A) | **KEEP** | SL 81 | "What 25 Days of Optimizations Taught Me About Compilers", Sat 15:00–16:00 BST, L1. |
| Google AI Studio workshop 17:30 Classroom 1; GitHub Copilot 19:00 (SL) | **KEEP** | SL 43–44; SL 81 | 17:30–18:00 and 19:00–19:30 BST, C1. |
| Cup stacking Saturday 20:30 BST (SL) | **KEEP** | SL 75; SL 81 | 20:30–21:00, C1. |
| Tiger Data "30-day free trial" (brief A) | **KEEP** | partners/tigerdata | More precisely: "$1,000 in complementary credits, valid for 30 days". |
| MLH Hardware Lab has Arduino, Raspberry Pi and more (SL) | **KEEP** (with nuance) | SL 42; HW; MLHE | The listed Pi is **Pico/RP2040**, with Grove servos, LEDs and sensors. Event stock is unconfirmed. |
| "What HRT needs: both a prediction AND a decision, plus a backtest showing the decision beats a simpler rule" (brief A) | **WEAK** | DP ("Use your creativity to make the best use of data."); SL 21 (title only) | Not a published criterion. The title supports "prediction + decision"; the backtest is the team's strategy, not an HRT rule. Ask the HRT team in L4. |
| "HRT cares about latency" (brief A) | **WEAK** | SL 14–18 (HRT roles and culture); SL 81 (Godbolt talk) | Latency is a theme of HRT's recruiting pitch, not of the prize text. A cheap bonus at most. |
| "Citadel Handmade" and "the professor judge" (brief A) | **WEAK** | DP; SL 85; WIKI | Official name "Best Handmade Prize" / "Best Handmade Project (With Thanks to Citadel)". Citadel is thanked as sponsor. The judge is **Tom 7 (Tom Murphy VII)**, whom WIKI calls a computer scientist and YouTuber (PhD CMU). No source calls him a professor. |
| Handmade rewards "craft, play, making for its own sake; a physical poetic element" (brief A) | **WEAK** | DP ("Get creative and build something from scratch."); WIKI (playful projects) | "Physical" is never stated. "From scratch" may mean building the software yourself, for example avoiding heavy libraries. Playfulness fits Tom 7's public work (inference). Ask the organisers. |
| "TIME theme optional" (user, §F) | **WEAK** | DC | True for HRT and MLH. **False for Best Handmade**, which per DC is judged with TIME. If you want Handmade, fit TIME. |
| Momentum's "clear fit with the TIME theme" as a reason it can win (brief A) | **WEAK** | DC | TIME is irrelevant to HRT judging; it matters only for First, Runner Up and Handmade. |
| "Honest Clock fits HRT, Citadel Handmade and Tiger Data in one build" (brief A) | **WEAK** | DC; DPG | Combining general and sponsor prizes is allowed (DC). How many prizes one project may enter or win is **unpublished**. |
| "Pitch about 2 minutes; show decision beating baseline within 60 s" (brief A) | **WEAK** | DC; MLHR | Each judge gives 4–5 min. Prepare a demo-first 4-minute walkthrough with Q&A, repeated for each judge; keep the 60-second hook. MLHR says demos beat pitches. |
| "Judges may read code" (brief A) | **WEAK** (plausible) | DPR (GitHub link required); DP Delta criteria (clean code); MLHR (code quality not judged) | Keep the repo clean and public. Only Delta's criteria explicitly score code. |
| Optional extras "Gemini narrates; Tiger Data stores per-turn data" make MLH prizes reachable (brief A) | **WEAK** | DP (Tiger Data: "most innovative, impactful, and performance-driven use") | MLH prizes reward a central "best use". Incidental use is unlikely to win. |
| Vultr prize = "portable screens"; Solana = "assorted prizes"; Gemini = "swag bags" (SL, §E) | **WEAK** | DP; MLHP vs SL 47/51/53 | Devpost/MLH: Vultr **M5Stack Official Tab5**; Solana **Unruggable Hardware Wallets** (per member); Gemini **MLH Swag Kits**; ElevenLabs "Wireless Earbuds" (slides: Beats Solo); Snowflake "Arduino Student Kit"; Presage "Fitbit Inspire & Presage Perks". |
| "Hand-built Raspberry Pi dial" using lab hardware (brief A) | **WEAK** | HW | The lab lists Pi **Pico**/RP2040, not a networked full Pi. Check stock at the MLH table or bring your own. |
| OX: "expect the event to finish by 4:30 PM on Sunday" | **WEAK** (stale) | SL 81 | Closing ceremony 16:00–16:45, group photo to 17:00 GMT. |
| Devpost deadline "October 25 at 12:00pm EDT" taken literally (= 16:00 GMT) | **DO NOT USE** | DPD; ICS; vs SL 81 | The clock times match the UK schedule (12:00 start, 12:00 end, 16:00 winners), so the timezone is wrong. Submit by **12:00 GMT**. The portal may stay open later, but late work breaks the "Hacking Finishes 12:00" rule. |
| Devpost "Winners Announced October 25 at 4:00pm EDT" (= 20:00 GMT) | **DO NOT USE** | DPD; SL 81 | Winners at the closing ceremony, 16:00 GMT, L1. |
| MLH event page time "Sat, Oct 24 · 1:11 AM – Sun, Oct 25 · 9:00 PM UTC" | **DO NOT USE** | MLHE vs OX, SL 81 | Placeholder times. Use the schedule in §2. |
| DP overview "There's no required theme or problem to solve" | **DO NOT USE** (for general prizes) | DC; SL 84 | TIME is the theme for First, Runner Up and Best Handmade. |

### 5. Open questions and who to ask

| # | Question | Why it matters | Ask |
|---|---|---|---|
| 1 | Is the real Devpost deadline 12:00 GMT Sunday? Devpost shows 12:00 **EDT** (= 16:00 GMT), and submissions don't open until 17:00 BST Saturday. | Avoid a late or blocked submission. | Organisers on Discord (Kaal / OxHack Strategy); confirm at the Devpost workshop, 09:00 GMT C1 |
| 2 | Can one project enter several prizes (HRT + Best Handmade + Tiger Data + ElevenLabs)? Can it win more than one? Is there a cap? | Decides whether to stack tracks or focus on HRT. | Organisers on Discord |
| 3 | For Best Handmade, is TIME a hard eligibility rule or one judging factor? | The user listed TIME as optional, but DC says it applies to Handmade. | Organisers on Discord (Kaal) |
| 4 | What counts as "handmade / build something from scratch"? Must there be a physical object? Is a software-only from-scratch build eligible? Are heavy libraries, pretrained models or AI coding tools penalised? | The brief assumes a physical dial; the official text doesn't require one. | Organisers on Discord; Tom 7 himself if reachable before judging |
| 5 | How will the HRT prize be judged, and by whom? (HRT staff at your table, or demos in L4? Weight on prediction quality vs decision quality vs data use vs latency? Rewards?) | The only written criterion is "make the best use of data". | HRT team in **L4**: Joshan Parmar (Algo Developer), Ronette Yeboah, Charlotte Whittington-Firth |
| 6 | What are the rewards for First, Runner Up, Best Handmade, HRT and Built with Delta? | All unpublished ("13 non-cash prizes"). | Organisers on Discord |
| 7 | What must a Devpost submission contain? Is a video required? Must the GitHub repo be public? Can it be edited after 12:00? | DPR only says "Devpost + GitHub link". | Devpost Submission Workshop, 09:00–10:00 GMT Sunday, C1 |
| 8 | Do MLH's standard rules apply (all code written during the event, public repo, AI disclosure)? Are datasets or pretrained models prepared before 12:00 BST Saturday OK? | Momentum relies on public replay datasets and libraries. | Organisers on Discord; MLH coach Oscar Ryley at the MLH table |
| 9 | What hardware does the lab actually have here (Pico W? full Raspberry Pi? Arduino boards? servos)? Is ID or a deposit needed, and when must it be returned? | Needed for the Handmade or Honest Clock dial. | MLH table / hardware lab (Oscar Ryley) |
| 10 | Do judges find teams by a table number entered on Devpost? Must we stay at our table for the whole 13:00–15:45 window? | Missing a judge in a science fair means losing that judge's score. | Organisers on Discord or at the workshop |
| 11 | Who judges Hackiest Hack and the MLH prizes? Do the MLH criteria (Technology, Design, Completion, Learning) apply? | Shapes what to show each judge. | Oscar Ryley (MLH), Holly Packer (Hackathons UK) |

Gaps and fetch notes:
- WebFetch got 403 on Devpost; curl with a browser user-agent returned the full static HTML for the overview, rules, dates, gallery, updates and discussions pages. The Devpost "Updates" and "Discussions" pages were empty.
- The Devpost submission form is behind a login and was not seen.
- No OxHack website schedule page exists (404s on /schedule etc.). The authoritative schedule is the image on slide 81.
- The MLH partner pages carry no prize criteria; Devpost holds the official prize wording.
- The Discord announcement (DC) could not be re-fetched and is taken from research-inputs.md §D.

---

# Pass 5, handmade_coaching_voice (source: `research_notes/OxHack HRT strategy gaps/handmade_coaching_voice.md`)

## Handmade element, coach-style replay review, ElevenLabs and Gemini (Momentum / OxHack 26)

Researcher notes. All pages read on **2026-10-24** unless stated otherwise. "Inference" marks my own reasoning, not a sourced fact. Time estimates are my estimates for a team new to the parts, not sourced numbers.

---

### 1. Summary

1. **The Handmade judge is Tom Murphy VII ("Tom 7"), not a generic committee or professor.** Devpost: "Best Handmade Prize — Judged by Tom 7! Get creative and build something from scratch. This challenge is with thank[s] to Citadel." ([OxHack Devpost](https://oxhack-2026.devpost.com/)) He made "Elo World", a SIGBOVIK 2019 paper and video, "30 Weird Chess Algorithms", that rates deliberately bad chess engines, including **worstfish** (it plays Stockfish's worst move) and Stockfish mixed with random moves. ([tom7.org/chess](http://tom7.org/chess/), [Elo World PDF](http://tom7.org/chess/weak.pdf)) A coach that scores game decisions sits squarely in his territory. Pitch the playful, from-scratch side, not polish.
2. **Best physical build: an analog "Momentum Meter".** A hand-made cardboard dial with a servo needle shows P(win). A knob scrubs the turns (TIME: rewind) and a big button says "coach me". The laptop runs everything and talks to an Arduino or Pico over **USB serial**, with no Pi OS and no Wi-Fi. Estimate: 4–6 h for one person. Every part except the strip LEDs is on MLH's hardware list (Grove servo, rotary angle sensor, button, Pico/Arduino). ([MLH hardware](https://www.mlh.com/resources/hardware))
3. **Avoid a Raspberry Pi as the servo driver.** Software PWM jitters on Linux. pigpio does not support the Pi 5. Setup and Wi-Fi add risk. A microcontroller with hardware timers or PWM is the low-risk path. ([gpiozero changelog](https://gpiozero.readthedocs.io/en/v2.0.1.post3/_sources/changelog.rst.txt), [Pi4J pigpio](https://www.pi4j.com/documentation/providers/pigpio), [SunFounder Pi 5](https://docs.sunfounder.com/projects/davinci-kit/en/latest/for_pi5.html))
4. **Coaching review: copy the Chess.com and Lichess pattern.** Show key moments, label each move by win-probability lost, and show the stronger move. Chess.com bands, in expected points lost: Inaccuracy 0.05–0.10, Mistake 0.10–0.20, Blunder >0.20. Lichess: 0.1/0.2/0.3 on a −1..+1 scale, which is **5/10/15 percentage points**. Both come from verified primary sources. ([Chess.com](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-and-etc), [lila Advice.scala](https://raw.githubusercontent.com/lichess-org/lila/master/modules/tree/src/main/Advice.scala), [scalachess eval.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/eval.scala))
5. **Ground every number.** Build a facts JSON in code, then a deterministic template, then an optional LLM paraphrase. Run a validator that rejects any number or move name not in the facts, and fall back to the template if it fails. A 2026 paper found GPT-5.4 without tools makes incorrect sub-claims in chess commentary **22.0%** of the time, and smaller open models over 40%. ([ACT-Eval, arXiv 2608.04240](https://arxiv.org/abs/2608.04240))
6. **ElevenLabs (optional).** The free tier gives 10,000 credits a month, is non-commercial, needs "elevenlabs.io" or "11.ai" in the title when published, and gets no voice-library voices over the API. MLH emails a free 1-month Creator code the week of the event. Current models: `eleven_v4` (flagship, launched 2026-09-28), `eleven_v4_turbo` (~100 ms) and `eleven_flash_v2_5` (~75 ms, cheapest). **Pre-generate and cache MP3s** for the demo replays. ([pricing](https://elevenlabs.io/pricing), [models](https://elevenlabs.io/docs/overview/models), [MLH ElevenLabs](https://www.mlh.com/partners/elevenlabs))
7. **Gemini (optional).** Google no longer publishes free-tier RPM/RPD; you check them per project in AI Studio. Third-party reports say about 20 RPD for 3.x Flash and about 500 RPD for Flash-Lite. Make **one structured-output call per replay** and cache it. Current IDs: `gemini-3.8-flash` and `gemini-3.5-flash-lite`. ([rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [models](https://ai.google.dev/gemini-api/docs/models), [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes))
8. **Ethics and IP.** Use a stock voice and never clone a real person. ElevenLabs' policy bans cloning any living person without explicit consent. Leave Pokémon sprites and logos out of the public repo and the physical build: Nintendo and TPC take down fan projects, mostly at the distribution point. ([ElevenLabs use policy](https://elevenlabs.io/use-policy), [Engadget](https://www.engadget.com/2018-08-29-pokemon-essentials-nintendo-takedown.html), [Axios](https://www.axios.com/2022/01/24/fan-made-game-escapes-nintendo))

---

### 2. Physical build options

Context: MLH's generic hardware list (not confirmed for OxHack's stock) includes Raspberry Pi Pico / RP2040, Arduino IDE, Grove Servo, Grove Motor/Servo Driver Board, Grove Rotary Angle sensor, Grove Button, Grove LCD, Grove 7-Segment display, Grove LED Socket Kit, stepper motors, breadboards, jumpers, ceramic capacitors, a resistor kit, a JBL Go 3 speaker, and lab tools (multimeter, strippers, tweezers). Tools stay in the lab. "Arduino hardware" is collected at the MLH hardware lab and "the Raspberry Pi" at the MLH table. **NeoPixel strips and e-ink displays are not listed.** ([MLH hardware](https://www.mlh.com/resources/hardware))

| Option | Parts | Time (est.) | Risk | Handmade appeal | Sources |
|---|---|---|---|---|---|
| **A. Servo P(win) needle ("Momentum Meter")**. **Recommended.** Laptop sends `P\n` over USB serial and the needle sweeps as the replay plays. | Arduino Uno/Nano or Pico + SG90 / Grove Servo + 470–1000 µF capacitor across servo power + cardboard / foam-board / papier-mâché dial face, hand-lettered 0–100% with turn ticks + pyserial on the laptop | Electronics 1–1.5 h; calibration 0.5 h; dial craft 2–3 h; **total ~4–6 h** | **Jitter:** low on Arduino, since the Servo lib drives pulses from a hardware timer (attach defaults 544–2400 µs, 20 ms refresh, and PWM is lost on that timer's pins). Pi software PWM is the main jitter source. **Power:** SG90 draws ~10 mA idle, 100–250 mA moving, up to 360 mA stalled. One servo off the board's 5 V is OK for experiments, but an external supply is better. Add the capacitor. **Range:** don't drive into the end-stops (noise, stall current); calibrate min/max. Spec ~0.1 s/60°, 4.8–6 V. | **High.** Analog, tactile, legible from a distance. The judge himself reportedly built a papier-mâché robot for his chess video (single source, WEAK). Physical motion fits TIME. | [Servo.h](https://raw.githubusercontent.com/arduino-libraries/Servo/master/src/Servo.h), [ProtoSupplies SG90](https://protosupplies.com/product/servo-motor-micro-sg90/), [SG90 datasheet](https://bit.nkust.edu.tw/~csshieh/teach/111A/mc/datasheet/SG90.pdf), [devjournal](https://devjournal.balinterdi.com/30-weird-chess-algorithms/) |
| **B. "Rewind" knob (turn scrubber)**. Add-on to A. | **Grove Rotary Angle Sensor**: a 10 kΩ potentiometer, 300°, linear, analog 0–Vcc, 4.75–5.25 V. Map the ADC value to a turn index. Better than a rotary encoder: absolute position, no debounce or interrupts, and it's on MLH's list. | 1–1.5 h | Low. Analog noise causes flicker between turns; fix with a moving average plus a hysteresis band. A 5 V sensor into a 3.3 V Pico ADC needs the sensor powered from 3.3 V (inference; check on the bench). | **High.** Turning a knob to move time backward is the TIME theme in your hand. | [Seeed wiki](https://wiki.seeedstudio.com/Grove-Rotary_Angle_Sensor/), [MLH hardware](https://www.mlh.com/resources/hardware) |
| **C. Big "Coach me" button**. Add-on. | Grove Button (or an arcade button if you have one) wired to a digital pin. Laptop plays the cached narration for the current turn. | 0.5–1 h | Low. Needs debounce in firmware. | Medium-high: an obvious interaction for science-fair judging (4–5 min per judge). | [MLH hardware](https://www.mlh.com/resources/hardware), research-inputs §D |
| **D. LED "eval bar"** | WS2812/NeoPixel strip (**bring your own; not on MLH list**) or Grove LED sockets / 7-segment. 300–500 Ω data resistor at the pixel end, 500–1000 µF capacitor, 5 V data needed (3.3 V Pico needs a 74AHCT125 level shifter), shared ground, solder rather than alligator clips. MicroPython has a built-in `neopixel` module on RP2. | 2–3 h | Medium. Logic-level problems on 3.3 V boards, parasitic power through the data line if the power-up order is wrong, flaky clip connections. | Medium. Reads like a product, not craft, unless diffused in a hand-made enclosure. | [Adafruit best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices), [MicroPython rp2 quickref](https://docs.micropython.org/en/latest/rp2/quickref.html) |
| **E. E-ink "coach card"** (shows "Turn 14 · Mistake · −19 pts") | Waveshare 2.13" B/W (250×122, SPI, 3.3 V) + Pi or Pico driver (**not on MLH list**) | 3–5 h | Medium-high. Full refresh takes **2 s** (partial 0.3 s); the red/black/white variant takes ~15 s full. Driver/library setup time. Too slow to animate a needle-style timeline. | Medium. Pretty, but a bought module. | [Waveshare spec](https://www.waveshare.com/2.13inch-e-paper.htm) |
| **F. Pi-hosted everything** (Pi runs the model, web UI and servo) | Raspberry Pi 4/5 + SD card + servo | 6–10 h | **High.** OS flashing and first boot. Venue Wi-Fi may be WPA2-Enterprise/eduroam (needs NetworkManager/PEAP config). gpiozero's default factory uses software PWM, and v1.6.0 added a warning for servos on the default factory. pigpio (the old jitter fix) **does not support the Pi 5** (RP1 chip), and gpiozero 2.0.1.post3 dropped its "use pigpio to fix servo jitter" warning. Hardware PWM on Pi 5 is on GPIO12/13/18/19 via `rpi-hardware-pwm`. | Same as A, but more can break. | [gpiozero changelog](https://gpiozero.readthedocs.io/en/v2.0.1.post3/_sources/changelog.rst.txt), [Pi4J](https://www.pi4j.com/documentation/providers/pigpio), [SunFounder](https://docs.sunfounder.com/projects/davinci-kit/en/latest/for_pi5.html), [rpi-hardware-pwm](https://pypi.org/project/rpi-hardware-pwm), [Pi WPA2-Ent guide](https://ac-training-lab.readthedocs.io/en/latest/raspberry-pi-wpa2-enterprise.html), [Adafruit lesson 8](https://learn.adafruit.com/adafruits-raspberry-pi-lesson-8-using-a-servo-motor) |

**Recommended combo:** A + B + C on one microcontroller, inside a hand-made cardboard or papier-mâché box. Estimate ~6–8 h for one person while the others build the model and decision layer.

**Wiring pointers (inference from the docs above):**
- **Arduino:** `Servo.attach(9)` then `write(angle)`. Read serial lines `P:<0-100>` and map them to 0–180°, clamped about 5° short of the end-stops. Grove pot on A0 and button on D2. Send `T:<turn>` and `B` back to the laptop.
- **Pico (MicroPython):** `PWM(Pin(n), freq=50)`. 1 ms ≈ `duty_u16` 3277 and 2 ms ≈ 6554 (computed as 65535 × pulse / 20 ms). Calibrate the real SG90 endpoints. The REPL is on USB serial.
- **Laptop:** `pyserial` at 115200 baud. Keep the serial protocol to plain text lines so it can be debugged in the Arduino Serial Monitor.

**Failure-risk checklist:**
- Bring a spare SG90.
- Add a bulk capacitor.
- Run with no Wi-Fi dependency.
- Hard-code a "demo mode" that replays a cached P(win) series if the model server is down.
- Record a backup video. AngelHack advises recording a clean run the night before and saving it locally ([AngelHack](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/)).

**What wins handmade/hardware prizes (sparse evidence):**
- I found **no Devpost prize literally called "Best Handmade" with published winners**. Hardware-prize rubrics vary by event. They commonly weigh whether it works, originality, technical complexity and utility, and sometimes design ([HackPrinceton S26](https://hackprinceton-spring-26.devpost.com/), [Hard Hack 2025](https://hard-hack-2025.devpost.com/), [sunhacks 2025](https://sunhacks2025.devpost.com/), [Hack From The Past](https://hackfromthepast.devpost.com/)).
- OxHack's own general criteria are **Creativity, Technicality, Completeness, Presentation/Hackathon Spirit** ([Devpost](https://oxhack-2026.devpost.com/)).
- A working rough build beats polished slides: "a rough build that functions will score above a polished set of slides describing one" ([AngelHack](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/)).
- The judge's own record: playful, technically real "not-very-serious" papers where "the results therein are real" ([tom7.org/chess](http://tom7.org/chess/)). Physical hacks include reverse-emulating the NES with a Raspberry Pi 3 on a custom cartridge board. He called the Pi "an absurdly advanced 'memory mapper'" ([Raspberry Pi magazine](https://magazine.raspberrypi.com/articles/reverse-emulated-nes), [Wikipedia](https://en.wikipedia.org/wiki/Tom_Murphy_VII)).
- Inference: for this judge, a funny, honest, home-made object that does something real (it moves with the data, and you can rewind it) is likely to beat a slick bought display. "Build something from scratch" also rewards showing the parts you wrote yourselves.

---

### 3. Coaching-review design

#### 3.1 What the reference products do

- **Chess.com Game Review.** A virtual Coach "provides a brief, one-line summary of how the game unfolded", then walks through **key moments**: last book move, brilliant move, bad move, missed tactic. It has "Show Idea / Show Fork / Best", a **Retry** button to find the best move, and a game graph showing "who had the advantage at each stage". **The Coach can read the review aloud**, which is a direct precedent for voice ([support 8584089](https://support.chess.com/en/articles/8584089-how-does-game-review-work)).
- **Chess.com classification** is by expected points lost (1.00 = winning, 0.50 even, 0.00 losing; page dated 2026-02-09):

  | Label | Expected points lost |
  |---|---|
  | Best | 0 |
  | Excellent | 0–0.02 |
  | Good | 0.02–0.05 |
  | Inaccuracy | 0.05–0.10 |
  | Mistake | 0.10–0.20 |
  | Blunder | 0.20–1.00 |

  Special labels: **Miss** = "fail to capitalize on your opponent's mistake"; **Great** = only good move or turns a loss into equality ([support 8572705](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-and-etc)).
- **Lichess.**
  - Win% = 50 + 50·(2/(1+exp(−0.00368208·cp)) − 1).
  - Accuracy% = 103.1668·exp(−0.04354·(Win%before − Win%after)) − 3.1669 ([accuracy page](https://lichess.org/page/accuracy)).
  - Labels in `Advice.scala`: `.3 → Blunder`, `.2 → Mistake`, `.1 → Inaccuracy` on the delta of `WinPercent.winningChances`. That function is commented `// [-1, +1]`, so the thresholds equal **5 / 10 / 15 Win% points** ([Advice.scala](https://raw.githubusercontent.com/lichess-org/lila/master/modules/tree/src/main/Advice.scala), [scalachess eval.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/eval.scala)). A forum user's measurement (blunder >15, mistake 10–15, inaccuracy 5–10) agrees ([lichess forum](https://lichess.org/forum/general-chess-discussion/what-constitutes-an-inaccuracy)).
  - Comment text is minimal, e.g. "Mistake. Nf3 was best." (`s" $move was best."`).

#### 3.2 Pipeline (fits the existing Momentum plan)

1. **Per-turn P(win)** for the reviewed player, from the LightGBM model (already planned).
2. **Alternatives per turn:** each legal move and switch → @smogon/calc + shallow look-ahead → resulting state → model re-scores P(win). Average over damage rolls, accuracy and crits where feasible, so the result is *expected* P(win) and not one lucky roll (inference).
3. **Decision loss** = P(best alternative) − P(chosen), in percentage points.
4. **Label:**
   - Use **Chess.com bands** (Good <5, Inaccuracy 5–10, Mistake 10–20, Blunder >20 pts). They are more lenient on blunders than Lichess's 15, which suits a noisier model (inference).
   - **Only label when the loss exceeds the model's own uncertainty.** For example, require the loss to exceed the bootstrap CI width or the calibration error for that bin. Otherwise say "close call".
   - These bands were tuned on chess engine evals, not on a Pokémon model with hidden information. Say so on the limits slide.
5. **Key moments:** up to 5 turns.
   - The biggest realised swing (the "decisive turn").
   - The biggest decision losses.
   - A "**Miss**": the opponent's error you didn't punish.
   - A "**Good decision, bad luck**" turn: high expected P after your move, but the RNG went against you. This is the most coach-like insight and quant judges like the luck-vs-skill split (inference).
6. **Optional Tom 7 nod:** show the *worst* legal option too ("worstfish says: Tera Normal into Ghost, 12%"). It is playful, and it gives a baseline span for the decision. Elo World's `worstfish` precedent: [Elo World PDF](http://tom7.org/chess/weak.pdf), [WorstFish Lichess bot](https://lichess.org/@/WorstFish/all).
7. **Facts JSON per key turn**, all computed in code:
   `{turn, side, chosen, p_before, p_after_chosen, best, p_after_best, worst, p_after_worst, loss_pts, label, ci_pts, top_reasons:[{feature, contribution_pts}], luck_flag}`.
   `top_reasons` should come from model attributions (SHAP / LightGBM `pred_contrib`), not from the LLM.
8. **Template text:** a deterministic string built from the facts, always shown first and always correct.
9. **Optional LLM paraphrase** with Gemini structured output.
   - Prompt: "Rewrite in a warm coaching voice. Use ONLY the facts. Do not add any number, move, Pokémon, ability or item not in the facts."
   - Schema: `{turn:int, headline:str, explanation:str, numbers_used:[number], names_used:[str]}`.
   - One request per replay, covering all key turns.
   - Gemini guarantees valid JSON but "values still need validation in your application". `minLength`/`maxLength` and similar constraints are stripped, while `minItems`/`maxItems` are enforced ([structured output](https://ai.google.dev/gemini-api/docs/structured-output), updated 2026-10-21).
10. **Validator (hallucination check):**
    - (a) Regex every number and percentage in `headline + explanation`. Each must equal a facts value after rounding, or a whole-number difference of two facts values.
    - (b) Match the text against a dictionary of all Pokémon, move, item and ability names (Showdown dex / PokeAPI). Every hit must be in that turn's allowed set.
    - (c) `numbers_used` and `names_used` must match what the regex finds.
    - Any failure means you **use the template** for that turn and log it.
    - Report the fallback rate on the honesty slide ("LLM paraphrase rejected on N of M turns").
    - This mirrors ACT-Eval's approach of splitting commentary into **atomic claims** and checking each against engine tools ([arXiv 2608.04240](https://arxiv.org/abs/2608.04240)). CCC also pairs an expert engine with an LLM because LLMs "are prone to hallucinations due to their limited decision-making capabilities" ([arXiv 2410.20811](https://arxiv.org/abs/2410.20811), NAACL 2025).
11. **Voice (optional):**
    - Run a normaliser before TTS: 62% → "sixty-two percent", T14 → "turn fourteen". Flash v2.5 misreads some number formats, and v4/v3 do not support SSML `<break>` tags ([normalization docs](https://elevenlabs.io/docs/best-practices/prompting/normalization)).
    - Use `/with-timestamps` to get per-character start and end times, so the needle can move as the voice says the number ([API ref](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)).
    - Pre-generate MP3s for the 3–5 demo replays and commit them to a local cache. Keep the live API call path in code for the prize.

#### 3.3 Sample script for one turn

The numbers are illustrative placeholders; the real values come from the facts JSON.

> **Template (always correct):** "Turn 14 · Mistake (−16 pts). You chose Tera Fairy + Make It Rain: win chance 58% → 39%. Stronger: switch to Great Tusk → 55%. Worst option was Shadow Ball → 31%. Main factors: speed order lost (−9 pts), Stealth Rock damage on switch-in (−4 pts). Model uncertainty ±5 pts."
>
> **Coach paraphrase (validated):** "Turn fourteen is where this one slipped. Going Fairy and firing Make It Rain felt aggressive, but it dropped your chances from fifty-eight to thirty-nine percent. Switching to Great Tusk keeps you at fifty-five, sixteen points better, mainly because you'd stop losing the speed race. Not every turn is this clear-cut, but this one we'd call a mistake."

The validator would check that 58, 39, 55 and 16 are all facts or fact differences, and that "Great Tusk" and "Make It Rain" are in the turn's allowed name set.

---

### 4. API facts (read 2026-10-24)

| Item | Fact | Source (date read) |
|---|---|---|
| ElevenLabs Free plan | 10,000 credits/month; Starter $6/mo (30,000 credits), Creator $22/mo (121,000), Pro $99 (600,000) | [pricing](https://elevenlabs.io/pricing), [API pricing](https://elevenlabs.io/pricing/api) (2026-10-24) |
| ElevenLabs free-tier terms | "does not include a commercial license"; when published, put "elevenlabs.io" or "11.ai" in the title; all paid plans include a commercial license (except Beta Services) | [help center](https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform) (2026-10-24) |
| ElevenLabs free tier + voice library | "The voice library is not available via the API to free tier users". Use default voices, e.g. "George" `JBFqnCBsd6RMkjVDRZzb` from the quickstart | [TTS capability](https://elevenlabs.io/docs/overview/capabilities/text-to-speech), [quickstart](https://elevenlabs.io/docs/quickstart) (2026-10-24) |
| ElevenLabs models | `eleven_v4` (flagship, 90+ langs, 10k chars/request); `eleven_v4_turbo` (~100 ms); `eleven_flash_v2_5` (~75 ms, 32 langs, 40k chars/request); `eleven_multilingual_v2` (previous generation, "most stable on long-form"); `eleven_v3` (previous generation); `eleven_turbo_v2_5` **deprecated** → use Flash v2.5. Latencies exclude network. | [models](https://elevenlabs.io/docs/overview/models) (2026-10-24) |
| Eleven v4 launch | 2026-09-28; Turbo ~100 ms median inference, 150 ms to first speech; audio tags like [laughs], [whispers]; multi-speaker; on every plan including free | [TestingCatalog](https://www.testingcatalog.com/elevenlabs-launches-eleven-v4-and-v4-turbo-voice-models.md) (2026-10-24); agrees with the models doc |
| ElevenLabs API price per 1K chars | v4 $0.08; v4 Turbo $0.04; v3 $0.08; Multilingual v2 $0.08; Flash/Turbo $0.04 | [API pricing](https://elevenlabs.io/pricing/api) (2026-10-24) |
| Credits per character | Multilingual v2: 1 credit/char. Flash/Turbo via API: 0.5–1 credit/char. v4 credit rate not stated (inference: probably 1/char, since its $ price equals v2's) | [pricing](https://elevenlabs.io/pricing) (2026-10-24) |
| Demo budget (inference) | 5 key turns × ~300 chars ≈ 1.5k chars per replay; 3 replays ≈ 4.5–6k chars, which fits in 10k free credits even at 1 credit/char | computed |
| ElevenLabs SDKs | Python `pip install elevenlabs`; JS `npm install @elevenlabs/elevenlabs-js`; env `ELEVENLABS_API_KEY`; `text_to_speech.convert(voice_id, model_id, output_format="mp3_44100_128")` | [quickstart](https://elevenlabs.io/docs/quickstart) (2026-10-24) |
| ElevenLabs timestamps | `POST /v1/text-to-speech/{voice_id}/with-timestamps` → `audio_base64` + `alignment.characters / character_start_times_seconds / character_end_times_seconds` | [API ref](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) (2026-10-24) |
| MLH ElevenLabs perk | Free **1-month Creator** subscription. MLH emails a promo code the week of the event and the link leads to ElevenLabs signup | [MLH partner page](https://www.mlh.com/partners/elevenlabs) (2026-10-24) |
| ElevenLabs hackathon page | Participants at sponsored events get Creator for 1 month, "100,000 total credits". **Conflicts** with 121,000 on the current pricing page; the hackathon page is probably older | [elevenlabs.io/hackathon](https://elevenlabs.io/hackathon) (2026-10-24) |
| MLH "Best Use of ElevenLabs" (OxHack) | Prize: Wireless Earbuds. Text: "Integrate fully autonomous audio experiences into your hack with ElevenLabs and give your project a voice". No further rubric published | [Devpost](https://oxhack-2026.devpost.com/) (2026-10-24) |
| Gemini models | Stable: `gemini-3.8-flash` (new, most capable Flash), `gemini-3.6-flash`, `gemini-3.5-flash-lite` (fastest/cheapest), `gemini-3.1-flash-lite`. Preview: `gemini-3-flash-preview`, `gemini-3.1-pro-preview`. Docs: "For any new projects, use … 3.5 Flash-Lite or 3.8 Flash". The 2.5 family is limited to prior users. TTS: `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts` | [models](https://ai.google.dev/gemini-api/docs/models) (updated 2026-10-22; read 2026-10-24) |
| Gemini free tier | Free of charge for 3.8 Flash, 3.6 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite, 3 Flash Preview, 2.5 family. **Not** on free tier: Gemini 4 Argon, 3.1 Pro Preview. Free-tier content **is used to improve Google products** | [pricing](https://ai.google.dev/gemini-api/docs/pricing) (2026-10-24) |
| Gemini paid price (for reference) | 3.8 Flash $0.75 in / $3.75 out per 1M tokens through 2026-12-31; 3.5 Flash-Lite $0.30 / $2.50 | [pricing](https://ai.google.dev/gemini-api/docs/pricing) (2026-10-24) |
| Gemini rate limits | Docs give **no** free-tier numbers ("View your active rate limits in AI Studio"). Limits are per project, not per key. RPD resets at midnight Pacific. Previews are tighter | [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (2026-10-24) |
| Gemini free-tier numbers (third party) | 2.5 Flash cut from 10 RPM / 250 RPD to 5 / 20 on 2025-12-06; developer reports (Sept 2026) say ~20 RPD for 3.x Flash and ~500 RPD for 3.x Flash-Lite. **WEAK**; check AI Studio | [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes) (reviewed 2026-10-21; read 2026-10-24) |
| Gemini structured output | Docs show `client.interactions.create(model="gemini-3.8-flash", response_format={"type":"text","mime_type":"application/json","schema": Model.model_json_schema()})`; Pydantic (Python) and Zod (JS); schema subset only; large/nested schemas → 400 | [structured output](https://ai.google.dev/gemini-api/docs/structured-output) (updated 2026-10-21) |
| MLH Gemini perk | "$10 in free credits per month by claiming your Google Program Benefits"; "$300 in free credits with a new account"; student plan 1 year free | [MLH partner page](https://www.mlh.com/partners/gemini) (2026-10-24) |
| MLH "Best Use of Gemini API" (OxHack) | Prize: MLH Swag Kits. Text: "build AI-powered apps that make your friends say WHOA"; examples include an app that "summarizes complex research papers". No rubric beyond that | [Devpost](https://oxhack-2026.devpost.com/) (2026-10-24) |

---

### 5. Claim ledger

| Claim | Verdict | Sources | Correction / note |
|---|---|---|---|
| The Best Handmade prize is judged by Tom 7 (Tom Murphy VII), with the brief "Get creative and build something from scratch", thanks to Citadel | **KEEP** | [Devpost](https://oxhack-2026.devpost.com/) (judges list includes "Tom Murphy VII") | The brief's "professor judge" framing is wrong; see the DO NOT USE row |
| Tom 7 wrote Elo World (SIGBOVIK 2019), rating weak chess engines including worstfish and Stockfish-random interpolations | **KEEP** | [tom7.org/chess](http://tom7.org/chess/), [Elo World PDF](http://tom7.org/chess/weak.pdf), [WorstFish bot](https://lichess.org/@/WorstFish/all) | Good pitch hook for the decision-quality angle |
| Tom 7 builds real hardware hacks (Raspberry Pi 3 inside an NES cartridge to run SNES games) | **KEEP** | [Raspberry Pi magazine](https://magazine.raspberrypi.com/articles/reverse-emulated-nes), [Wikipedia](https://en.wikipedia.org/wiki/Tom_Murphy_VII) | n/a |
| OxHack general criteria: Creativity, Technicality, Completeness, Presentation/Hackathon Spirit | **KEEP** | [Devpost](https://oxhack-2026.devpost.com/) | Presumably applies to Handmade too (not stated explicitly) |
| Chess.com bands: Inaccuracy 0.05–0.10, Mistake 0.10–0.20, Blunder >0.20 expected points | **KEEP** | [Chess.com 8572705](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-and-etc) | Page dated 2026-02-09 |
| Lichess thresholds are 0.1/0.2/0.3 winning-chances on a −1..+1 scale, i.e. 5/10/15 Win% points | **KEEP** | [Advice.scala](https://raw.githubusercontent.com/lichess-org/lila/master/modules/tree/src/main/Advice.scala), [scalachess eval.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/eval.scala), [winningChances.ts](https://raw.githubusercontent.com/lichess-org/lila/master/ui/lib/src/ceval/winningChances.ts), [forum measurement](https://lichess.org/forum/general-chess-discussion/what-constitutes-an-inaccuracy) | Do **not** quote this as "10/20/30%" (scale error) |
| Lichess Win% formula constant 0.00368208; Accuracy formula 103.1668·exp(−0.04354·Δ) − 3.1669 | **KEEP** | [lichess accuracy](https://lichess.org/page/accuracy), [winningChances.ts](https://raw.githubusercontent.com/lichess-org/lila/master/ui/lib/src/ceval/winningChances.ts) | n/a |
| Chess.com's Coach does key moments, Retry, show best move, and can read the review aloud | **KEEP** | [Chess.com 8584089](https://support.chess.com/en/articles/8584089-how-does-game-review-work) | Precedent for the voice coach |
| LLM chess commentary hallucinates (GPT-5.4 without tools 22.0% incorrect sub-claims; small open models >40%); tool/engine grounding helps | **KEEP** | [ACT-Eval 2608.04240](https://arxiv.org/abs/2608.04240), [CCC 2410.20811](https://arxiv.org/abs/2410.20811) | Chess, not Pokémon, but the same failure mode |
| Gemini structured output gives valid JSON but values still need app-side validation; some JSON Schema constraints are ignored | **KEEP** | [structured output](https://ai.google.dev/gemini-api/docs/structured-output) | n/a |
| ElevenLabs free tier: 10k credits/mo, non-commercial, attribution "elevenlabs.io"/"11.ai" in the title | **KEEP** | [pricing](https://elevenlabs.io/pricing), [help center](https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform), [TestingCatalog](https://www.testingcatalog.com/elevenlabs-launches-eleven-v4-and-v4-turbo-voice-models.md) | Use the MLH Creator code to avoid attribution and voice-library limits |
| Eleven v4 / v4 Turbo exist (launched 2026-09-28); Turbo v2.5 deprecated | **KEEP** | [models](https://elevenlabs.io/docs/overview/models), [TestingCatalog](https://www.testingcatalog.com/elevenlabs-launches-eleven-v4-and-v4-turbo-voice-models.md) | OpenRouter lists 7 Oct (its own availability date) |
| Flash v2.5 ~75 ms model latency | **KEEP** (one official source) | [models](https://elevenlabs.io/docs/overview/models) | Excludes network; budget 300 ms+ end to end (inference) |
| MLH gives a free 1-month ElevenLabs Creator code, emailed the week of the event | **KEEP** | [MLH ElevenLabs](https://www.mlh.com/partners/elevenlabs), [elevenlabs.io/hackathon](https://elevenlabs.io/hackathon) | Credit amount conflicts: 100k (hackathon page) vs 121k (pricing page) |
| Free-tier users can't use voice-library voices via the API | **KEEP** | [TTS capability](https://elevenlabs.io/docs/overview/capabilities/text-to-speech) | n/a |
| ElevenLabs bans cloning or impersonating any living person's voice without explicit consent | **KEEP** | [use policy](https://elevenlabs.io/use-policy) (updated 2026-10-09) | Use a stock voice; don't imitate a famous commentator or anime voice actor |
| Gemini free-tier limits are not published in docs; check AI Studio per project | **KEEP** | [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes) | n/a |
| Gemini free tier includes 3.8 Flash and 3.5 Flash-Lite; free-tier data used to improve products | **KEEP** | [pricing](https://ai.google.dev/gemini-api/docs/pricing), [models](https://ai.google.dev/gemini-api/docs/models) | Don't send personal data |
| Arduino Servo lib uses hardware timers (default 544–2400 µs, 20 ms); disables PWM on timer pins | **KEEP** | [Servo.h](https://raw.githubusercontent.com/arduino-libraries/Servo/master/src/Servo.h) | On Uno that's pins 9/10 (common knowledge; not in the fetched text) |
| SG90: 4.8–6 V, ~0.1 s/60°, idle ~10 mA, moving 100–250 mA, stall up to ~360 mA | **KEEP** | [ProtoSupplies](https://protosupplies.com/product/servo-motor-micro-sg90/), [SG90 datasheet](https://bit.nkust.edu.tw/~csshieh/teach/111A/mc/datasheet/SG90.pdf) | Stall figure is from vendor testing; another test says 300 mA |
| Add a 470–1000 µF capacitor on servo/LED power | **KEEP** | [ProtoSupplies](https://protosupplies.com/product/servo-motor-micro-sg90/), [Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices) | n/a |
| NeoPixels at 5 V need 5 V data (level shifter from 3.3 V), a 300–500 Ω resistor and a shared ground | **KEEP** | [Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices) | n/a |
| pigpio doesn't support the Raspberry Pi 5; use lgpio / rpi-hardware-pwm | **KEEP** | [Pi4J](https://www.pi4j.com/documentation/providers/pigpio), [SunFounder](https://docs.sunfounder.com/projects/davinci-kit/en/latest/for_pi5.html), [gpiozero changelog](https://gpiozero.readthedocs.io/en/v2.0.1.post3/_sources/changelog.rst.txt) | n/a |
| Grove Rotary Angle Sensor is a 300° 10 kΩ potentiometer (absolute), so it's a simpler rewind knob than an encoder | **KEEP** | [Seeed wiki](https://wiki.seeedstudio.com/Grove-Rotary_Angle_Sensor/), [MLH hardware](https://www.mlh.com/resources/hardware) | n/a |
| Waveshare 2.13" B/W e-paper: 2 s full / 0.3 s partial refresh | **KEEP** | [Waveshare](https://www.waveshare.com/2.13inch-e-paper.htm), plus search result for the Pico variant | n/a |
| Working prototype beats slides; record a backup video | **KEEP** | [AngelHack](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/), research-inputs §A | n/a |
| "MLH Hardware Lab has Arduino, Raspberry Pi and more" | **WEAK** | Opening slides (research-inputs §E), [MLH hardware](https://www.mlh.com/resources/hardware) | The MLH page lists Pico/RP2040 and a Grove kit. Quantities and what OxHack actually stocks are unknown. Check the table in hour 1 |
| Tom 7 built a papier-mâché robot for his chess video | **WEAK** | [devjournal (2019)](https://devjournal.balinterdi.com/30-weird-chess-algorithms/) only; not in the paper text | Don't cite it on stage unless someone watches the video and confirms |
| Gemini free tier is ~20 RPD for 3.x Flash and ~500 RPD for Flash-Lite | **WEAK** | [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes) (developer reports) | Design for one call per replay plus a cache |
| Pico 3.3 V PWM drives an SG90 signal reliably | **WEAK** (inference) | none found | Common practice, but test on the bench |
| Pre-generated audio still qualifies for "Best Use of ElevenLabs" | **WEAK** (inference) | [Devpost](https://oxhack-2026.devpost.com/) asks for "fully autonomous audio experiences" | Keep a live API path (button, then generate) with the cache as fallback; show the code |
| Nintendo/TPC take down Pokémon fan projects, mainly at distribution hubs | **KEEP** (context) | [Engadget](https://www.engadget.com/2018-08-29-pokemon-essentials-nintendo-takedown.html), [Axios](https://www.axios.com/2022/01/24/fan-made-game-escapes-nintendo), [TechRaptor](https://techraptor.net/gaming/news/pokemon-essentials-gets-dmcad-by-nintendo) | Hackathon demo risk is low (inference). Avoid bundling sprites or the Poké Ball logo in the public repo and the physical build; text names are fine |
| The handmade judge is "the professor judge" who values "craft, play, making for its own sake" (research-inputs §A) | **DO NOT USE** | [Devpost](https://oxhack-2026.devpost.com/) | The judge is Tom Murphy VII, a computer scientist and YouTuber (no professor title found). The brief is "build something from scratch". The "play" part fits him; target his style (playful, real results, from scratch) |
| Lichess blunder = 30% win-chance drop | **DO NOT USE** | [scalachess eval.scala](https://raw.githubusercontent.com/lichess-org/scalachess/master/core/src/main/scala/eval.scala) | The scale is −1..+1, so it's **15 Win% points** |
| `eleven_turbo_v2_5` as the low-latency pick | **DO NOT USE** | [models](https://elevenlabs.io/docs/overview/models) | Deprecated. Use `eleven_flash_v2_5` or `eleven_v4_turbo` |
| pigpio fixes Pi servo jitter | **DO NOT USE** (on Pi 5) | [Pi4J](https://www.pi4j.com/documentation/providers/pigpio), [gpiozero changelog](https://gpiozero.readthedocs.io/en/v2.0.1.post3/_sources/changelog.rst.txt) | Use a microcontroller, or Pi hardware PWM via `rpi-hardware-pwm` |

---

### 6. Open questions

1. **What hardware does OxHack's MLH table actually have** (Arduino Uno vs Nano, Pi 4 vs 5, how many Grove servos and kits, any NeoPixels)? Not published for this event. Ask in hour 1.
2. **Does the Handmade prize expect a physical object, or does "from scratch" also reward software built from scratch?** The Devpost text is ambiguous. Consider asking an organiser, or Tom 7 at judging, and pitching both: a hand-built dial and hand-written components.
3. **Is Tom 7 judging in person or remotely?** This matters for whether a physical object can be seen. Not found.
4. **Exact Gemini free-tier RPM/RPD** for `gemini-3.8-flash` / `gemini-3.5-flash-lite` on the team's project. Check the AI Studio rate-limit page, and claim the MLH "$10/month" Google Program Benefits as backup.
5. **ElevenLabs v4 credit cost per character** (not on the pricing page) and the Creator coupon's credit amount (100k vs 121k). Check the dashboard after redeeming.
6. **Does the old `client.models.generate_content(..., response_schema=...)` path still work?** The current docs only show the new `interactions.create` API. Not verified.
7. **Gemini TTS pricing and quality** (`gemini-3.8-flash-tts`) as a single-vendor alternative if the team targets only the Gemini prize. Not checked.
8. **Threshold calibration for Pokémon.** No published Pokémon-specific blunder thresholds were found. The team must justify its bands (e.g. the model CI) on the limits slide.
9. **Venue Wi-Fi type** (open/PSK vs eduroam). Matters only if a Pi is used. Unknown.

---

# Pass 6, notes-bot-setup (source: `notes-bot-setup.md`)

## Research notes: Showdown bot setup (local only; goes into OxHack-2026-research.md as its own section)

Pass run 2026-10-24 by the bot-setup session. Question: what's the fastest sound way to get a bot playing on Pokémon
Showdown, so the data and decision layers can plug in later?

### KEEP (corroborated)
- **poke-env 0.16.1 is current and runs on our Python.** Released 2026-08-23; `requires_python >=3.10`; classifiers list
  3.10–3.14. Installed cleanly into a fresh Python 3.14.3 venv on this machine (2026-10-24).
  Sources: PyPI JSON (pypi.org/pypi/poke-env/json) · local install test.
- **poke-env defaults:** `battle_format="gen9randombattle"`, `server_configuration=LocalhostServerConfiguration`,
  `max_concurrent_battles=1`. `choose_move(battle)` may return a `BattleOrder` *or an awaitable*, so a slow brain
  (an LLM call) can be `async`. Sources: poke-env `src/poke_env/player/player.py` (master) · poke-env quickstart docs.
- **Local server setup:** `git clone https://github.com/smogon/pokemon-showdown` → `npm install` →
  `cp config/config-example.js config/config.js` → `node pokemon-showdown start --no-security`; battles watchable at
  http://localhost:8000. Showdown 0.11.11 needs **Node >=22.18.0** (this machine has 24.18.0).
  Sources: poke-env getting-started docs · smogon/pokemon-showdown `package.json`.
- **Official server needs an account with a password** (`ShowdownServerConfiguration` + `AccountConfiguration`).
  Sources: poke-env getting-started docs · poke-env "connecting to showdown and challenging humans" example.

### WEAK (one source only; second not found yet)
- **Bots on the public server must be registered (since 2026-10-09).** Smogon announcement "★ Initial policy on bots"
  (Django, senior staff): a self-declared bot registry is mandatory; running an unregistered bot is "a bannable offense";
  register via `/ht` in PS chat → bot registration (Hecate, 2026-10-12); bot battles don't affect human ratings; AI help in
  tournaments = ghosting, immediate ban. Staff say the details are "to be confirmed". Treat as binding: register before any
  public-server play. Source: smogon.com/forums/threads/3789528/. A web search for a second source found nothing.

### Context, not load-bearing
- PokéAgent Challenge Track 1 ran its own Showdown server; only registered usernames could play the qualifiers (13–19 Oct),
  bot names prefixed "PAC". Source: pokeagent.github.io/track1.html.
- Community consensus (Reddit / HN): not mined this pass.

### DO NOT USE
- ~~"Node.js v10+ is enough for the local server"~~ (poke-env getting-started page). Refuted by Showdown's own
  `package.json` (`node >=22.18.0`). Outdated docs; use the package.json number.

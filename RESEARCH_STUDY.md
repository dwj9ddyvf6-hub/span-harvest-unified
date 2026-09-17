# SPAN HARVEST UNIFIED — Deep Research Study and Actionable Algorithm

**Version:** 1.2.0 research implementation
**Date:** 2026-09-17
**Status:** `RESEARCH_ONLY / NO_PROMOTION`

## Executive conclusion

The supplied X post is asking for a second layer after an underdog detector: an algorithm that captures the largest repeatable part of a favorable move while controlling reversal, settlement, fees, and execution risk. The right abstraction is a causal optimal-stopping and execution policy, not a hindsight “buy the low, sell the high” calculation.

I synthesized the useful prior work, the attached specification, the TimePortal replay semantics, the reviewed research sources, the archived reverse-engineering work, and the executable research code into one algorithm:

`SPAN_HARVEST_UNIFIED_1.2.0`

It combines:

1. chronological profile selection with abstention;
2. staged entry in the observed profit zone;
3. three inventory sleeves for harvesting, trailing, and riding;
4. causal bounce, slope, toxicity, shock, and time controls;
5. explicit fee, settlement, unresolved-end, and accounting treatment;
6. optional level-2 execution observations with strict as-of lookup;
7. adaptive exit-surface search kept separate from the frozen production registry;
8. calibration diagnostics, family-wise correction, cluster bootstrap, embargo, fee stress, and shadow-fill reconciliation;
9. deterministic evidence records and promotion gates.

The algorithm is designed to become profitable only when the data proves a positive edge after costs. That distinction matters: no backtest can manufacture missing order-book depth, queue position, latency, or a future outcome. On the current 512-tape release, the honest result is no promotion and no trades under the strict causal gate.

## What the original sources establish

The [X post](https://x.com/PredictionAlgos/status/2100369942898242015?s=46) describes an underdog detector and asks for a second algorithm that optimizes profit per selected underdog/match, specifically by finding the lowest buy and highest sell across the board and “scooping” the best profit zone. The visible discussion points toward trailing stops, MACD-like momentum/deceleration, and reacting to an underdog taking an early lead.

The supplied [TimePortal detailed replay](https://timeportal.pro/polymarket/detailed.php) was visually inspected and its embedded JavaScript semantics were traced. It uses one rising span per match, actual first-crossing fills, target credit at the declared sale price, settlement at 1/0, and explicit unknown-end behavior. The published comparison, before fees, was:

| Rule | Buys | Profitable exits | Losses | Net |
|---|---:|---:|---:|---:|
| 20¢ → 60¢ | 303 | 82 | 221 | −$42.51 |
| 30% of open → 3× fill | 260 | 64 | 196 | −$68.00 |
| 10% of open → settlement | 216 | 7 | 209 | −$54.53 |

The comparator is useful as a baseline, not as proof that any replacement is profitable.

## Research repository synthesis

The prior algorithm and reverse-engineering material was searched across the available research archive, the attached specification, and the reviewed research sources. The reusable synthesis is:

- deterministic chronological replay is mandatory;
- selection, execution, risk, allocation, and accounting must be separate;
- completed evidence is authoritative; current or future outcomes cannot enter a decision;
- unknown ends remain unresolved and receive no performance credit;
- partial fills, fees, close state, and reconciliation must be explicit;
- promotion requires a frozen holdout, fee/slippage stress, stability after removing the best trade, regime breadth, and prospective shadow evidence;
- match-level confidence is insufficient when observations are concentrated in the same sport/date regime, so the implementation also applies a deterministic sport/date-cluster lower-bound screen;
- Research surfaces are useful for immutable hashes, decision records, freshness gates, completed-bar discipline, and observation-only workflows;
- no reviewed source contains a verified live prediction-market depth/queue simulator or a valid order route; the sampled observatory explicitly reported `ORDER_ROUTE_ABSENT`.

Earlier prototype work contributed adaptive target/trailing concepts and exposed the parity problem. The attached specification contributed the PZOE/APZI separation, sport-relative clock, shock normalization, A/B/C sleeves, evidence ledger, and strict no-promotion result. The paper-desk, research, scanner, ledger, observation, and alerting archives contributed closed-loop testing, shadow deployment, immutable evidence, and fail-closed principles.

The research-source audit covered the reviewed surfaces. Their useful transferable assets are research protocols, source/evidence hashes, completed-bar decision records, freshness and actionability states, and fail-closed directives. The prediction-market observatory tables were empty for market bars/observations at audit time; other research data were not evidence for prediction-market execution.

## The unified algorithm

### Inputs and definitions

For each candidate match:

- `O`: opening price;
- `P_i`: observed price print at event `i`;
- `t_i`: timestamp;
- `F`: actual simulated fill price;
- `S`: shares, with `$1` stake giving `S = 1/F` for a single rung;
- `R_i`: sport-relative match clock;
- `m`: profile selected using older matches only;
- `c`: explicit per-share fee and later slippage/depth assumptions.

All prices are bounded to `[0,1]` and all entry/exit logic is evaluated sequentially. A print is an observation proxy, not proof that the same price was executable at the required size.

### Phase 1 — causal profile selection

Sort matches by `(start_timestamp, match_id)`. For the current match, search the hierarchy:

1. sport + cohort + opening bucket;
2. sport + cohort;
3. cohort + opening bucket;
4. sport;
5. cohort;
6. all.

Use the first group with at least 30 prior matches. Replay all 14 frozen profiles on that prior group. A profile is eligible only when:

- at least 5 prior filled matches are resolved;
- at least 85% of the group is evaluable;
- the 95% lower confidence bound of net profit per match is positive;
- the same lower bound remains positive after removing the single best trade.
- a deterministic sport/date-cluster lower bound is positive;
- the cluster lower bound remains positive after removing the single best trade.
- the profile-family-adjusted lower bound remains positive when multiple profiles were searched;
- the prior sample satisfies the configured sport/date-cluster minimum and any configured embargo.

If no profile passes, output `NO_TRADE`. This is the core profitability mechanism: the engine trades only when historical evidence supports positive expected net under the frozen replay assumptions.

### Phase 2 — staged entry

Use three capital rungs: `45% / 35% / 20%` of the per-match stake.

- R1 rests at `55% of open` through relative clock `0.25`, then reprices to `38% of open`.
- R1 follows the exact first-crossing rule: if the first print is below the limit, fill at the observed print; if the limit was crossed after a prior higher print, fill at the resting limit.
- R2 and R3 require price in `[15¢,85¢]`, price no higher than the active limit, an 8-minute prior running-low bounce of at least `1.5¢`, non-negative 6-minute slope, no falling-knife drop of `8¢` with negative slope, and no toxic price at or below `6¢` while fading.
- Stop accepting staged entries after relative clock `0.80`.
- Optional shock profiles require a causal normalized shock and subsequent recovery before entry.

### Phase 3 — profit-zone exits

Inventory is assigned at purchase time to three sleeves:

- A: `34%`, harvest;
- B: `33%`, trail/target;
- C: `33%`, ride or transfer.

For average fill `F_avg`:

```text
A target = ceil_to_tick(max(2.15 × F_avg, F_avg + 18¢))
B target = max(72¢, F_avg + one tick)
```

- A exits at the first later observed print at or above its target.
- B exits at its target or when a running high gives back at least `38%` of the runup while the 6-minute slope is no longer supportive.
- C transfers to B when the bounded causal state score is weak; it may ride to settlement only while the state remains strong.
- Any inventory at or below `8¢` while fading is salvaged.
- Any inventory still open after 240 minutes is flattened at the observed print.
- Remaining resolved inventory settles at `1` for a win or `0` for a loss.
- Unknown ends with open inventory or an unresolved pending entry are `UNRESOLVED`, never a win, loss, or artificial zero.

The state score is deliberately labeled a ranking diagnostic rather than a probability. It combines price position, causal slope, and recovery from a prior low. It must be calibrated on future data before it is used as a probability or position-sizing input.

The implementation also exposes a bounded six-surface exit search for training folds only, expanded to 12 candidates when shock variants are included. It varies harvest multiple, additive target, trailing giveback, B target, and flatten horizon. It is never silently substituted for the frozen 14-profile registry; the number of candidates is recorded and the family-wise bound is applied.

### Phase 4 — accounting and evidence

For every match record:

- source release and payload hash;
- profile registry hash;
- group and prior-history size;
- all entry rungs, prices, limits, and fees;
- all sleeve transfers and exits;
- settlement or unresolved status;
- net P&L and exit reason;
- explicit no-trade reason when abstaining.

The implementation contains no wallet, broker, order-submission, external mutation, or public-posting authority.

### Execution and shadow layer

An optional strict mode parses point-in-time book snapshots and uses the latest observation at or before each event. It requires a valid market, bid/ask, positive depth, and executable ask at or below the limit. Missing book data fails closed rather than falling back to a print. The independent `evaluate_execution_gate` additionally checks fill probability, target-hit probability, queue/latency penalties, participation cap, and the lower bound of costed EV.

The paper-trading layer records expected price, size, and timestamp, then reconciles them against observed fills. It classifies each record as `PENDING_OBSERVATION`, `RECONCILED`, `MISMATCH`, or `INVALID_OBSERVATION`; it has no order-placement side effect.

## Mathematical profitability condition

For a single fill `F` and sale price `Q`, the pre-fee return on `$1` stake is:

```text
return = Q / F − 1
```

But an exit target is profitable only if its probability of being reached, its residual settlement distribution, fees, slippage, and execution probability jointly make expected net positive. The live decision condition is therefore:

```text
E[net | information available now]
  − execution_uncertainty
  − fees
  − adverse_selection
  > 0
```

The model does not substitute the later maximum for this expectation. That would be lookahead bias.

### Dependence-aware evidence screen

The ordinary lower bound treats every resolved match as independent. That is too optimistic when a day, sport, tournament, or news regime produces many related observations. Each resolved trade therefore carries its match start timestamp, and the engine groups resolved outcomes by `(sport, UTC calendar day)`. It preserves the per-match mean but estimates uncertainty from cluster contributions. A profile must clear both the ordinary and cluster-robust lower bounds, including after best-trade removal. A single cluster is reported without invented dispersion and is not sufficient for final promotion; final promotion still requires a pre-registered block-bootstrap or equivalent dependence-aware analysis over a prospective ledger.

## External market-structure findings

The [Polymarket sampling-markets endpoint](https://docs.polymarket.com/api-reference/markets/get-sampling-markets) exposes market state and fields such as order-book availability, activity, tick size, and fee-related metadata. The [spreads endpoint](https://docs.polymarket.com/api-reference/market-data/get-spreads) exposes best-bid/best-ask spread data. The [CLOB V2 migration documentation](https://docs.polymarket.com/v2-migration) establishes the current CLOB architecture and makes legacy assumptions unsafe.

The [Kalshi order-book WebSocket documentation](https://docs.kalshi.com/websockets/orderbook-updates) shows the correct shape of an execution-grade feed: an initial snapshot followed by order-book deltas. Academic microstructure work on Polymarket reports that trade-direction inference from on-chain executions agrees with order-book data only around 59% of the time, which is a direct warning against treating prints as exact executable-side evidence ([Polymarket microstructure study](https://arxiv.org/abs/2604.24366)). Queue position and adverse-selection research likewise shows why time priority and queue uncertainty must be modeled before claiming realized fills ([queue uncertainty study](https://pubsonline.informs.org/doi/10.1287/mnsc.2023.03371)).

Therefore the current tape engine is a rigorous replay and screening layer, not yet a live execution engine. The next adapter must ingest snapshots/deltas, available size, spread, tick, fees, timestamp latency, cancel/replace events, and actual fills.

## Web research expansion

### Doctoral theses and research systems

The literature review covered doctoral work because the main risk in this project is not inventing another indicator; it is building a valid decision and execution system around a thin, path-dependent market.

- The CMU dissertation [Automated Market Making Theory and Practice](https://kilthub.cmu.edu/articles/thesis/Automated_Market_Making_Theory_and_Practice/6714920) treats prediction-market market making as a distinct inventory and risk problem and studies practical automated market makers. Transfer: maintain explicit inventory and terminal-settlement risk rather than treating every position as a generic asset.
- The Imperial College thesis [SPORTSBET and UBEL](https://wwwhomes.doc.ic.ac.uk/~wjk/publications/tsirimpas-2015.pdf) emphasizes data cleaning, mathematical algorithms, market simulation, execution, calibration, sensitivity analysis, and synchronized historical/realtime streams. Transfer: keep the event engine and replay semantics as first-class artifacts, not hidden inside a strategy script.
- The King's College thesis [A Queue Reactive Stochastic Limit Order Book Simulation Architecture and High Frequency Market Making via Reinforcement Learning](https://kclpure.kcl.ac.uk/portal/en/studentTheses/a-queue-reactive-stochastic-limit-order-book-simulation-architect/) treats queue state, inventory, adverse selection, and dynamic order updates as part of the policy. Transfer: a resting order cannot be counted as a fill without a queue-aware model.
- The UCL thesis [Microstructural Financial Modelling Point Processes and Reinforcement Learning](https://discovery.ucl.ac.uk/id/eprint/10221263/) uses Hawkes-process ideas for memoryful order-book dynamics and stresses minimal assumptions, data-driven validation, and practical applicability. Transfer: use event intensity and recency as candidate features only after execution data exists; do not promote a complex learner from synthetic evidence.
- The Bristol thesis [Deep Learning Based Limit Order Book Modelling and Simulation](https://research-information.bris.ac.uk/en/studentTheses/deep-learning-based-limit-order-book-modelling-and-simulation/) combines neural point processes with agent-based simulation and explicitly distinguishes reconstruction from realistic interactive simulation. Transfer: a quote reconstruction is not an executable simulator; simulator validation must include response to our own orders.
- The 2026 dissertation [Prediction Markets as Financial Markets Herding or Wisdom of the Crowds](https://digitalcommons.du.edu/etd/2756/) finds that prediction markets can be both behavioral aggregation mechanisms and financial pricing venues, with domain-dependent convergence and sluggish adjustment. Transfer: allow price formation to be biased and slow, but estimate that bias by sport, price band, and regime rather than assuming one universal effect.

### Peer-reviewed and preprint findings that change the design

- [The Anatomy of a Decentralized Prediction Market](https://arxiv.org/abs/2604.24366) joins 30 billion Polymarket order-book events to authoritative on-chain trades. It reports that public-feed trade-direction inference agrees with ground truth only about 59% of the time, along with concentrated depth, category-dependent spreads, and depth decay near resolution. Transfer: use authoritative fills for labels and treat print direction as uncertain.
- [Arbitrage Analysis in Polymarket NBA Markets](https://arxiv.org/abs/2605.00864) reconstructs more than 75 million snapshots across 173 games. It finds only seven executable single-market episodes with median duration 3.6 seconds; combinatorial opportunities are more common but are constrained by shallow depth, with 76.9% limited to an average 14.8 shares. Transfer: add a hard capacity gate and do not confuse theoretical arbitrage with scalable profit.
- [OpenMarket](https://arxiv.org/abs/2607.26245) is a public synchronized Polymarket–Binance dataset and pipeline. Its out-of-sample 43-feature logistic model did not beat the order book and its simulated strategy lost after stated fees and slippage. Transfer: the market's own executable book is a high bar; cross-venue features need clock validation and must beat a fee-aware book baseline out of sample.
- [PredictionMarketBench](https://arxiv.org/abs/2602.00133) standardizes event-driven replay from order books, trades, lifecycle, and settlement, with maker/taker and fee modeling. Transfer: the next version of this project should be benchmarked in the same event-driven shape, including cancellation and settlement, before any live authority is considered.
- [Optimal Market Making in Prediction Markets](https://arxiv.org/abs/2607.17991) formulates the binary contract as a stochastic-control problem with both mark-to-market inventory risk and terminal settlement risk. Transfer: the exit layer must optimize terminal wealth and inventory exposure jointly; a local “sell at target” rule is incomplete.
- [XGBoost Learning of Dynamic Wager Placement](https://arxiv.org/abs/2401.06086) reports profitable learned wagering policies inside the Bristol Betting Exchange agent-based model. Transfer and warning: an ABM is useful for stress testing policy behavior, but simulated profitability is not evidence of real-market profitability without an external-data holdout and execution calibration.
- [Optimal Trading with a Trailing Stop](https://arxiv.org/abs/1701.03960) provides a mathematical treatment of double stopping and supports pairing a liquidation limit with a trailing stop under its diffusion assumptions. Transfer: retain the A/B/C sleeve structure, but estimate the trailing distance by regime and test it against actual markouts rather than importing a universal percentage.
- The NBER work [Prediction Markets for Economic Forecasting](https://www.nber.org/system/files/working_papers/w18222/w18222.pdf) and [Explaining the Favorite Longshot Bias](https://www.nber.org/papers/w15923) document that prices need not equal objective probabilities and that low-probability outcomes can be systematically overvalued in betting settings. Transfer: the underdog detector is a selection input, not proof that a low price is cheap; fit calibration by price bucket and sport.
- [Excess Movement in High Frequency Prediction Market Quotes](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7237938) argues that short-lag quote movement can create the appearance of mean-reversion profit and that the effect changes sharply with horizon. Transfer: require horizon-specific markouts, entry delay tests, and a no-midpoint rule; do not infer edge from quote variance alone.

### Public implementations worth reusing as architecture references

These repositories are useful for interfaces and failure modes, not as verified money-making systems:

- [Polymarket rs-clob-client](https://github.com/Polymarket/rs-clob-client) demonstrates typed market and user WebSocket streams for book, price, order, and trade events.
- [Polymarket clob-client order example](https://github.com/Polymarket/clob-client/blob/main/examples/order.ts) shows the market-specific tick-size and risk-flag inputs required to construct an order. The repository status and API surface must be rechecked before use.
- [Bristol Betting Exchange](https://arxiv.org/abs/2108.02419) provides an open agent-based sports-exchange simulator and reports a large speedup from parallel/GPU execution. Use it for adversarial synthetic regimes and capacity experiments, never as a substitute for live-feed replay.
- [OpenMarket repository](https://github.com/gregyoung14/openmarket) provides a reproducible collector, synchronization pipeline, data cards, and walk-forward baseline. Its published null result is especially valuable as a guardrail.
- [Kalshi trading bot framework](https://github.com/Viprasol-Tech/kalshi-trading-bot) separates exchange, strategy, risk, execution, telemetry, and dry-run backtesting. Transfer the separation and dry-run defaults; do not treat its bundled example strategy or synthetic backtest as an edge claim.

### Validation and overfitting controls

The statistical methods pass adds a further protection against “winning” by trying enough variants:

- [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) formalizes the danger that the best historical configuration is a selection artifact. Transfer: keep the profile registry frozen, record every trial, and report the number of candidates searched.
- [White’s Reality Check applied to technical trading rules](https://www.fmg.ac.uk/publications/discussion-papers/data-snooping-technical-trading-rule-performance-and-bootstrap) shows why the null must account for the full universe of rules tested. Transfer: if the 14 profiles or future challengers are tuned on the same history, use a family-wise data-snooping correction or a new untouched holdout.
- [Purged cross-validation with embargo](https://github.com/landtml/purgedcv) supplies an auditable implementation pattern for forward-looking labels and serial dependence. Transfer: any target-hit, markout, or settlement label with a future window must purge overlapping training labels and embargo the boundary.
- [Machine learning for sports betting calibration](https://arxiv.org/abs/2303.06021) highlights that calibration, not accuracy alone, is central when a probability is converted into a wager. Transfer: evaluate Brier score, log loss, reliability slope/intercept, and calibration by sport and price band before using `h` or any state score in EV or sizing.

The resulting research policy is simple: a challenger can compete with the frozen baseline only on a predeclared walk-forward protocol; the final holdout is read once; and a positive result must survive dependence-aware intervals, cost stress, best-trade removal, and the number of alternatives searched.

## Synthesized execution gated algorithm

The web evidence supports one material refinement to the tape algorithm: SPAN HARVEST is a two-stage policy, not one monolithic signal.

1. `Candidate layer`: the current PZOE/APZI replay identifies a potential underdog reversal or continuation setup using only the information available at the decision time.
2. `Execution layer`: a book-aware adapter estimates whether the entry can actually fill and whether the proposed harvest/trail/settlement policy has positive net value after spread, depth, queue, fees, latency, and residual settlement risk.
3. `Abstention layer`: if any required execution input is missing, stale, or fails its lower-bound test, the action is `NO_TRADE` or `SHADOW_ONLY`.

For a proposed buy at executable ask `a`, target sale at executable bid `q`, entry-fill probability `f`, target-hit probability `h`, and conditional fallback return `r` if the target is not reached, use:

```text
EV = f × [h × (q / a − 1) + (1 − h) × r]
     − entry_cost − exit_cost − queue_penalty − latency_penalty
```

Estimate `f`, `h`, and `r` from point-in-time data by sport, opening-price bucket, relative clock, and execution state. Here `r` is a conditional fallback net return per dollar at risk. Calibrate with an expanding historical window, use a simple regularized baseline before any neural/RL challenger, and require a dependence-aware lower confidence bound on `EV` to be positive. The model must use executable bid/ask and available size; a last print or midpoint may be a feature but may not be the settlement of an assumed fill.

The live execution state is therefore:

- `DATA_OK`: fresh book snapshot/delta, valid market status, synchronized event clock, tick/fee metadata, and no feed disagreement;
- `EDGE_OK`: calibrated EV lower bound remains above zero after pessimistic spread, slippage, and latency scenarios;
- `CAPACITY_OK`: requested size is below the conservative available depth and participation cap, with queue-fill probability above threshold;
- `RISK_OK`: per-market stake, correlated exposure, unresolved inventory, drawdown, and time-to-resolution limits are all clear.

Only when all four states are true may a staged rung be placed. The existing A/B/C sleeves then operate on realized fills and executable exit prices. The default research tape remains print-proxy only and cannot claim these states; this is precisely why the current result stays research-only.

The contrarian conclusion from the literature is that adding MACD, a neural network, or reinforcement learning before solving these four gates would increase model complexity faster than it increases trustworthy edge. Momentum/deceleration and an early lead remain useful explanatory features, but they are subordinate to point-in-time calibration and execution economics.

The high-upside research path is selective rather than indiscriminate: search a small declared exit family, isolate the strongest sport/time/liquidity regimes, and increase opportunity capture only when executable edge remains positive under adverse cost and capacity assumptions. Lowering the gates to force trades would increase activity, not expected profit.

## Evidence from the current release

Source snapshot:

- timestamped clean-tape snapshot;
- 597 raw records;
- 512 loaded/kept tapes;
- 85 rejected or omitted;
- 114 unknown ends in the source population;
- pooled sport-relative clock: 159.741667 minutes;
- 487 of the 512 loaded tapes are tennis, so cross-sport generalization is not established.

Descriptive replay of all 14 profiles over all 512 tapes found:

- 13 of 14 profiles had negative total net;
- `shock_wide_zone` was the only positive full-sample profile, at `+$2.3403` total;
- its mean net per resolved fill was `+$0.0371`, but its ordinary 95% lower bound was `−$0.00864` per match;
- its sport/date-cluster lower bound was `−$0.17197`, and its cluster bound after removing the best trade was `−$0.18678`;
- after removing its best trade, the ordinary lower bound was `−$0.08654`;
- no profile therefore proves a durable positive edge.

The new bounded exit-surface search also failed to rescue the edge: its best candidate was `surface_6_shock`, with total net `−$1.7795`, family-wise lower bound `−$0.01653`, cluster lower bound `−$0.09531`, and best-trade-removed family-wise lower bound `−$0.15662`.

Fee stress on the descriptive `shock_wide_zone` lead was:

| Fee/share | Total net | Mean net/fill | Family-wise LCB | Cluster bootstrap LCB |
|---:|---:|---:|---:|---:|
| $0.000 | +$2.3403 | +$0.0371 | −$0.00864 | −$0.07820 |
| $0.005 | +$0.6220 | +$0.0099 | −$0.01210 | −$0.10614 |
| $0.010 | −$1.0962 | −$0.0174 | −$0.01560 | −$0.13460 |
| $0.020 | −$4.5328 | −$0.0719 | −$0.02273 | −$0.19062 |

Strict L2 replay produced zero fills because the supplied 512-tape release contains no execution observations. This is the correct fail-closed result and identifies the next required dataset: synchronized order-book snapshots/deltas plus actual paper fills.

Causal walk-forward replay with the strict gate produced:

```text
matches              512
filled               0
unresolved           0
total net            $0.00
lower bound          $0.00
walk-forward warmup  30
no-profile gate      482
status               RESEARCH_ONLY / NO_PROMOTION
```

This is a successful safety result, not a failed implementation: the engine refused to convert weak or non-executable evidence into trades. The descriptive positive profile is a research lead to test prospectively, not a claim of profitability.

## Unknowns that remain material

The following gaps are not safely inferable from the supplied tape:

- order-book depth and available quantity at each level;
- queue position and time priority;
- partial fills and cancel/replace latency;
- bid/ask spread at the exact event time;
- real fee schedule and rebates;
- market close, halt, and settlement timing;
- whether the source print is executable for the required side and size;
- dependence among matches, leagues, tournaments, and correlated markets;
- calibration of the state score and shock score;
- whether the underdog detector’s candidate set was itself selected using future information;
- performance under regime change and sport expansion.

The algorithm must remain `NO_TRADE` or `SHADOW_ONLY` until these are measured or conservatively bounded.

## Promotion protocol

Promotion is allowed only after all of the following are true:

1. exact replay parity with the source engine and frozen source hashes;
2. a real order-book execution model with spread, depth, queue, partial fill, latency, and fees;
3. positive strict-holdout net lower bound after costs;
4. positive lower bound after removing the best trade;
5. positive result across several expanding walk-forward folds;
6. enough resolved observations by sport/cohort, not merely pooled tennis results;
7. sensitivity to fee, spread, latency, and pessimistic fill assumptions;
8. a prospective shadow ledger with immutable decision and data hashes;
9. reconciliation between simulated and observed paper fills;
10. explicit kill switches for drawdown, stale data, close state, feed disagreement, and unresolved inventory.
11. calibration diagnostics for every probability used in EV or sizing;
12. purged and embargoed validation for overlapping forward labels;
13. a data-snooping correction or untouched holdout accounting for every challenger tried;
14. a capacity report showing how performance changes as requested size approaches available depth.

Until then, the actionable algorithm is the implementation plus its abstention rule—not an instruction to place capital.

## Files

- `span_harvest_unified.py` — unified deterministic research engine, causal feature cache, bounded exit-surface search, cluster-robust selector, strict L2 mode, cost stress, and fail-closed execution/shadow gates.
- `tests/test_span_harvest_unified.py` — 26 focused causal, accounting, fee, unknown-end, cluster, selector, calibration, embargo, execution, stress, and shadow-reconciliation tests for the canonical engine.
- `RESEARCH_STUDY.md` — this research and validation record.
- `SPAN_HARVEST_UNIFIED_DEEP_RESEARCH_STUDY.docx` — shareable Word version of this record.

Focused verification for the current implementation:

```text
py_compile: PASS
unittest:   26/26 PASS in this standalone repository; full workspace regression 30/30 including retained legacy parity tests
feature-cache equivalence probe: 3,159 causal points PASS
full 512-tape descriptive rerun: PASS
12-candidate exit-surface search: PASS / no candidate clears promotion evidence
fee stress: PASS / descriptive edge degrades through zero at $0.01/share
strict L2 replay: PASS / 0 fills because source has no book observations
strict causal walk-forward: PASS / NO_PROFILE_CLEARS_GATE (482 post-warmup)
```

The current artifact is therefore a serious, reproducible, fail-closed algorithmic research system. It is not yet evidence-backed permission to call the strategy profitable.

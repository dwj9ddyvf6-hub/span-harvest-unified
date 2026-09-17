# SPAN HARVEST UNIFIED

Standalone causal prediction-market research engine.

Status: `RESEARCH_ONLY / NO_PROMOTION`

This repository contains the canonical v1.2.0 implementation, its focused tests, and the shareable research study. It is a deterministic replay and decision-control system—not a broker, wallet, order router, or guarantee of profit.

## What it includes

- chronological profile selection with abstention and no lookahead;
- staged entry logic and three inventory sleeves for harvest, trailing/target, and settlement exposure;
- causal slope, bounce, toxicity, shock, and time controls;
- explicit settlement, unresolved-end, fee, and accounting treatment;
- optional point-in-time level-2 execution observations with fail-closed gates;
- family-wise and cluster-robust evidence checks, fee stress, and shadow-fill reconciliation.

## Run the tests

```text
python -m unittest discover -s tests -p "test_*.py" -q
```

The suite covers the core replay, accounting, calibration, overfitting, execution, stress, and shadow-reconciliation invariants.

## Run the command-line engine

```text
python span_harvest_unified.py --help
```

The default public tape and clock sources are declared in the module. Use `--require-execution-book` to fail closed unless contemporaneous executable ask/depth observations are present.

## Evidence status

The included study records the current validation honestly:

- 26/26 canonical-engine tests pass in this standalone repository (the full workspace regression, including retained legacy parity tests, was 30/30);
- the current 512-tape release contains no execution observations, so strict level-2 replay produces zero fills;
- the descriptive pre-fee positive profile does not survive robust confidence, best-trade removal, and fee-stress promotion gates;
- live profitability is therefore unproven, and the engine remains research-only.

Read [`RESEARCH_STUDY.md`](RESEARCH_STUDY.md) for the algorithm, research synthesis, public references, validation results, and promotion protocol. The Word version is [`SPAN_HARVEST_UNIFIED_DEEP_RESEARCH_STUDY.docx`](SPAN_HARVEST_UNIFIED_DEEP_RESEARCH_STUDY.docx).

## Safety boundary

The code has no credentials, wallet, broker, order-submission, or live-capital authority. A print is an observation proxy; it is not proof of executable depth, queue position, or fillability. Do not deploy capital until the promotion requirements in the study are satisfied on prospective, execution-grade data.

## License

MIT. See [`LICENSE`](LICENSE).

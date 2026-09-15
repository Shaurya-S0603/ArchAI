# ArchAI project status

**Updated:** September 15, 2026

**Development preview:** `v0.2.0-alpha.2` — Phase 2G concept-conditioning research

**Release review:** [Draft PR #3](https://github.com/Shaurya-S0603/ArchAI/pull/3)

Phase 2G improves raw neural target prediction, but does not demonstrate overall
quality benefit after repair. The default application remains deterministic;
the optional Phase 2F engine uses the existing frozen checkpoint. Phase 2A–2F
was merged into `main` as `v0.2.0-alpha.1` on September 10, 2026.

## Delivered against the execution plan

| Increment | Delivered |
|---|---|
| 2A–2B | Frozen evaluation, transparent metrics and optional CP-SAT baseline |
| 2C | Governed room graphs, grouped splits and 592 admitted synthetic plans |
| 2D | Reproducible 60,261-parameter CPU model; frozen epoch-96 checkpoint |
| 2E | Strict proposal repair, topology validation and matched comparison |
| 2F | Bounded distinct search, experimental serving/fallback and fresh qualification |
| 2G | Concept-conditioned model, fresh grouped cohorts, three-seed ablation and strong matched controls |

## Latest model evidence

The [Phase 2G report](../reports/phase2g-conditioning.md) evaluates every declared
seed on the same 32 validation briefs. Both neural arms train on 592 targets;
158 validation targets select checkpoints. The 493 reserved test targets from
100 briefs are not scored.

| Gate or measure | Result |
|---|---|
| Raw coordinate MAE versus token ablation | 35.89–36.55% lower across three seeds |
| Repaired diversity versus token ablation | 31.42–35.14% higher |
| Four-arm five-concept output contract | 100% strict valid distinct output |
| Raw geometric validity | 0%; every neural plan still overlaps |
| Conditioned repaired adjacency | 98.98–99.13% |
| Concept/type reference / solver-only adjacency | 100% / 99.89% |
| No diversity regression against all controls | Fail |
| Conditioned warm CPU p95 | 0.818–1.075 seconds on measured runners |
| Overall validation neural benefit | Not demonstrated |

The fixed concept token helps the model predict teacher layouts more accurately.
It does not yet improve final quality over the strong controls. No winning seed
is selected, and validation is not counted as held-out qualification.

## Retained engineering qualification and open release gates

The [Phase 2F qualification](../reports/phase2f-qualification.md) remains the
evidence for the frozen experimental serving path: every 100-brief holdout and
1,000-brief stress input returned five strictly valid, distinct plans, with zero
crashes and warm p95 of 0.799 / 0.785 seconds. These historical cohorts were not
rerun as new Phase 2G qualification.

Model promotion still requires measured downstream neural benefit, prospective
holdout confirmation, independently licensed real-plan evaluation and blinded
human preference above 60%. No external source is admitted and no preference
study or learned ranker is included. Diversity remains within the supported
corridor/perimeter family. Latency excludes cold startup and concurrent queueing.

## Verification and repository hygiene

[The implementation workflow](https://github.com/Shaurya-S0603/ArchAI/actions/runs/34825488348)
passes all eleven jobs: the existing eight checks and three conditioning seeds.
The backend suite passes 93 tests at 93.83% CI coverage (four ML modules skip in
the web-only environment); the dedicated ML/serving/research suite passes 84
tests at 97.57%. Frozen Phase 2D training reproduces the exact original tensor
digest. The report records implementation/merge tree identities and all run links.

Compact reports, protocol, source provenance and cohort identities are tracked.
Datasets, checkpoints, databases, build output and runtime reports remain outside
source control. The changelog preserves the earlier release evidence. Final
metadata/report changes do not tune the evaluated model or repair algorithm.

## Prioritized next sprint

1. Diagnose the validation briefs where learned displacement loses adjacency;
   freeze and test geometry-aware training or discrete slot prediction against
   the same controls. Keep the reserved holdout unscored during development.
2. Broaden topology coverage and review a licensed real-plan source and adapter.
3. Establish blinded, consented pairwise preference evaluation before ranking.
4. Revisit serving integration and default promotion after qualification gates.

No decision blocks further synthetic research. Later decisions concern intended
checkpoint distribution rights, real-plan source admission and the human
evaluation protocol. See [the roadmap](ROADMAP.md) for the Phase 3 semantic 3D/BIM
product track and [the protocol](PHASE2G_PROTOCOL.md) to reproduce Phase 2G.

# ArchAI Layout Generator Card

**Component:** ArchAI transparent layout baseline

**Version:** v0.1.0-dev.1

**Maintained by:** Shaurya Singhal

## Status

This release is **not a trained neural-network or reinforcement-learning model**.
It is a deterministic constraint-based baseline used to make the application
executable, testable, and measurable before ML training begins.

## Purpose

- generate five residential concept layouts from a validated brief;
- represent room relationships as an adjacency graph;
- rank concepts using adjacency and compactness proxies;
- provide a no-GPU fallback for future learned generators.

## Inputs

- site width and depth;
- bedroom, bathroom, household, and optional-room counts;
- architectural style;
- budget and currency;
- sustainability and accessibility priorities.

## Outputs

- rectangular 2D room geometry in metres;
- building and site bounds;
- adjacency, compactness, and circulation-proxy metrics;
- corridor, wall, door, entry, and window topology;
- furniture-use, door-approach, and accessible turning zones;
- a concept ranking score.

## Method

The generator builds a room program from editable minimum and target areas,
reserves a continuous 1.8 m circulation spine, and allocates rooms as weighted
perimeter strips on both sides. It then derives atomic wall segments and selects
a connected spanning set of door openings. Exterior entry and window openings are
added from perimeter walls. A shared-wall graph is scored against functional
adjacency preferences. Furniture-use zones are then fitted within supported room
types, while door-approach zones follow semantic openings and accessible briefs
receive 1.5 m turning-circle overlays in bathrooms and circulation space.

## Evaluation

The current automated suite verifies deterministic results, valid API behavior,
room-area conservation, edited overlap detection, and OBJ geometry output. These
tests establish software correctness only; they do not establish architectural
quality or regulatory compliance.

## Data

No training data is used in v0.1. CubiCasa5K, FloorCAD, or any other dataset must
undergo license, provenance, bias, and split review before a trained model is
added or distributed.

## Limitations

- single-floor rectangular residential concepts only;
- doors and windows are concept geometry, not detailed construction assemblies;
- concept zones are not product-specific furniture layouts or accessibility certification;
- no structural system or building-services coordination;
- generated geometry may require substantial professional revision;
- the score is a transparent heuristic, not confidence or design approval;
- regional, cultural, climatic, and site-specific requirements are not modeled.

## Planned model gate

A trained generator will be released only with a reproducible training pipeline,
held-out evaluation data, comparison against this baseline, documented failure
cases, and hard-constraint checks that remain outside the learned model.

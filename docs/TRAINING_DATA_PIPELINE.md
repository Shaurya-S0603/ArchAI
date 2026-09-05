# Phase 2C training-data contract

Phase 2C provides a governed rectangle-plan adapter, data validation, grouped
splits and a training batch interface. It includes a fresh synthetic pilot.
It does not include a learned model, real-plan license approval, a ResPlan/SVG
parser, or observed door/window annotations. The web API remains unchanged.

## Run from the repository root

```bash
python -m pip install -r requirements.txt
python -m archai.datasets pilot --output data/processed/pilot-v1 --count 120 --seed 20260905
python -m archai.datasets validate data/processed/pilot-v1
```

Output directories are immutable: choose a new destination for a new run. Files:
`records.jsonl`, `manifest.json`, `source.json`, `report.json`, `DATA_CARD.md`,
and `preview.png`. Raw/processed data, quarantined downloads and training runs
are ignored by Git. Only source, documentation, compact reports and QA are committed.
The CI dataset job regenerates the pilot and compares its full report with
`reports/phase2c-dataset.json`. Full generated artifacts expire after 30 days;
the committed generator and reports preserve reproduction.

## Input JSONL schema v1

One object per line with exactly these fields:

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `id` | Unique opaque sample identifier |
| `source_id` | Matches the source manifest ID |
| `building_id` | Same opaque ID for all plans/augmentations of the original building |
| `units` | Exactly `m`; convert known units explicitly in an audited source adapter |
| `footprint` | Rectangle: `x`, `y`, `width`, `depth` in metres |
| `rooms` | 4-32 objects, each with `id`, `type`, `box` (same rectangle fields) |

Coordinates use x to the right and y downward. Opaque IDs allow only ASCII letters,
digits, underscore, dot, colon and hyphen, up to 100 characters. Never encode
addresses or identifying details in IDs. Duplicate sample IDs abort the run.
Labels, addresses, metadata and unsupported fields are rejected, not silently copied.
Unknown types, polygons, pixels and unscaled images are rejected. Do not flatten
an irregular polygon into a bounding rectangle and call it equivalent geometry.

Room taxonomy (fixed order for type encoding): balcony, bathroom, bedroom,
corridor, dining, garage, kitchen, laundry, living, lounge, storage, study, utility.
Minimum areas come from the current ArchAI room library; this is a concept-data
filter, not a jurisdictional standard. It intentionally excludes some real plans.

## Source manifest and external admission

Supply `schema_version`, `id`, `version`, `origin` (synthetic/external), `license`,
`source_url`, SHA-256 of the exact input bytes, `coverage`, `limitations`, and
`review`. The review requires true `training`, `derivatives`, `redistribution`,
`checkpoint_distribution`, `privacy`, plus `reviewer`, ISO `date` and `evidence`.
Evidence must refer to the reviewed license text/version, provenance and privacy
basis. These assertions record a real review; changing booleans is not approval.

No Kaggle source is currently admitted. After a source actually passes the
existing governance checklist and its adapter produces this rectangle schema:

```bash
python -m archai.datasets ingest --input data/raw/admitted-v1/plans.jsonl \
  --source data/raw/admitted-v1/source.json --output data/processed/admitted-v1
```

The CLI checks the source checksum/review, then validates each record. Invalid
records produce reason counts; a source admission failure or zero surviving
plans exits nonzero and publishes no output directory. Review rejection rates
before training; successful ingestion is not a data-quality endorsement.
The Python `preprocess` API also accepts an explicit evaluation exclusion set;
custom callers must supply their evaluation sets as part of governance.

## Canonical targets and normalization

Independent x/y and dimension rounding in the existing generator can leave 1 mm
edge differences. Consolidate clusters with total span at most 2 mm (no unbounded
transitive snapping), prioritizing footprint boundaries. Recheck minimum areas
and overlaps after snapping. No substantial geometry is repaired or invented.

Canonical rooms are ordered by type and geometry. Targets contain
`[x/width, y/depth, room_width/width, room_depth/depth]`, with x/y relative to the
footprint origin and eight decimal places. Physical footprint width/depth remain
available so normalization can be reversed. Source IDs and building IDs are
retained; input room labels and ordering are not.

`adjacency` contains sorted zero-based room-index pairs sharing at least 0.8 m
of boundary. The graph must be connected. These are geometric training targets,
not observed doors, accessible paths, daylight, structural or safety validation.
Training loads revalidate geometry/adjacency and verify file and record hashes.
Hashes detect corruption relative to the manifest; they are not signatures.

## Duplicates, splits and benchmark isolation

Group all records from the same source/building together. Also union exact and
coarse duplicate buckets transitively across building IDs, before removing exact
duplicates. The eight-decimal geometry fingerprint ignores room IDs/order,
translation, uniform scale, reflections and quarter-turns, while preserving
footprint aspect ratio. A three-decimal fingerprint groups likely near copies.
Keep the lexicographically smallest sample ID for an exact geometry class.

Coarse rounding can miss near duplicates at bin boundaries. It is a conservative
guard, not comprehensive similarity detection. Adding new duplicate bridges can
change group assignments; all dataset versions must therefore remain immutable.
Do not merge independently split source datasets without joint regrouping.

Hash each complete group with the split seed into 80% train, 10% validation and
10% test probability ranges. Actual counts depend on groups; small datasets may
have empty splits. There is no silent train/test mixing in the batch loader.

The pilot uses a different generation seed from the frozen 100-case benchmark,
excludes exact benchmark briefs, and excludes groups matching any of its 500
baseline-generated geometries (492 unique coarse keys). The ingest CLI performs
the same baseline geometry exclusion. This is not an independent real-world
benchmark and does not prove exclusion against unknown data sources.

## Training batches

```python
from pathlib import Path
from archai.datasets.training import batches

for batch in batches(Path('data/processed/pilot-v1'), 'train', batch_size=16, seed=7):
    inputs = batch['type_ids'], batch['minimum_area_fraction'], batch['footprint_m']
    targets = batch['target_boxes'], batch['target_adjacency']
    mask = batch['room_mask']
```

Type IDs are one-based with zero padding. Room masks distinguish data from padding;
use the outer product of the room mask for adjacency loss and exclude the diagonal.
Box/adjacency tensors are targets and must not be fed as input features by mistake.
These dependency-free nested lists can be converted to tensors by Phase 2D.
No implicit all-split mode or ML framework import exists. The pilot validates the
interface; it does not yet implement requested-adjacency conditioning, training,
checkpointing or a model architecture.

## Current evidence and remaining gates

The 120-brief pilot produces 600 valid input plans, removes eight exact duplicates,
and retains 592: 477 train / 55 validation / 60 test. All 13 room types are present.
The QA sheet samples minimum/maximum room counts from each split and has been
visually inspected for placement, legibility and aspect-ratio preservation.

Reproducibility tests compare every artifact byte across two runs in the same
environment. Record digests are independent of renderer output. Pillow rendering
bytes can differ across versions; use the manifest hashes for artifact integrity.
Synthetic corridor/perimeter layouts carry strong teacher bias. Next: expand
admitted data, train a small supervised baseline, evaluate on held-out groups,
add constraint repair and diversity selection, then separately assess external
generalization and CPU performance. No learned-quality improvement is claimed here.

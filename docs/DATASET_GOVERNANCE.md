# ArchAI Dataset Governance

## Purpose

This policy controls every dataset used to evaluate or train an ArchAI generator.
No external dataset may enter the pipeline until its license, provenance, privacy,
scope, exclusions, and redistribution conditions have been recorded and reviewed.

## Admitted datasets

| Dataset | Role | Cases | Source | License | Redistribution |
|---|---|---:|---|---|---|
| `archai-synthetic-residential-v1` | Regression evaluation | 100 | Deterministic ArchAI code | MIT | Included in this repository |
| `archai-synthetic-roomgraphs-v1` | Training-interface pilot | 592 plans / 120 briefs | Fresh ArchAI briefs/layouts | MIT | Code/report committed; full data generated locally or in CI |

The Phase 2A dataset contains input briefs only. It does not contain copied floor
plans, scraped images, user projects, addresses, or personal data. Its manifest
pins the schema version, generator seed, split counts, and SHA-256 digest.

External sources under consideration, including Kaggle listings, are maintained
in `docs/DATASET_CANDIDATES.md`. Listing a source there does not admit it. A
Kaggle page, API download, or notebook is a discovery mechanism and does not
replace the original publisher's license or prove permission to distribute
derived weights.

## Fixed splits

| Split | Cases | Permitted use |
|---|---:|---|
| Development | 60 | Implementation and debugging |
| Validation | 20 | Threshold selection and candidate comparison |
| Test | 20 | Final reported comparison after a candidate is frozen |

The fixtures are public and reproducible, so the test split is not a secret or
blind benchmark. Future release claims must include a genuinely independent
evaluation source before they describe real-world generalization.

## External-data admission checklist

Before adding any external plan or annotation dataset, record:

1. canonical source and maintainer;
2. exact version, retrieval date, and immutable checksum;
3. license text and permission for training, derivatives, and redistribution;
4. whether personal, location, or sensitive attributes are present;
5. geographic, cultural, building-type, and annotation coverage;
6. known duplicates, leakage paths, exclusions, and quality limitations;
7. deterministic preprocessing code and rejected-record counts;
8. split policy that prevents building or near-duplicate leakage;
9. artifact license and distribution conditions for resulting checkpoints;
10. reviewer and approval date.

An available download is not proof of permission. Datasets mentioned in research
notes remain excluded until this checklist is complete.

## Privacy and user projects

Saved ArchAI projects are application data, not training data. They must never be
silently added to a dataset. Any future contribution workflow requires clear
consent, de-identification, deletion handling, and a separate governance review.

## Change control

Phase 2C enforces recorded source reviews and input checksums. The current source
record is synthetic-only and does not approve any external dataset. The manifest
validator checks the evidence record; it cannot authenticate legal permissions.
External review and the candidate register remain authoritative admission steps.
See `TRAINING_DATA_PIPELINE.md` for schemas, grouped split policy and limitations.

Changing any case, split, schema, seed, or preprocessing rule requires a new
dataset version and digest. Existing benchmark versions remain immutable so old
reports stay reproducible. Pull requests changing evaluation data must include a
regenerated manifest, baseline report, test updates, and an explanation of metric
movement.

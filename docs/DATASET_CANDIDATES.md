# ArchAI External Dataset Candidate Register

**Review date:** September 3, 2026

## Decision

Kaggle is useful for discovering architectural datasets, but no external dataset
is admitted to ArchAI v0.2.0-dev.2. The next phase will use a candidate only after
the original publisher's license, provenance, privacy, derivative-work terms, and
checkpoint-redistribution terms are recorded. Dataset files must not be committed
or downloaded into the training pipeline before approval.

## Candidate register

| Candidate | Potential use | Current decision | Reason / next evidence required |
|---|---|---|---|
| [ResPlan on Kaggle](https://www.kaggle.com/datasets/resplan/resplan) | Preferred vector/graph generation source; 17,000 residential plans | Quarantined | Strong schema fit, but confirm that the dataset files—not only the paper—have an explicit license permitting training, derivatives, and checkpoint redistribution; document the rights and privacy basis for plans derived from real-estate listings. |
| [ResPlan paper](https://arxiv.org/abs/2508.14006) | Canonical description and provenance evidence | Review source | Use to verify collection and annotation claims; a paper license must not be assumed to license the separate data files. |
| [CubiCasa5K official repository](https://github.com/CubiCasa/CubiCasa5k) | Floor-plan parsing and semantic pretraining | Research-only quarantine | The official dataset license is [CC BY-NC 4.0](https://github.com/CubiCasa/CubiCasa5k/blob/master/LICENSE), so it is incompatible with unrestricted commercial use. Any use needs attribution, noncommercial-scope review, source verification, and an explicit checkpoint-distribution decision. Prefer the official source over Kaggle mirrors. |
| [Floor Plans 500 on Kaggle](https://www.kaggle.com/datasets/umairinayat/floor-plans-500-annotated-object-detection) | Small object-detection pilot | Quarantined | Its YOLO annotations may help parsing rather than layout generation. Verify original image provenance, exact dataset license, class map, duplicates, and redistribution rights. |
| [Floor Plan dataset on Kaggle](https://www.kaggle.com/datasets/asutoshprad/floor-plan-dataset) | Parsing experiment | Rejected pending relicensing | Kaggle currently reports `License Unknown`; do not download, train, or redistribute it. |
| [RPLAN original project](https://wutomwu.github.io/particulars.html?id=1) | Graph-conditioned layout generation | Quarantined | High task relevance, but the public project page does not provide enough evidence here for dataset redistribution and derived-checkpoint rights. Obtain and archive written terms before use. |

## Phase 2C selection rule

ResPlan is the leading technical candidate because its vector geometry and room
connectivity match ArchAI's target representation. It is not approved yet. If its
license and real-estate-source provenance cannot clear the governance checklist,
Phase 2C will continue with synthetic-data expansion and a separate, clearly
licensed research-only parsing experiment rather than weakening the policy.

For any approved source, ingestion must happen through a reproducible script that
records version, checksum, accepted/rejected counts, normalized room taxonomy,
near-duplicate groups, building-level splits, and a generated data card. Raw data,
credentials, and Kaggle API tokens must stay outside Git.

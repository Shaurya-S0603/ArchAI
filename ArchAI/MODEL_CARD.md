# ArchAI — AI Model Card

**Model Name:** ArchAI Space Planning AI
**Version:** v1.0
**Maintained By:** Shaurya Singhal

---

## Purpose

This model is used to:

* Generate intelligent 2D layouts
* Optimize room adjacency
* Enforce spatial rules
* Adapt plans according to survey input

---

## Input

* Number of rooms
* Style
* Budget
* Land size
* Climate preferences

---

## Output

* 2D grid plan
* Room adjacency graph
* Confidence score
* Validity results

---

## Training Data

* Cubicasa 5K
* FloorCAD
* Self-generated datasets

---

## Limitations

* Very large/fancy designs may fail
* Regional codes vary
* Still improving accuracy

---

## Roadmap

✅ Multi-floor support
✅ Region-wise training
✅ Reinforcement learning
✅ Custom style transfer

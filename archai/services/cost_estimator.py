"""Editable parametric cost baseline with no paid data dependency."""

from __future__ import annotations

from typing import Any

from archai.models import DesignBrief, Layout

STYLE_RATE_SGD_M2 = {
    "modern": 2650.0,
    "classic": 3100.0,
    "contemporary": 2800.0,
    "industrial": 2500.0,
    "sustainable": 2950.0,
}

CURRENCY_FROM_SGD = {"SGD": 1.0, "USD": 0.74, "INR": 64.0, "EUR": 0.63, "GBP": 0.55}

BREAKDOWN = {
    "Structure and foundations": 0.30,
    "Envelope and roofing": 0.17,
    "Mechanical and electrical": 0.18,
    "Interior finishes": 0.17,
    "Labor and site work": 0.13,
    "Design contingency": 0.05,
}


def estimate_cost(layout: Layout, brief: DesignBrief) -> dict[str, Any]:
    base_rate = STYLE_RATE_SGD_M2[brief.style]
    sustainability_factor = 1.06 if brief.sustainability else 1.0
    complexity_factor = 1.0 + max(0, len(layout.rooms) - 8) * 0.012
    total_sgd = layout.floor_area * base_rate * sustainability_factor * complexity_factor
    conversion = CURRENCY_FROM_SGD[brief.currency]
    total = total_sgd * conversion
    rate = base_rate * sustainability_factor * complexity_factor * conversion
    budget_delta = brief.budget - total if brief.budget else None
    breakdown = [
        {"category": category, "share": share, "amount": round(total * share, 2)}
        for category, share in BREAKDOWN.items()
    ]
    return {
        "currency": brief.currency,
        "floor_area_m2": round(layout.floor_area, 2),
        "rate_per_m2": round(rate, 2),
        "estimated_total": round(total, 2),
        "budget": round(brief.budget, 2),
        "budget_delta": round(budget_delta, 2) if budget_delta is not None else None,
        "within_budget": budget_delta >= 0 if budget_delta is not None else None,
        "breakdown": breakdown,
        "assumptions": [
            "Concept-stage baseline rates are stored locally and are not live supplier quotations.",
            "Land, tax, financing, professional fees, permits, and unusual site work are excluded.",
            "Replace the editable regional rate table before relying on any project decision.",
        ],
    }

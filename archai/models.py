"""Validated domain models shared by the generation and analysis services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any

ALLOWED_STYLES = {"modern", "classic", "contemporary", "industrial", "sustainable"}
ALLOWED_CURRENCIES = {"SGD", "USD", "INR", "EUR", "GBP"}
ALLOWED_OTHER_ROOMS = {
    "study",
    "garage",
    "laundry",
    "balcony",
    "lounge",
    "storage",
    "utility",
}


def _bounded_number(data: dict[str, Any], key: str, minimum: float, maximum: float) -> float:
    try:
        value = float(data[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number.") from exc
    if not isfinite(value):
        raise ValueError(f"{key} must be a finite number.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{key} must be between {minimum:g} and {maximum:g}.")
    return value


def _bounded_int(data: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = _bounded_number(data, key, minimum, maximum)
    if not value.is_integer():
        raise ValueError(f"{key} must be a whole number.")
    return int(value)


@dataclass(frozen=True)
class DesignBrief:
    site_width_m: float
    site_depth_m: float
    bedrooms: int
    bathrooms: int
    style: str
    budget: float
    currency: str = "SGD"
    household_size: int = 3
    other_rooms: tuple[str, ...] = ()
    sustainability: bool = False
    accessibility: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DesignBrief:
        if not isinstance(data, dict):
            raise ValueError("The request body must be a JSON object.")

        style = str(data.get("style", "modern")).lower().strip()
        if style not in ALLOWED_STYLES:
            raise ValueError(f"style must be one of: {', '.join(sorted(ALLOWED_STYLES))}.")

        currency = str(data.get("currency", "SGD")).upper().strip()
        if currency not in ALLOWED_CURRENCIES:
            raise ValueError(f"currency must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}.")

        raw_other_rooms = data.get("other_rooms", [])
        if not isinstance(raw_other_rooms, list):
            raise ValueError("other_rooms must be a list.")
        other_rooms = tuple(dict.fromkeys(str(room).lower().strip() for room in raw_other_rooms))
        invalid_rooms = set(other_rooms) - ALLOWED_OTHER_ROOMS
        if invalid_rooms:
            raise ValueError(f"Unsupported additional rooms: {', '.join(sorted(invalid_rooms))}.")

        try:
            budget = float(data.get("budget", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("budget must be a number.") from exc
        if budget < 0 or budget > 1_000_000_000:
            raise ValueError("budget must be between 0 and 1,000,000,000.")

        return cls(
            site_width_m=_bounded_number(data, "site_width_m", 10, 60),
            site_depth_m=_bounded_number(data, "site_depth_m", 10, 80),
            bedrooms=_bounded_int(data, "bedrooms", 1, 6),
            bathrooms=_bounded_int(data, "bathrooms", 1, 5),
            style=style,
            budget=budget,
            currency=currency,
            household_size=_bounded_int(
                {"household_size": data.get("household_size", 3)}, "household_size", 1, 12
            ),
            other_rooms=other_rooms,
            sustainability=bool(data.get("sustainability", False)),
            accessibility=bool(data.get("accessibility", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["other_rooms"] = list(self.other_rooms)
        return result


@dataclass
class Room:
    id: str
    type: str
    label: str
    x: float
    y: float
    width: float
    depth: float
    color: str
    minimum_area: float = 4.0

    @property
    def area(self) -> float:
        return self.width * self.depth

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["area"] = round(self.area, 2)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Room:
        try:
            room = cls(
                id=str(data["id"]),
                type=str(data["type"]),
                label=str(data["label"]),
                x=float(data["x"]),
                y=float(data["y"]),
                width=float(data["width"]),
                depth=float(data["depth"]),
                color=str(data.get("color", "#a8c7b0")),
                minimum_area=float(data.get("minimum_area", 4.0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Each room requires id, type, label, x, y, width, and depth.") from exc
        dimensions = (room.x, room.y, room.width, room.depth, room.minimum_area)
        if not all(isfinite(value) for value in dimensions):
            raise ValueError("Room coordinates and dimensions must be finite numbers.")
        if not room.id.strip() or not room.type.strip() or not room.label.strip():
            raise ValueError("Each room requires non-empty id, type, and label values.")
        if room.width <= 0 or room.depth <= 0 or room.minimum_area <= 0:
            raise ValueError("Room width, depth, and minimum area must be greater than zero.")
        if max(abs(room.x), abs(room.y), room.width, room.depth, room.minimum_area) > 10_000:
            raise ValueError("Room coordinates and dimensions exceed the supported range.")
        return room


@dataclass
class Layout:
    id: str
    name: str
    objective: str
    style: str
    site_width_m: float
    site_depth_m: float
    building_bounds: dict[str, float]
    rooms: list[Room]
    score: float = 0
    metrics: dict[str, Any] = field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)
    zones: dict[str, Any] = field(default_factory=dict)

    @property
    def floor_area(self) -> float:
        return sum(room.area for room in self.rooms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "style": self.style,
            "site_width_m": self.site_width_m,
            "site_depth_m": self.site_depth_m,
            "building_bounds": self.building_bounds,
            "rooms": [room.to_dict() for room in self.rooms],
            "score": round(self.score, 1),
            "floor_area": round(self.floor_area, 2),
            "metrics": self.metrics,
            "topology": self.topology,
            "zones": self.zones,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Layout:
        if not isinstance(data, dict) or not isinstance(data.get("rooms"), list):
            raise ValueError("layout must be an object containing a rooms list.")
        if not 1 <= len(data["rooms"]) <= 100:
            raise ValueError("layout must contain between 1 and 100 rooms.")
        try:
            bounds = {
                key: float(data["building_bounds"][key]) for key in ("x", "y", "width", "depth")
            }
            layout = cls(
                id=str(data.get("id", "edited-layout")),
                name=str(data.get("name", "Edited layout")),
                objective=str(data.get("objective", "User edited")),
                style=str(data.get("style", "modern")),
                site_width_m=float(data["site_width_m"]),
                site_depth_m=float(data["site_depth_m"]),
                building_bounds=bounds,
                rooms=[Room.from_dict(room) for room in data["rooms"]],
                score=float(data.get("score", 0)),
                metrics=dict(data.get("metrics", {})),
                topology=dict(data.get("topology", {})),
                zones=dict(data.get("zones", {})),
            )
            dimensions = (
                layout.site_width_m,
                layout.site_depth_m,
                bounds["x"],
                bounds["y"],
                bounds["width"],
                bounds["depth"],
            )
            if not all(isfinite(value) for value in dimensions):
                raise ValueError("Layout dimensions and building bounds must be finite numbers.")
            if layout.site_width_m <= 0 or layout.site_depth_m <= 0:
                raise ValueError("Layout site dimensions must be greater than zero.")
            if bounds["width"] <= 0 or bounds["depth"] <= 0:
                raise ValueError("Layout building dimensions must be greater than zero.")
            return layout
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ValueError) and str(exc).startswith("Each room"):
                raise
            raise ValueError("layout contains invalid dimensions or building bounds.") from exc

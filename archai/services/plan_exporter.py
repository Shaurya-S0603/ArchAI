"""Vector A3 concept plan-sheet export."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from archai.models import DesignBrief, Layout
from archai.version import VERSION

PAGE_WIDTH, PAGE_HEIGHT = landscape(A3)
INK = HexColor("#18342A")
INK_SOFT = HexColor("#52665F")
GREEN = HexColor("#1E6A4A")
BLUE = HexColor("#397FA4")
AMBER = HexColor("#B66B19")
PAPER = HexColor("#FFFDF8")
LINE = HexColor("#D9DED5")


def _wrapped_text(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font: str = "Helvetica",
    size: float = 8,
    leading: float = 10,
) -> float:
    words = str(text).split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and stringWidth(candidate, font, size) > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    canvas.setFont(font, size)
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def _fill_color(value: str) -> Color:
    try:
        color = HexColor(value)
        return Color(
            min(1, color.red + 0.18),
            min(1, color.green + 0.18),
            min(1, color.blue + 0.18),
        )
    except (TypeError, ValueError):
        return HexColor("#DFECE4")


def layout_to_pdf(
    layout: Layout,
    brief: DesignBrief,
    project_name: str = "ArchAI project",
    compliance: dict[str, Any] | None = None,
) -> bytes:
    """Return a single-page, print-ready vector PDF concept sheet."""

    output = BytesIO()
    canvas = Canvas(output, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    canvas.setTitle(f"{project_name} - {layout.name}")
    canvas.setAuthor("ArchAI")
    canvas.setSubject("Concept plan - not for construction")

    margin = 34
    sidebar_width = 225
    gutter = 24
    plan_x = margin
    plan_y = 62
    plan_width = PAGE_WIDTH - 2 * margin - sidebar_width - gutter
    plan_height = PAGE_HEIGHT - 116
    sidebar_x = plan_x + plan_width + gutter

    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 19)
    canvas.drawString(margin, PAGE_HEIGHT - 38, "ArchAI concept plan")
    canvas.setFillColor(GREEN)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(PAGE_WIDTH - margin, PAGE_HEIGHT - 34, "PHASE 1C / SCHEMA V3")
    canvas.setStrokeColor(LINE)
    canvas.line(margin, PAGE_HEIGHT - 49, PAGE_WIDTH - margin, PAGE_HEIGHT - 49)

    site_width = layout.site_width_m
    site_depth = layout.site_depth_m
    scale = min(plan_width / site_width, plan_height / site_depth)
    origin_x = plan_x + (plan_width - site_width * scale) / 2
    origin_y = plan_y + (plan_height - site_depth * scale) / 2

    def px(value: float) -> float:
        return origin_x + value * scale

    def py(value: float) -> float:
        return origin_y + (site_depth - value) * scale

    def draw_rect(x: float, y: float, width: float, depth: float, fill: bool, stroke: bool):
        canvas.rect(px(x), py(y + depth), width * scale, depth * scale, fill=fill, stroke=stroke)

    canvas.saveState()
    canvas.setStrokeColor(HexColor("#8FA093"))
    canvas.setLineWidth(0.7)
    canvas.setDash(4, 3)
    draw_rect(0, 0, site_width, site_depth, fill=False, stroke=True)
    canvas.restoreState()

    bounds = layout.building_bounds
    canvas.setStrokeColor(INK_SOFT)
    canvas.setLineWidth(1.2)
    draw_rect(bounds["x"], bounds["y"], bounds["width"], bounds["depth"], False, True)

    for room in layout.rooms:
        canvas.setFillColor(_fill_color(room.color))
        canvas.setStrokeColor(white)
        canvas.setLineWidth(0.5)
        draw_rect(room.x, room.y, room.width, room.depth, True, True)

    canvas.saveState()
    canvas.setStrokeColor(Color(BLUE.red, BLUE.green, BLUE.blue, alpha=0.65))
    canvas.setLineWidth(0.7)
    canvas.setDash(3, 2)
    for zone in layout.zones.get("clearances", []):
        if zone["shape"] == "circle":
            canvas.circle(px(zone["cx"]), py(zone["cy"]), zone["radius"] * scale, fill=0, stroke=1)
        else:
            draw_rect(zone["x"], zone["y"], zone["width"], zone["depth"], False, True)
    canvas.restoreState()

    canvas.saveState()
    canvas.setStrokeColor(HexColor("#6B746F"))
    canvas.setFillColor(Color(0.92, 0.92, 0.89, alpha=0.35))
    canvas.setLineWidth(0.6)
    canvas.setDash(2, 2)
    for zone in layout.zones.get("furniture", []):
        draw_rect(zone["x"], zone["y"], zone["width"], zone["depth"], True, True)
    canvas.restoreState()

    for wall in layout.topology.get("walls", []):
        canvas.setStrokeColor(INK if wall["kind"] == "exterior" else INK_SOFT)
        canvas.setLineWidth(2.2 if wall["kind"] == "exterior" else 1.3)
        if wall["kind"] == "room_boundary":
            canvas.setStrokeColor(AMBER)
            canvas.setDash(3, 2)
        else:
            canvas.setDash()
        canvas.line(px(wall["x1"]), py(wall["y1"]), px(wall["x2"]), py(wall["y2"]))

    for opening in layout.topology.get("openings", []):
        canvas.setStrokeColor(PAPER)
        canvas.setLineWidth(4.3)
        canvas.line(
            px(opening["x1"]),
            py(opening["y1"]),
            px(opening["x2"]),
            py(opening["y2"]),
        )
        canvas.setStrokeColor(
            BLUE if opening["kind"] == "window" else AMBER if opening["kind"] == "entry_door" else GREEN
        )
        canvas.setLineWidth(2.1 if opening["kind"] == "window" else 1.2)
        canvas.line(
            px(opening["x1"]),
            py(opening["y1"]),
            px(opening["x2"]),
            py(opening["y2"]),
        )

    for room in layout.rooms:
        center_x = px(room.x + room.width / 2)
        center_y = py(room.y + room.depth / 2)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawCentredString(center_x, center_y + 2, room.label[:30])
        canvas.setFont("Helvetica", 5.6)
        canvas.drawCentredString(center_x, center_y - 6, f"{room.area:.1f} m2")

    canvas.setFillColor(INK)
    canvas.setStrokeColor(INK)
    north_x = plan_x + plan_width - 20
    north_y = plan_y + plan_height - 28
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(north_x, north_y + 16, "N")
    canvas.line(north_x, north_y - 10, north_x, north_y + 10)
    canvas.line(north_x, north_y + 10, north_x - 3, north_y + 5)
    canvas.line(north_x, north_y + 10, north_x + 3, north_y + 5)

    bar_metres = 5
    bar_x = plan_x + 12
    bar_y = plan_y + 12
    canvas.setLineWidth(2)
    canvas.line(bar_x, bar_y, bar_x + bar_metres * scale, bar_y)
    canvas.setFont("Helvetica", 6)
    canvas.drawString(bar_x, bar_y + 5, "0")
    canvas.drawRightString(bar_x + bar_metres * scale, bar_y + 5, "5 m")

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.8)
    canvas.rect(sidebar_x, plan_y, sidebar_width, plan_height, fill=0, stroke=1)
    side_x = sidebar_x + 14
    side_width = sidebar_width - 28
    y = plan_y + plan_height - 22
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(side_x, y, layout.name[:36])
    y -= 16
    canvas.setFillColor(INK_SOFT)
    y = _wrapped_text(canvas, project_name[:80], side_x, y, side_width, size=7.5, leading=9)
    y -= 8

    canvas.setFillColor(GREEN)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(side_x, y, "PROJECT BRIEF")
    y -= 13
    canvas.setFillColor(INK)
    details = (
        ("Site", f"{brief.site_width_m:g} x {brief.site_depth_m:g} m"),
        ("Household", str(brief.household_size)),
        ("Bedrooms", str(brief.bedrooms)),
        ("Bathrooms", str(brief.bathrooms)),
        ("Style", brief.style.title()),
        ("Floor area", f"{layout.floor_area:.1f} m2"),
    )
    for label, value in details:
        canvas.setFillColor(INK_SOFT)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(side_x, y, label)
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 6.5)
        canvas.drawRightString(side_x + side_width, y, value)
        y -= 11
    y -= 8

    topology = layout.topology.get("summary", {})
    zoning = layout.zones.get("summary", {})
    canvas.setFillColor(GREEN)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(side_x, y, "SEMANTIC PLAN")
    y -= 14
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 6.8)
    for line in (
        f"{topology.get('walls', 0)} wall segments",
        f"{topology.get('doors', 0)} doors / {topology.get('windows', 0)} windows",
        f"{zoning.get('furniture_zones', 0)} furniture zones",
        f"{zoning.get('clearance_zones', 0)} clearance zones",
    ):
        canvas.drawString(side_x, y, line)
        y -= 10
    y -= 8

    canvas.setFillColor(GREEN)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(side_x, y, "PRELIMINARY CHECKS")
    y -= 14
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 8)
    if compliance:
        canvas.drawString(side_x, y, f"{compliance['status'].upper()} / {compliance['score']}")
        y -= 12
        summary = compliance["summary"]
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(
            side_x,
            y,
            f"{summary['errors']} errors, {summary['warnings']} warnings, {summary['info']} notes",
        )
        y -= 14
    y -= 4
    canvas.setFillColor(AMBER)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(side_x, y, "IMPORTANT")
    y -= 13
    canvas.setFillColor(INK_SOFT)
    _wrapped_text(
        canvas,
        "Concept design only. Not for construction, permitting, structural design, procurement, or code certification. A qualified architect or engineer must verify this plan.",
        side_x,
        y,
        side_width,
        size=6.6,
        leading=9,
    )

    canvas.setFillColor(INK_SOFT)
    canvas.setFont("Helvetica", 6)
    canvas.drawString(margin, 26, f"ArchAI v{VERSION}")
    canvas.drawCentredString(PAGE_WIDTH / 2, 26, "A3 landscape / vector concept sheet")
    canvas.drawRightString(PAGE_WIDTH - margin, 26, "NOT FOR CONSTRUCTION")

    canvas.showPage()
    canvas.save()
    return output.getvalue()

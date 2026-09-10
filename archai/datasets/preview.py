"""Static contact sheet for inspecting processed geometry with preserved aspect ratios."""

from io import BytesIO

from PIL import Image, ImageDraw

from archai.datasets.schema import ROOM_TYPES, SPLITS
from archai.services.layout_generator import ROOM_LIBRARY


def contact_sheet(rows: list[dict]) -> bytes:
    image = Image.new("RGB", (1200, 860), "#fffdf8")
    draw = ImageDraw.Draw(image)
    draw.text(
        (24, 18),
        "ArchAI Phase 2C | canonical room graphs | synthetic pilot QA",
        fill="#18342a",
        font_size=22,
    )
    selected = []
    for split in SPLITS:
        candidates = sorted(
            (r for r in rows if r["split"] == split), key=lambda r: (len(r["rooms"]), r["id"])
        )
        if candidates:
            selected.extend([candidates[0], candidates[-1]])
    for i, row in enumerate(selected):
        col, line = i // 2, i % 2
        ox, oy = 24 + col * 400, 60 + line * 350
        draw.text(
            (ox, oy), f"{row['split']} | {len(row['rooms'])} rooms", fill="#18342a", font_size=18
        )
        draw.text((ox, oy + 24), row["id"][-45:], fill="#52665f", font_size=12)
        bw, bh = row["footprint_m"]
        scale = min(350 / bw, 260 / bh)
        px, py = ox + (350 - bw * scale) / 2, oy + 50
        draw.rectangle((px, py, px + bw * scale, py + bh * scale), outline="#18342a")
        for index, room in enumerate(row["rooms"]):
            x, y, w, h = room["box"]
            left, top = px + x * bw * scale, py + y * bh * scale
            right, bottom = left + w * bw * scale, top + h * bh * scale
            draw.rectangle(
                (left, top, right, bottom),
                fill=ROOM_LIBRARY[room["type"]]["color"],
                outline="#ffffff",
                width=1,
            )
            draw.text(
                ((left + right) / 2, (top + bottom) / 2),
                str(index + 1),
                anchor="mm",
                fill="#18342a",
                font_size=12,
            )
    for i, kind in enumerate(ROOM_TYPES):
        x, y = 24 + (i % 7) * 167, 773 + (i // 7) * 25
        draw.rectangle((x, y, x + 12, y + 12), fill=ROOM_LIBRARY[kind]["color"])
        draw.text((x + 17, y), kind, fill="#18342a", font_size=12)
    draw.text(
        (24, 837),
        "Room numbers index canonical targets. Shared boundaries are not door annotations.",
        fill="#52665f",
        font_size=12,
    )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()

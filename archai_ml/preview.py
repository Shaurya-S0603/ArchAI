"""Fixed-ID prediction QA, with target and raw predicted geometry side by side."""

import io

from PIL import Image, ImageDraw

from archai.services.layout_generator import ROOM_LIBRARY


def prediction_sheet(rows, predictions):
    by_id = {r["id"]: r for r in rows}
    selected = sorted(predictions, key=lambda p: p["id"])[:6]
    image = Image.new("RGB", (960, 80 + 240 * len(selected)), "#f7f7f2")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((24, 18), "ArchAI Phase 2D | Target (left) / raw neural prediction (right)", fill="black")
    draw.text((24, 42), "First six held-out IDs. Overlap is shown, not repaired. Concept research only.",
              fill="black")
    for k, prediction in enumerate(selected):
        row = by_id[prediction["id"]]
        w, h = row["footprint_m"]
        scale = min(400 / w, 180 / h)
        draw.text((24, 84 + k * 240),
                  f"{row['id']} | raw geometry valid: {prediction['geometric_valid']}", fill="black")
        for column, boxes in enumerate(([r["box"] for r in row["rooms"]], prediction["boxes"])):
            x, y = 24 + column * 480, 108 + k * 240
            draw.rectangle((x, y, x + w * scale, y + h * scale), outline="black", width=2)
            for room, box in zip(row["rooms"], boxes, strict=True):
                bx, by, bw, bh = box
                rect = (x + bx * w * scale, y + by * h * scale,
                        x + (bx + bw) * w * scale, y + (by + bh) * h * scale)
                color = ROOM_LIBRARY[room["type"]]["color"]
                rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
                draw.rectangle(rect, fill=(*rgb, 110), outline=(*rgb, 255), width=2)
                if rect[2] - rect[0] > 38 and rect[3] - rect[1] > 14:
                    draw.text((rect[0] + 3, rect[1] + 2), room["type"][:5], fill="black")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()

from __future__ import annotations

from pathlib import Path
import textwrap

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "assets" / "screens"
OUT = ROOT / "final-demo.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 30


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


FONT_TITLE = font(78, True)
FONT_SUBTITLE = font(34)
FONT_OVERLAY = font(34, True)
FONT_BODY = font(28)
FONT_SMALL = font(22)


def cover(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#f8fafc")
    canvas.paste(image, ((WIDTH - image.width) // 2, (HEIGHT - image.height) // 2))
    return canvas


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, radius: int = 22) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def add_overlay(frame: Image.Image, title: str, subtitle: str | None = None) -> Image.Image:
    frame = frame.copy()
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = (56, 54, 1120, 170 if subtitle else 130)
    rounded_rect(draw, box, (15, 23, 42, 214), 24)
    draw.text((86, 76), title, font=FONT_OVERLAY, fill="#ffffff")
    if subtitle:
        draw.text((86, 120), subtitle, font=FONT_SMALL, fill="#cbd5e1")
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def card(title: str, subtitle: str, footer: str = "") -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0b1120")
    draw = ImageDraw.Draw(img)
    draw.ellipse((1280, -260, 2140, 600), fill="#111827")
    draw.ellipse((-260, 680, 520, 1460), fill="#172554")
    draw.rounded_rectangle((136, 132, 238, 234), radius=28, fill="#ffffff")
    draw.arc((158, 154, 216, 212), 35, 325, fill="#111827", width=8)
    draw.line((178, 183, 203, 183), fill="#111827", width=8)
    draw.ellipse((199, 176, 214, 191), fill="#22d3ee")
    draw.text((136, 314), title, font=FONT_TITLE, fill="#ffffff")
    y = 425
    for line in textwrap.wrap(subtitle, 64):
        draw.text((140, y), line, font=FONT_SUBTITLE, fill="#cbd5e1")
        y += 48
    if footer:
        draw.text((140, 930), footer, font=FONT_BODY, fill="#94a3b8")
    return img


def fit_frame(base: Image.Image, progress: float) -> Image.Image:
    # Subtle motion without cropping important UI.
    scale = 1.0 + 0.012 * progress
    w, h = int(WIDTH * scale), int(HEIGHT * scale)
    img = base.resize((w, h), Image.Resampling.BICUBIC)
    x = (w - WIDTH) // 2
    y = (h - HEIGHT) // 2
    return img.crop((x, y, x + WIDTH, y + HEIGHT))


def frames_for(base: Image.Image, seconds: float, overlay: tuple[str, str | None] | None = None):
    total = int(seconds * FPS)
    for i in range(total):
        frame = fit_frame(base, i / max(1, total - 1))
        if overlay:
            frame = add_overlay(frame, overlay[0], overlay[1])
        yield frame


def fade(a: Image.Image, b: Image.Image, seconds: float = 0.35):
    total = max(1, int(seconds * FPS))
    for i in range(total):
        yield Image.blend(a, b, (i + 1) / total)


SCENES = [
    (card("Chronos Engine", "AI decision intelligence that turns work history into simulated future paths.", "React · FastAPI · Chroma · NetworkX · Fireworks/Tavily-ready"), 5.0, None),
    (cover(SCREENS / "01-landing.png"), 8.0, ("Start with a decision", "A user needs evidence-backed career and product-positioning guidance.")),
    (cover(SCREENS / "02-connect-data.png"), 10.0, ("Connect the memory graph", "GitHub, Slack, Notion, uploads, or a demo-safe sample workspace.")),
    (cover(SCREENS / "03-ingesting.png"), 5.0, ("Ingestion runs", "Accelerated: Chronos extracts sources into graph nodes and evidence.")),
    (cover(SCREENS / "05-define-filled.png"), 12.0, ("Define the strategic fork", "Three paths are compared against goals, constraints, and context.")),
    (cover(SCREENS / "06-simulating.png"), 5.0, ("Simulation in progress", "Accelerated: evidence, precedents, and agents are evaluated.")),
    (cover(SCREENS / "07-timelines.png"), 18.0, ("Evidence-backed futures", "Timeline branches expose probability, expected regret, milestones, and confidence.")),
    (cover(SCREENS / "08-memory-graph.png"), 13.0, ("Trace the reasoning", "A focused graph makes the evidence and source labels inspectable.")),
    (cover(SCREENS / "10-future-self-answer.png"), 18.0, ("Ask Future Self", "The answer cites memory graph nodes and external evidence instead of generic advice.")),
    (card("Chronos Engine", "The benefit: decisions become inspectable simulations, not one-off guesses.", "Submission build · local demo validated · github.com/shurender/Chronos-AI"), 6.0, None),
]


def main() -> None:
    previous: Image.Image | None = None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=8, macro_block_size=1) as writer:
        for base, seconds, overlay in SCENES:
            first = add_overlay(base, overlay[0], overlay[1]) if overlay else base
            if previous is not None:
                for frame in fade(previous, first):
                    writer.append_data(np.asarray(frame))
            last = first
            for frame in frames_for(base, seconds, overlay):
                writer.append_data(np.asarray(frame))
                last = frame
            previous = last
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

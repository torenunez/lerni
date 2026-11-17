"""Draw Lerni's home-screen icons (v4.6.5): the MentalMap, interests linked to a golden L.

    .venv/bin/python scripts/make_icons.py   # writes icon.png and icon-dev.png

Needs Pillow (run by hand, not at serve time). Drawn on a 100-unit grid, at 4× then shrunk,
so the edges stay smooth. The squares are full bleed: iOS rounds the corners itself.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "src" / "lerni" / "student" / "web"
SIZE = 180  # iOS home-screen icon, in pixels
SCALE = SIZE * 4 / 100  # grid units to drawing pixels
GOLD, GOLD_TEXT = "#FAC775", "#633806"  # the center node and its L
NODES = ((26, 28), (76, 30), (28, 74), (74, 72))  # the interests around the center


def draw(background: str, links: str, dev: bool) -> Image.Image:
    """One icon: four interests linked to a golden L; development adds a red DEV band.

    Args:
        background: The square's color.
        links: The interests' and links' color.
        dev: Whether to add the band.
    Returns:
        The icon at SIZE × SIZE.
    """
    big = Image.new("RGB", (SIZE * 4, SIZE * 4), background)
    pen = ImageDraw.Draw(big)

    def at(x: float, y: float) -> tuple[float, float]:  # grid units to pixels
        return x * SCALE, y * SCALE

    def dot(x: float, y: float, r: float, color: str) -> None:
        pen.ellipse([*at(x - r, y - r), *at(x + r, y + r)], fill=color)

    for x, y in NODES:  # links first, so the dots sit on top
        pen.line([at(50, 50), at(x, y)], fill=links, width=round(4 * SCALE))
    for x, y in NODES:
        dot(x, y, 8, links)
    dot(50, 50, 15, GOLD)
    # the L as two bars, so no font is needed
    pen.rectangle([*at(44, 41), *at(48.5, 59)], fill=GOLD_TEXT)  # upright
    pen.rectangle([*at(44, 54.5), *at(57, 59)], fill=GOLD_TEXT)  # foot
    if dev:
        pen.rectangle([*at(0, 84), *at(100, 100)], fill="#E24B4A")  # the DEV band
        # D, E, V as bars and a wedge, 6 units tall, centered on the band
        for x0, y0, x1, y1 in ((38, 89, 39.5, 95), (38, 89, 41.5, 90.2), (38, 93.8, 41.5, 95),
                               (41, 90, 42.5, 94),  # D: spine, top, bottom, bowl
                               (45, 89, 46.5, 95), (45, 89, 49.5, 90.2), (45, 91.4, 48.5, 92.6),
                               (45, 93.8, 49.5, 95)):  # E: spine and three arms
            pen.rectangle([*at(x0, y0), *at(x1, y1)], fill="#FFFFFF")
        pen.polygon([at(52, 89), at(53.6, 89), at(55, 93.4), at(56.4, 89), at(58, 89),
                     at(55.7, 95), at(54.3, 95)], fill="#FFFFFF")  # V
    return big.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    draw("#0F6E56", "#9FE1CB", dev=False).save(OUT / "icon.png", optimize=True)  # production
    draw("#2C2C2A", "#888780", dev=True).save(OUT / "icon-dev.png", optimize=True)  # development
    print(f"wrote {OUT / 'icon.png'} and {OUT / 'icon-dev.png'}")


if __name__ == "__main__":
    main()

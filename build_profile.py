"""Build the profile card: pulsing asteroid particles behind the text."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "profile.svg"
FONT_PATH = r"C:\Windows\Fonts\msyhbd.ttc"

BG = "#07070b"
CYAN = "#22d3ee"
MAGENTA = "#e879f9"
INK = "#f4feff"

W = 1120
H = 680


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=0)


def bitmap(text, font_px, step):
    face = font(font_px)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=face)
    pad = step * 2
    image = Image.new("L", (right - left + pad * 2, bottom - top + pad * 2), 0)
    ImageDraw.Draw(image).text((pad - left, pad - top), text, font=face, fill=255)
    width = max(1, image.size[0] // step)
    height = max(1, image.size[1] // step)
    small = image.resize((width, height), Image.Resampling.BOX)
    pixels = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if small.getpixel((x, y)) > 80
    ]
    if not pixels:
        raise SystemExit(f"No pixels for {text!r}")
    min_x = min(x for x, _y in pixels)
    min_y = min(y for _x, y in pixels)
    max_x = max(x for x, _y in pixels)
    max_y = max(y for _x, y in pixels)
    trimmed = [(x - min_x, y - min_y) for x, y in pixels]
    return trimmed, max_x - min_x + 1, max_y - min_y + 1


def runs(pixels):
    rows = {}
    for x, y in pixels:
        rows.setdefault(y, []).append(x)
    rects = []
    for y, xs in rows.items():
        xs = sorted(set(xs))
        start = prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
            else:
                rects.append((start, y, prev - start + 1))
                start = prev = x
        rects.append((start, y, prev - start + 1))
    return rects


def emit_pixels(pixels, ox, oy, cell, fill, gap=1):
    parts = []
    body = cell - gap
    for x, y, width in runs(pixels):
        parts.append(
            f'<rect x="{ox + x * cell}" y="{oy + y * cell}" '
            f'width="{width * cell - gap}" height="{body}" fill="{fill}"/>'
        )
    return "".join(parts)


def paint(text, font_px, step, cell, x, y, fill, anchor="middle"):
    pixels, tw, th = bitmap(text, font_px, step)
    width = tw * cell
    height = th * cell
    if anchor == "middle":
        origin = x - width / 2
    elif anchor == "start":
        origin = x
    else:
        origin = x - width
    return emit_pixels(pixels, origin, y, cell, fill), width, height


def rect(x, y, w, h, fill, opacity=None):
    extra = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{extra}/>'


class Rng:
    def __init__(self, seed):
        self.state = seed & 0x7FFFFFFF

    def unit(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state / 0x7FFFFFFF

    def span(self, low, high):
        return low + (high - low) * self.unit()


CYCLE = 6.8
CLOCK = 'keyTimes="0;0.2;0.52;0.68;1" calcMode="linear" dur="6.8s" repeatCount="indefinite"'


def pulse(inner, outer):
    distances = (inner, inner, outer, outer, inner)
    values = ";".join(f"{distance:.1f},0" for distance in distances)
    return f'values="{values}" {CLOCK}'


def asteroid_svg(size, kind, color):
    shapes = {
        0: (
            rect(-size * 0.35, -1, size * 0.3, 2, color, 0.35)
            + rect(0, -size * 0.32, size, size * 0.58, color)
            + rect(size * 0.62, 0, size * 0.42, size * 0.42, color)
        ),
        1: (
            rect(-size * 0.32, -1, size * 0.28, 2, color, 0.35)
            + rect(-size * 0.1, -size * 0.42, size * 0.95, size * 0.38, color)
            + rect(size * 0.15, -size * 0.05, size * 0.5, size * 0.62, color)
        ),
        2: (
            rect(-size * 0.3, -1, size * 0.26, 2, color, 0.35)
            + rect(0, -size * 0.36, size * 0.7, size * 0.7, color)
            + rect(size * 0.4, size * 0.08, size * 0.36, size * 0.32, color)
        ),
    }
    return shapes[kind]


def field(cx, cy, frozen=None):
    rng = Rng(11)
    groups = (
        ("dust", 70, (0, 22), (460, 620), (4, 7), (0.45, 0.8)),
        ("rock", 90, (2, 36), (600, 820), (8, 13), (0.75, 1)),
        ("chunk", 32, (4, 48), (740, 980), (14, 22), (0.9, 1)),
    )
    colors = (CYAN, MAGENTA, INK)
    parts = []
    index = 0
    for _name, count, inner_span, outer_span, size_span, opacity_span in groups:
        for _ in range(count):
            angle = rng.unit() * 360
            inner = rng.span(*inner_span)
            outer = rng.span(*outer_span)
            size = rng.span(*size_span)
            opacity = rng.span(*opacity_span)
            color = colors[index % 3]
            kind = index % 3
            index += 1
            shape = asteroid_svg(size, kind, color)
            if frozen == "out":
                body = f'<g transform="translate({outer:.1f},0) scale(1.2)">{shape}</g>'
            elif frozen == "in":
                body = f'<g transform="translate({inner:.1f},0)">{shape}</g>'
            else:
                body = (
                    "<g>"
                    f'<animateTransform attributeName="transform" type="translate" {pulse(inner, outer)}/>'
                    "<g>"
                    f'<animateTransform attributeName="transform" type="scale" '
                    f'values="1,1;1,1;1.15,1.15;1.15,1.15;1,1" {CLOCK}/>'
                    f"{shape}</g></g>"
                )
            parts.append(
                f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({angle:.2f})" opacity="{opacity:.2f}">'
                f"{body}</g>"
            )
    return "".join(parts)


def broken_frame():
    t = 3
    x, y, w, h = 10, 10, W - 20, H - 20
    return "".join(
        (
            rect(x, y, w * 0.34, t, CYAN),
            rect(x + w * 0.4, y - 4, w * 0.16, t, MAGENTA),
            rect(x + w * 0.6, y, w * 0.4, t, CYAN),
            rect(x, y + h - t, w * 0.48, t, CYAN),
            rect(x + w * 0.54, y + h - t + 4, w * 0.2, t, MAGENTA),
            rect(x + w * 0.78, y + h - t, w * 0.22, t, CYAN),
            rect(x, y, t, h * 0.4, CYAN),
            rect(x - 4, y + h * 0.46, t, h * 0.14, MAGENTA),
            rect(x, y + h * 0.64, t, h * 0.36, CYAN),
            rect(x + w - t, y, t, h * 0.28, CYAN),
            rect(x + w - t + 4, y + h * 0.34, t, h * 0.18, CYAN),
            rect(x + w - t, y + h * 0.56, t, h * 0.44, CYAN),
        )
    )


def build(frozen=None):
    meta_font, meta_step, meta_cell = 34, 2, 3
    interests = "篮球、跑步、游泳、听歌...."
    status = "学习ing"
    name_svg, _nw, name_h = paint("lisuhang11", 52, 1, 2, W / 2, 0, INK)
    tag_svg, _tw, tag_h = paint("一个很有idea的开发者", 32, 1, 2, W / 2, 0, MAGENTA)
    label_1, label_w, meta_h = paint("兴趣", meta_font, meta_step, meta_cell, 0, 0, CYAN, anchor="start")
    value_1, value_1_w, _h = paint(interests, meta_font, meta_step, meta_cell, 0, 0, INK, anchor="start")
    label_2, label_2_w, _h = paint("正在", meta_font, meta_step, meta_cell, 0, 0, MAGENTA, anchor="start")
    value_2, value_2_w, _h = paint(status, meta_font, meta_step, meta_cell, 0, 0, INK, anchor="start")
    label_w = max(label_w, label_2_w)
    gap = 18
    block_w = label_w + gap + max(value_1_w, value_2_w)
    block_x = (W - block_w) / 2

    block_h = name_h + 16 + tag_h + 26 + meta_h + 16 + meta_h
    top = (H - block_h) / 2
    name_y = top
    tag_y = name_y + name_h + 16
    meta_1_y = tag_y + tag_h + 26
    meta_2_y = meta_1_y + meta_h + 16

    text = (
        f'<g transform="translate(0,{name_y})">{name_svg}</g>'
        f'<g transform="translate(0,{tag_y})">{tag_svg}</g>'
        f'<g transform="translate({block_x},{meta_1_y})">{label_1}</g>'
        f'<g transform="translate({block_x + label_w + gap},{meta_1_y})">{value_1}</g>'
        f'<g transform="translate({block_x},{meta_2_y})">{label_2}</g>'
        f'<g transform="translate({block_x + label_w + gap},{meta_2_y})">{value_2}</g>'
    )
    desc = "lisuhang11，一个很有idea的开发者。兴趣：篮球、跑步、游泳、听歌.... 正在：学习ing。"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" shape-rendering="crispEdges" role="img">
  <title>lisuhang11</title>
  <desc>{desc}</desc>
  <defs>
    <clipPath id="card">
      <rect width="{W}" height="{H}"/>
    </clipPath>
  </defs>
  <g clip-path="url(#card)">
    {rect(0, 0, W, H, BG)}
    {field(W / 2, H / 2, frozen)}
    {text}
  </g>
  {broken_frame()}
</svg>
'''


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

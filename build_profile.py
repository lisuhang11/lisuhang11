"""Build the profile card SVG. Text is outlined so it does not depend on fonts."""

import math
import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection, TTFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "profile.svg"

BOLD_PATH = r"C:\Windows\Fonts\msyhbd.ttc"
REGULAR_PATH = r"C:\Windows\Fonts\msyh.ttc"

BG = "#07070b"
CYAN = "#22d3ee"
MAGENTA = "#e879f9"
INK = "#f4feff"
MUTED = "#9ee7f0"

W = 1120
WIN_X, WIN_Y, WIN_W, WIN_H = 36, 36, 1048, 400
HOLD = 2.5
SLIDE = 0.55
PERIOD = HOLD + SLIDE
FRAME_COUNT = 4
TOTAL = PERIOD * FRAME_COUNT

NUMBER = re.compile(r"-?\d+\.\d+|-?\d+")


def load_face(path):
    if path.lower().endswith(".ttc"):
        return TTCollection(path).fonts[0]
    return TTFont(path)


BOLD = load_face(BOLD_PATH)
REGULAR = load_face(REGULAR_PATH)


def quantize(d):
    def repl(match):
        value = float(match.group(0))
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        if text in ("-0", ""):
            return "0"
        return text

    return NUMBER.sub(repl, d)


def glyph_name(font, char):
    cmap = font.getBestCmap() or {}
    return cmap.get(ord(char))


def measure(font, text, size, tracking=0):
    units = font["head"].unitsPerEm
    scale = size / units
    hmtx = font["hmtx"]
    width = 0.0
    for index, char in enumerate(text):
        name = glyph_name(font, char)
        if name is None:
            width += size * 0.5
        else:
            width += hmtx[name][0] * scale
        if index != len(text) - 1:
            width += tracking
    return width


def text_path(font, text, size, x, baseline, tracking=0, anchor="middle"):
    missing = [char for char in text if glyph_name(font, char) is None]
    if missing:
        raise SystemExit(f"Missing glyphs {missing!r} in {text!r}")
    width = measure(font, text, size, tracking)
    if anchor == "middle":
        cursor = x - width / 2
    elif anchor == "start":
        cursor = x
    else:
        cursor = x - width
    units = font["head"].unitsPerEm
    scale = size / units
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    commands = []
    for index, char in enumerate(text):
        name = glyph_name(font, char)
        pen = SVGPathPen(glyph_set)
        transform = TransformPen(pen, (scale, 0, 0, -scale, cursor, baseline))
        glyph_set[name].draw(transform)
        commands.append(pen.getCommands())
        cursor += hmtx[name][0] * scale
        if index != len(text) - 1:
            cursor += tracking
    return quantize(" ".join(commands)), width


def paint_text(font, text, size, x, baseline, fill, tracking=0, anchor="middle", glow=None):
    d, width = text_path(font, text, size, x, baseline, tracking, anchor)
    parts = []
    if glow:
        color, stroke_width, opacity = glow
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{stroke_width}" '
            f'stroke-linejoin="round" stroke-linecap="round" opacity="{opacity}"/>'
        )
    parts.append(f'<path d="{d}" fill="{fill}"/>')
    return "".join(parts), width


def smoothstep(t):
    return t * t * (3 - 2 * t)


def slide_keyframes():
    times = [0.0]
    values = [0.0]
    steps = 6
    for index in range(FRAME_COUNT):
        hold_end = index * PERIOD + HOLD
        times.append(hold_end / TOTAL)
        values.append(-index * WIN_W)
        for step in range(1, steps + 1):
            t = step / steps
            times.append((hold_end + SLIDE * t) / TOTAL)
            values.append((-index - smoothstep(t)) * WIN_W)
    times[-1] = 1.0
    for previous, current in zip(times, times[1:]):
        if current <= previous:
            raise SystemExit(f"keyTimes not increasing: {times}")
    return times, values


def fmt_times(times):
    rendered = []
    for time in times:
        text = f"{time:.5f}".rstrip("0").rstrip(".")
        rendered.append(text or "0")
    return ";".join(rendered)


def fmt_values(values):
    return ";".join(f"{value:.2f},0" for value in values)


def arc(cx, cy, radius, start_deg, end_deg):
    start = math.radians(start_deg)
    end = math.radians(end_deg)
    x0 = cx + radius * math.cos(start)
    y0 = cy + radius * math.sin(start)
    x1 = cx + radius * math.cos(end)
    y1 = cy + radius * math.sin(end)
    large = 1 if (end_deg - start_deg) % 360 > 180 else 0
    return (
        f"M {x0:.2f},{y0:.2f} A {radius:.2f},{radius:.2f} 0 {large} 1 {x1:.2f},{y1:.2f}"
    )


def frame_shell():
    return (
        f'<rect width="{WIN_W}" height="{WIN_H}" fill="{BG}"/>'
        f'<rect width="{WIN_W}" height="{WIN_H}" fill="url(#dots)" opacity="0.9"/>'
    )


def frame_hello():
    cx, cy = WIN_W / 2, 188
    return (
        frame_shell()
        + f'<circle cx="{cx}" cy="{cy}" r="156" fill="none" stroke="{CYAN}" stroke-width="1" opacity="0.18"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="118" fill="none" stroke="{CYAN}" stroke-width="1.25" stroke-dasharray="2 9" opacity="0.85"/>'
        + f'<path d="{arc(cx, cy, 118, 206, 338)}" fill="none" stroke="{CYAN}" stroke-width="2.5" stroke-linecap="round"/>'
        + f'<path d="{arc(cx, cy, 138, 18, 132)}" fill="none" stroke="{MAGENTA}" stroke-width="2" stroke-linecap="round" opacity="0.95"/>'
        + paint_text(
            BOLD, "你好", 104, cx, 214, INK, glow=(CYAN, 10, 0.28)
        )[0]
        + paint_text(BOLD, "你好", 104, cx, 214, INK)[0]
    )


def frame_light():
    return (
        frame_shell()
        + f'<rect x="48" y="196" width="{WIN_W - 96}" height="36" rx="18" fill="url(#beamSoft)"/>'
        + f'<rect x="48" y="208" width="{WIN_W - 96}" height="12" rx="6" fill="url(#beam)"/>'
        + '<circle cy="214" r="18" fill="#22d3ee" opacity="0.28">'
        + '<animate attributeName="cx" values="70;978" dur="2.4s" repeatCount="indefinite"/>'
        + '<animate attributeName="opacity" values="0;0.28;0.28;0" keyTimes="0;0.14;0.86;1" dur="2.4s" repeatCount="indefinite"/>'
        + "</circle>"
        + '<circle cy="214" r="6.5" fill="#f7feff">'
        + '<animate attributeName="cx" values="70;978" dur="2.4s" repeatCount="indefinite"/>'
        + '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.14;0.86;1" dur="2.4s" repeatCount="indefinite"/>'
        + "</circle>"
        + paint_text(
            BOLD, "光从左往右", 46, WIN_W / 2, 132, INK, glow=(CYAN, 6, 0.22)
        )[0]
    )


def frame_split():
    phrase = [("青", CYAN), ("，然后", INK), ("品红", MAGENTA)]
    size = 52
    total = sum(measure(BOLD, text, size) for text, _color in phrase)
    cursor = (WIN_W - total) / 2
    painted = []
    for text, color in phrase:
        painted.append(paint_text(BOLD, text, size, cursor, 214, color, anchor="start")[0])
        cursor += measure(BOLD, text, size)
    return (
        frame_shell()
        + f'<rect width="{WIN_W / 2}" height="{WIN_H}" fill="{CYAN}" opacity="0.14">'
        + '<animate attributeName="opacity" values="0.08;0.2;0.08" dur="3.4s" repeatCount="indefinite"/>'
        + "</rect>"
        + f'<rect x="{WIN_W / 2}" width="{WIN_W / 2}" height="{WIN_H}" fill="{MAGENTA}" opacity="0.14">'
        + '<animate attributeName="opacity" values="0.2;0.08;0.2" dur="3.4s" repeatCount="indefinite"/>'
        + "</rect>"
        + f'<rect x="{WIN_W / 2 - 1}" y="48" width="2" height="112" fill="{INK}" opacity="0.8"/>'
        + f'<rect x="{WIN_W / 2 - 1}" y="248" width="2" height="104" fill="{INK}" opacity="0.8"/>'
        + "".join(painted)
    )


def frame_again():
    cx, cy, radius = WIN_W / 2, 156, 74
    left = cx - radius
    right = cx + radius
    orbit = (
        f"M {right:.2f},{cy:.2f} "
        f"A {radius:.2f},{radius:.2f} 0 0 1 {left:.2f},{cy:.2f} "
        f"A {radius:.2f},{radius:.2f} 0 0 1 {right:.2f},{cy:.2f}"
    )
    return (
        frame_shell()
        + f'<circle cx="{cx}" cy="{cy}" r="108" fill="none" stroke="{MAGENTA}" stroke-width="1" opacity="0.35"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{CYAN}" stroke-width="1.6" stroke-dasharray="3 8"/>'
        + f'<circle r="5" fill="{INK}">'
        + f'<animateMotion dur="3.2s" repeatCount="indefinite" path="{orbit}"/>'
        + "</circle>"
        + paint_text(
            BOLD, "它会再来一次", 44, cx, 318, INK, glow=(MAGENTA, 6, 0.2)
        )[0]
    )


def indicators():
    times = [0, 2.5, 3.05, 5.55, 6.1, 8.6, 9.15, 11.65, 12.2]
    key_times = fmt_times([time / TOTAL for time in times])
    bright = "1"
    dim = "0.42"
    sequences = [
        [bright, bright, dim, dim, dim, dim, dim, dim, bright],
        [dim, dim, bright, bright, dim, dim, dim, dim, dim],
        [dim, dim, dim, dim, bright, bright, dim, dim, dim],
        [dim, dim, dim, dim, dim, dim, bright, bright, dim],
    ]
    width = 28
    gap = 10
    total = 4 * width + 3 * gap
    start = (W - total) / 2
    y = WIN_Y + WIN_H - 24
    parts = []
    for index, values in enumerate(sequences):
        x = start + index * (width + gap)
        parts.append(
            f'<rect x="{x:.2f}" y="{y}" width="{width}" height="4" rx="2" fill="{CYAN}">'
            f'<animate attributeName="opacity" dur="{TOTAL}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{key_times}" values="{";".join(values)}"/>'
            f"</rect>"
        )
    return "".join(parts)


def corner_ticks():
    arm = 18
    inset = 14
    x, y, w, h = WIN_X, WIN_Y, WIN_W, WIN_H
    corners = (
        (x + inset, y + inset, 1, 1),
        (x + w - inset, y + inset, -1, 1),
        (x + inset, y + h - inset, 1, -1),
        (x + w - inset, y + h - inset, -1, -1),
    )
    parts = []
    for px, py, dx, dy in corners:
        parts.append(
            f'<path d="M {px + dx * arm:.1f},{py} H {px} V {py + dy * arm:.1f}" '
            f'fill="none" stroke="{CYAN}" stroke-width="1.5"/>'
        )
    return "".join(parts)


def build(animated=True, frame=0, shift=None):
    times, values = slide_keyframes()
    if animated:
        motion = (
            f'<animateTransform attributeName="transform" type="translate" '
            f'dur="{TOTAL}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{fmt_times(times)}" values="{fmt_values(values)}"/>'
        )
    else:
        motion = ""
        if shift is None:
            shift = -frame * WIN_W
    frames = [
        frame_hello(),
        frame_light(),
        frame_split(),
        frame_again(),
        frame_hello(),
    ]
    slide = []
    for index, inner in enumerate(frames):
        slide.append(
            f'<g transform="translate({WIN_X + index * WIN_W},{WIN_Y})">{inner}</g>'
        )
    if animated:
        strip = f'<g>{motion}{"".join(slide)}</g>'
    else:
        strip = f'<g transform="translate({shift},0)">{"".join(slide)}</g>'

    name_y = WIN_Y + WIN_H + 96
    tag_y = name_y + 52
    rule_y = tag_y + 34
    meta1_y = rule_y + 52
    meta2_y = meta1_y + 42
    sweep_y = meta2_y + 52
    height = sweep_y + 36

    label_size = 18
    value_size = 26
    label_gap = 22
    interests = "篮球、跑步、游泳、听歌...."
    status = "学习ing"
    label_w = max(
        measure(BOLD, "兴趣", label_size, 2),
        measure(BOLD, "正在", label_size, 2),
    )
    value_w = max(
        measure(REGULAR, interests, value_size),
        measure(REGULAR, status, value_size),
    )
    block_w = label_w + label_gap + value_w
    block_x = (W - block_w) / 2

    identity = (
        paint_text(BOLD, "lisuhang11", 58, W / 2, name_y, INK, tracking=1.5)[0]
        + paint_text(REGULAR, "一个很有idea的开发者", 26, W / 2, tag_y, MAGENTA)[0]
        + f'<line x1="{W / 2 - 36}" y1="{rule_y}" x2="{W / 2 + 36}" y2="{rule_y}" stroke="{CYAN}" stroke-width="1.25" opacity="0.85"/>'
        + paint_text(BOLD, "兴趣", label_size, block_x, meta1_y - 2, CYAN, tracking=2, anchor="start")[0]
        + paint_text(REGULAR, interests, value_size, block_x + label_w + label_gap, meta1_y, INK, anchor="start")[0]
        + paint_text(BOLD, "正在", label_size, block_x, meta2_y - 2, MAGENTA, tracking=2, anchor="start")[0]
        + paint_text(REGULAR, status, value_size, block_x + label_w + label_gap, meta2_y, INK, anchor="start")[0]
    )

    sweep = (
        f'<line x1="72" y1="{sweep_y}" x2="{W - 72}" y2="{sweep_y}" stroke="{CYAN}" stroke-width="1" opacity="0.28"/>'
        f'<g>'
        f'<rect y="{sweep_y - 2.5}" width="210" height="5" rx="2.5" fill="url(#sweep)">'
        f'<animate attributeName="x" from="-210" to="{W}" dur="3.2s" repeatCount="indefinite"/>'
        f"</rect>"
        f'<circle cy="{sweep_y}" r="3.2" fill="{INK}">'
        f'<animate attributeName="cx" from="0" to="{W + 210}" dur="3.2s" repeatCount="indefinite"/>'
        f"</circle>"
        f"</g>"
    )

    title = "lisuhang11，一个很有idea的开发者"
    desc = (
        "滑动画面依次是：你好；光从左往右；青，然后品红；它会再来一次。"
        "兴趣：篮球、跑步、游泳、听歌.... 正在：学习ing。"
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img">
  <title>{title}</title>
  <desc>{desc}</desc>
  <defs>
    <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="{CYAN}" opacity="0.33"/>
    </pattern>
    <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
      <stop offset="0.18" stop-color="{CYAN}"/>
      <stop offset="0.55" stop-color="#f7feff"/>
      <stop offset="0.82" stop-color="{MAGENTA}"/>
      <stop offset="1" stop-color="{MAGENTA}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="beamSoft" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
      <stop offset="0.5" stop-color="{CYAN}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{MAGENTA}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{MAGENTA}" stop-opacity="0"/>
      <stop offset="0.45" stop-color="{MAGENTA}" stop-opacity="0.15"/>
      <stop offset="0.72" stop-color="{MAGENTA}"/>
      <stop offset="0.9" stop-color="{CYAN}"/>
      <stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="windowClip">
      <rect x="{WIN_X}" y="{WIN_Y}" width="{WIN_W}" height="{WIN_H}" rx="18"/>
    </clipPath>
    <radialGradient id="vignette" cx="0.5" cy="0.5" r="0.72">
      <stop offset="0.62" stop-color="{BG}" stop-opacity="0"/>
      <stop offset="1" stop-color="{BG}" stop-opacity="0.45"/>
    </radialGradient>
  </defs>
  <rect x="1.5" y="1.5" width="{W - 3}" height="{height - 3}" rx="28" fill="{BG}"/>
  <g clip-path="url(#windowClip)">
    {strip}
    <rect x="{WIN_X}" y="{WIN_Y}" width="{WIN_W}" height="{WIN_H}" fill="url(#vignette)"/>
  </g>
  <rect x="{WIN_X + 0.5}" y="{WIN_Y + 0.5}" width="{WIN_W - 1}" height="{WIN_H - 1}" rx="18" fill="none" stroke="{CYAN}" stroke-width="1.5"/>
  {corner_ticks()}
  {indicators()}
  {identity}
  {sweep}
  <rect x="1.5" y="1.5" width="{W - 3}" height="{height - 3}" rx="28" fill="none" stroke="{CYAN}" stroke-width="1.5"/>
</svg>
'''


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(animated=True), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

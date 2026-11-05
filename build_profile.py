"""Build the pixel-glitch profile card. Text is rasterized into blocks."""

from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = __import__("pathlib").Path(__file__).resolve().parent
OUT = ROOT_DIR / "assets" / "profile.svg"
FONT_PATH = r"C:\Windows\Fonts\msyhbd.ttc"

BG = "#07070b"
CYAN = "#22d3ee"
MAGENTA = "#e879f9"
INK = "#f4feff"

W = 1120
WIN_X, WIN_Y, WIN_W, WIN_H = 28, 28, 1064, 392
HOLD = 2.5
SLIDE = 0.55
PERIOD = HOLD + SLIDE
FRAME_COUNT = 4
TOTAL = PERIOD * FRAME_COUNT

FONT = None


def font(size):
    global FONT
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
    pixels = []
    for y in range(height):
        for x in range(width):
            if small.getpixel((x, y)) > 80:
                pixels.append((x, y))
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


def emit_pixels(pixels, ox, oy, cell, fill, gap=1, opacity=None, dx=0):
    gutter = gap
    body = cell - gutter
    extra = f' opacity="{opacity}"' if opacity is not None else ""
    parts = []
    for x, y, w in runs(pixels):
        parts.append(
            f'<rect x="{ox + (x + dx) * cell}" y="{oy + y * cell}" '
            f'width="{w * cell - gutter}" height="{body}" fill="{fill}"{extra}/>'
        )
    return "".join(parts)


def glitch_layers(pixels, shift):
    cyan, magenta = [], []
    for x, y in pixels:
        if y % 6 == 0:
            cyan.append((x + shift, y))
        elif y % 6 == 3:
            magenta.append((x - shift, y))
    return pixels, cyan, magenta


def paint(text, font_px, step, cell, x, y, fill, anchor="middle", glitch=0):
    pixels, tw, th = bitmap(text, font_px, step)
    width = tw * cell
    height = th * cell
    if anchor == "middle":
        origin = x - width / 2
    elif anchor == "start":
        origin = x
    else:
        origin = x - width
    if glitch:
        _main, cyan_px, magenta_px = glitch_layers(pixels, glitch)
        svg = (
            emit_pixels(cyan_px, origin, y, cell, CYAN, opacity=0.85)
            + emit_pixels(magenta_px, origin, y, cell, MAGENTA, opacity=0.85)
            + emit_pixels(pixels, origin, y, cell, fill)
        )
    else:
        svg = emit_pixels(pixels, origin, y, cell, fill)
    return svg, width, height


def rect(x, y, w, h, fill, opacity=None):
    extra = f' opacity="{opacity}"' if opacity is not None else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>'


def mosaic(width, height, salt):
    cell = 14
    parts = []
    cols = width // cell
    rows = height // cell
    for iy in range(rows):
        for ix in range(cols):
            n = (ix * 13 + iy * 17 + salt * 29) % 23
            if n > 3:
                continue
            ox = 4 if n == 0 else 0
            oy = -3 if n == 1 else 0
            color = CYAN if (ix + salt) % 2 == 0 else MAGENTA
            size = 8 if n != 2 else 5
            parts.append(rect(ix * cell + ox, iy * cell + oy, size, size, color, 0.28 if n < 2 else 0.55))
    return "".join(parts)


def frame_shell(salt):
    return rect(0, 0, WIN_W, WIN_H, BG) + mosaic(WIN_W, WIN_H, salt)


def tears(y_positions):
    parts = []
    for index, y in enumerate(y_positions):
        shift = 18 if index % 2 == 0 else -26
        color = CYAN if index % 2 == 0 else MAGENTA
        parts.append(rect(36 + shift, y, WIN_W - 160, 3, color, 0.8))
        parts.append(rect(80, y + 5, 220, 3, INK, 0.35))
    return "".join(parts)


def frame_hello():
    svg, _width, _height = paint("你好", 86, 2, 5, WIN_W / 2, 108, INK, glitch=2)
    return frame_shell(1) + tears((32, WIN_H - 36)) + svg


def frame_light():
    title, _w, _h = paint("光从左往右", 44, 2, 4, WIN_W / 2, 86, INK, glitch=1)
    blocks = []
    beam_y = 196
    span = WIN_W - 96
    count = 36
    block_w = span // count
    for index in range(count):
        color = CYAN if index < count * 0.45 else (INK if index < count * 0.62 else MAGENTA)
        blocks.append(rect(48 + index * block_w, beam_y, block_w - 3, 10, color))
    mover = (
        '<rect y="188" width="16" height="16" fill="#f7feff">'
        '<animate attributeName="x" values="48;1000" dur="2.4s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.88;1" dur="2.4s" repeatCount="indefinite"/>'
        "</rect>"
    )
    return frame_shell(2) + tears((28,)) + "".join(blocks) + mover + title


def frame_split():
    phrase = [("青", CYAN), ("，然后", INK), ("品红", MAGENTA)]
    rendered = []
    total = 0
    for text, color in phrase:
        svg, width, height = paint(text, 48, 2, 4, 0, 0, color, anchor="start", glitch=1)
        rendered.append((svg, width, height))
        total += width
    total += 20
    cursor = (WIN_W - total) / 2
    top = 168
    placed = []
    for svg, width, _height in rendered:
        placed.append(f'<g transform="translate({cursor},{top})">{svg}</g>')
        cursor += width + 10
    jagged = []
    for index, y in enumerate(range(36, WIN_H - 36, 10)):
        jitter = ((index * 5) % 7) - 3
        jagged.append(rect(WIN_W / 2 - 2 + jitter * 6, y, 4, 8, INK))
    left = rect(0, 0, WIN_W / 2, WIN_H, CYAN, 0.08)
    right = rect(WIN_W / 2, 0, WIN_W / 2, WIN_H, MAGENTA, 0.1)
    return frame_shell(3) + left + right + "".join(jagged) + "".join(placed)


def circle_points(cx, cy, radius):
    points = []
    x = 0
    y = radius
    decision = 3 - 2 * radius
    while x <= y:
        points.extend(
            (
                (cx + x, cy + y),
                (cx - x, cy + y),
                (cx + x, cy - y),
                (cx - x, cy - y),
                (cx + y, cy + x),
                (cx - y, cy + x),
                (cx + y, cy - x),
                (cx - y, cy - x),
            )
        )
        if decision < 0:
            decision += 4 * x + 6
        else:
            decision += 4 * (x - y) + 10
            y -= 1
        x += 1
    return points


def pixel_circle(cx, cy, radius, fill, skip=2):
    parts = []
    seen = set()
    for index, (x, y) in enumerate(circle_points(cx, cy, radius)):
        key = (int(x), int(y))
        if key in seen or index % skip == 0:
            continue
        seen.add(key)
        parts.append(rect(x, y, 4, 4, fill))
    return "".join(parts)


def frame_again():
    cx, cy, radius = WIN_W / 2, 150, 70
    title, _w, _h = paint("它会再来一次", 42, 2, 4, cx, 268, INK, glitch=1)
    left = cx - radius
    right = cx + radius
    orbit = (
        f"M {right},{cy} "
        f"A {radius},{radius} 0 0 1 {left},{cy} "
        f"A {radius},{radius} 0 0 1 {right},{cy}"
    )
    mover = (
        f'<rect width="10" height="10" fill="{INK}">'
        f'<animateMotion dur="3.2s" repeatCount="indefinite" path="{orbit}"/>'
        "</rect>"
    )
    return (
        frame_shell(4)
        + pixel_circle(cx - 2, cy - 2, radius + 18, MAGENTA, skip=3)
        + pixel_circle(cx - 2, cy - 2, radius, CYAN, skip=2)
        + mover
        + title
    )


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
    return times, values


def fmt_times(times):
    rendered = []
    for time in times:
        text = f"{time:.5f}".rstrip("0").rstrip(".")
        rendered.append(text or "0")
    return ";".join(rendered)


def fmt_values(values):
    return ";".join(f"{value:.2f},0" for value in values)


def broken_frame(x, y, w, h, color):
    t = 3
    parts = [
        rect(x, y, w * 0.36, t, color),
        rect(x + w * 0.40, y - 4, w * 0.18, t, MAGENTA),
        rect(x + w * 0.62, y, w * 0.38, t, color),
        rect(x, y + h - t, w * 0.52, t, color),
        rect(x + w * 0.58, y + h - t + 4, w * 0.22, t, CYAN),
        rect(x + w * 0.84, y + h - t, w * 0.16, t, color),
        rect(x, y, t, h * 0.42, color),
        rect(x - 4, y + h * 0.48, t, h * 0.16, MAGENTA),
        rect(x, y + h * 0.68, t, h * 0.32, color),
        rect(x + w - t, y, t, h * 0.3, color),
        rect(x + w - t + 4, y + h * 0.34, t, h * 0.2, CYAN),
        rect(x + w - t, y + h * 0.58, t, h * 0.42, color),
    ]
    return "".join(parts)


def corner_blocks():
    arm = 22
    thick = 4
    inset = 12
    x, y, w, h = WIN_X, WIN_Y, WIN_W, WIN_H
    corners = (
        (x + inset, y + inset, 1, 1, CYAN),
        (x + w - inset, y + inset, -1, 1, INK),
        (x + inset, y + h - inset, 1, -1, MAGENTA),
        (x + w - inset, y + h - inset, -1, -1, CYAN),
    )
    parts = []
    for px, py, dx, dy, color in corners:
        parts.append(rect(px if dx > 0 else px - arm, py if dy > 0 else py - thick, arm, thick, color))
        parts.append(rect(px if dx > 0 else px - thick, py if dy > 0 else py - arm, thick, arm, color))
    return "".join(parts)


def indicators():
    times = [0, 2.5, 3.05, 5.55, 6.1, 8.6, 9.15, 11.65, 12.2]
    key_times = fmt_times([time / TOTAL for time in times])
    sequences = [
        ["1", "1", "0.28", "0.28", "0.28", "0.28", "0.28", "0.28", "1"],
        ["0.28", "0.28", "1", "1", "0.28", "0.28", "0.28", "0.28", "0.28"],
        ["0.28", "0.28", "0.28", "0.28", "1", "1", "0.28", "0.28", "0.28"],
        ["0.28", "0.28", "0.28", "0.28", "0.28", "0.28", "1", "1", "0.28"],
    ]
    width = 28
    gap = 10
    total = 4 * width + 3 * gap
    start = (W - total) / 2
    y = WIN_Y + WIN_H - 28
    parts = []
    for index, values in enumerate(sequences):
        px = start + index * (width + gap)
        parts.append(
            f'<rect x="{px}" y="{y}" width="{width}" height="8" fill="{CYAN}">'
            f'<animate attributeName="opacity" dur="{TOTAL}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{key_times}" values="{";".join(values)}"/>'
            "</rect>"
        )
    return "".join(parts)


def debris(x, y, color):
    spec = (
        (0, 0, 10, 10, 0.9),
        (14, 2, 6, 6, 0.45),
        (8, 14, 16, 6, 0.7),
        (28, 0, 6, 18, 0.35),
        (4, 24, 10, 10, 0.55),
    )
    return "".join(rect(x + dx, y + dy, w, h, color, opacity) for dx, dy, w, h, opacity in spec)


def build(animated=True, frame=0, shift=None):
    times, values = slide_keyframes()
    frames = [frame_hello(), frame_light(), frame_split(), frame_again(), frame_hello()]
    slide = []
    for index, inner in enumerate(frames):
        slide.append(f'<g transform="translate({WIN_X + index * WIN_W},{WIN_Y})">{inner}</g>')
    if animated:
        motion = (
            f'<animateTransform attributeName="transform" type="translate" '
            f'dur="{TOTAL}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{fmt_times(times)}" values="{fmt_values(values)}"/>'
        )
        strip = f"<g>{motion}{''.join(slide)}</g>"
    else:
        if shift is None:
            shift = -frame * WIN_W
        strip = f'<g transform="translate({shift},0)">{"".join(slide)}</g>'

    name_svg, _name_w, name_h = paint("lisuhang11", 52, 1, 2, W / 2, 0, INK, glitch=1)
    tag_svg, _tag_w, tag_h = paint("一个很有idea的开发者", 32, 1, 2, W / 2, 0, MAGENTA, glitch=1)
    meta_font, meta_step, meta_cell = 34, 2, 3
    interests = "篮球、跑步、游泳、听歌...."
    status = "学习ing"
    label_1, label_w, meta_h = paint("兴趣", meta_font, meta_step, meta_cell, 0, 0, CYAN, anchor="start")
    value_1, value_1_w, _h = paint(interests, meta_font, meta_step, meta_cell, 0, 0, INK, anchor="start")
    label_2, label_2_w, _h = paint("正在", meta_font, meta_step, meta_cell, 0, 0, MAGENTA, anchor="start")
    value_2, value_2_w, _h = paint(status, meta_font, meta_step, meta_cell, 0, 0, INK, anchor="start")
    label_w = max(label_w, label_2_w)
    gap = 18
    block_w = label_w + gap + max(value_1_w, value_2_w)
    block_x = (W - block_w) / 2

    name_y = WIN_Y + WIN_H + 36
    tag_y = name_y + name_h + 18
    rule_y = tag_y + tag_h + 18
    meta_1_y = rule_y + 22
    meta_2_y = meta_1_y + meta_h + 14
    sweep_y = meta_2_y + meta_h + 30
    height = int(sweep_y + 34)

    identity = (
        f'<g transform="translate(0,{name_y})">{name_svg}</g>'
        f'<g transform="translate(0,{tag_y})">{tag_svg}</g>'
        + rect(W / 2 - 78, rule_y, 28, 4, CYAN)
        + rect(W / 2 - 42, rule_y - 3, 18, 4, MAGENTA)
        + rect(W / 2 - 16, rule_y, 10, 4, INK)
        + rect(W / 2 + 4, rule_y + 3, 36, 4, CYAN)
        + rect(W / 2 + 48, rule_y, 22, 4, MAGENTA)
        + f'<g transform="translate({block_x},{meta_1_y})">{label_1}</g>'
        + f'<g transform="translate({block_x + label_w + gap},{meta_1_y})">{value_1}</g>'
        + f'<g transform="translate({block_x},{meta_2_y})">{label_2}</g>'
        + f'<g transform="translate({block_x + label_w + gap},{meta_2_y})">{value_2}</g>'
    )

    sweep_blocks = []
    cursor = 0
    for width, color in ((28, MAGENTA), (18, MAGENTA), (14, INK), (22, CYAN), (16, CYAN), (10, INK)):
        sweep_blocks.append(rect(cursor, sweep_y, width, 8, color))
        cursor += width + 4
    sweep = (
        rect(36, sweep_y + 2, W - 72, 3, CYAN, 0.28)
        + "<g>"
        + f'<animateTransform attributeName="transform" type="translate" from="-220,0" to="{W},0" dur="3.2s" repeatCount="indefinite"/>'
        + "".join(sweep_blocks)
        + "</g>"
    )

    title = "lisuhang11，一个很有idea的开发者"
    desc = (
        "滑动画面依次是：你好；光从左往右；青，然后品红；它会再来一次。"
        "兴趣：篮球、跑步、游泳、听歌.... 正在：学习ing。"
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" shape-rendering="crispEdges" role="img">
  <title>{title}</title>
  <desc>{desc}</desc>
  <defs>
    <clipPath id="windowClip">
      <rect x="{WIN_X}" y="{WIN_Y}" width="{WIN_W}" height="{WIN_H}"/>
    </clipPath>
  </defs>
  {rect(0, 0, W, height, BG)}
  <g clip-path="url(#windowClip)">
    {strip}
    {debris(WIN_X + 18, WIN_Y + 16, CYAN)}
    {debris(WIN_X + WIN_W - 70, WIN_Y + WIN_H - 70, MAGENTA)}
  </g>
  {broken_frame(WIN_X, WIN_Y, WIN_W, WIN_H, CYAN)}
  {corner_blocks()}
  {indicators()}
  {identity}
  {sweep}
  {broken_frame(8, 8, W - 16, height - 16, CYAN)}
</svg>
'''


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(animated=True), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

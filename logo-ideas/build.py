"""Render the five candidate FiloFax marks as standalone SVGs + a contact sheet.

One geometry per mark, drawn on a 32x32 grid and reused at every preview
size: an icon that only reads at one size isn't a logo, so the sheet shows
128 / 32 / 16px and a filled app tile for each.
"""
import pathlib

ACCENT = "#b8604a"
INK = "#2a2724"
BG = "#f7f5f2"
DARK_BG = "#211e1b"
DARK_INK = "#efe9e1"

# (name, tagline, why, <g> contents for the stroke version, for the solid version)
MARKS = [
    (
        "spine", "Spine",
        "A day as a vertical thread with two entries hung off it.",
        "Looks like nothing else in this category. Simplified from three dots to "
        "two and thickened, because three was mush at 16px.",
        '<path d="M8.5 4.5v23"/><path d="M8.5 12h8"/><path d="M8.5 21h8"/>'
        '<circle cx="21.5" cy="12" r="3.4"/><circle cx="21.5" cy="21" r="3.4"/>',
        '<path d="M6.8 4h3.4v24H6.8z"/><path d="M10.2 10.1h6.4v3.4h-6.4zM10.2 19.1h6.4v3.4h-6.4z"/>'
        '<circle cx="22" cy="11.8" r="4.3"/><circle cx="22" cy="21.3" r="4.3"/>',
    ),
    (
        "clasp", "Clasp",
        "The strap that closes a notebook, as one unbroken stroke.",
        "The most logo-like of the set and genuinely unusual. Opened the hook so "
        "it stops reading as a paperclip.",
        '<path d="M7.5 28V11.5A8.5 8.5 0 0124.5 11.5v8.8a4.6 4.6 0 01-9.2 0v-8.3"/>',
        '<path d="M5 28.5V11.5a11 11 0 0122 0v8.8a7.1 7.1 0 01-14.2 0v-8.3h5v8.3a2.1 2.1 0 004.2 0v-8.8a6 6 0 00-12 0v17z"/>',
    ),
    (
        "fold", "Folded day",
        "One square creased down the middle, the far half turning away.",
        "Reads as a page being turned rather than a page sitting still, which is "
        "closer to what a daybook is for. Two tones, no outline needed.",
        '<path d="M16 5.5H7.2A1.7 1.7 0 005.5 7.2v17.6A1.7 1.7 0 007.2 26.5H16"/>'
        '<path d="M16 5.5l9.4 3.1a1.7 1.7 0 011.1 1.6v12.6a1.7 1.7 0 01-1.1 1.6L16 26.5z"/>'
        '<path d="M16 5.5v21"/>',
        '<path d="M16 4H6.6A2.6 2.6 0 004 6.6v18.8A2.6 2.6 0 006.6 28H16z" opacity=".45"/>'
        '<path d="M16 4l10.2 3.4A2.6 2.6 0 0128 9.9v12.2a2.6 2.6 0 01-1.8 2.5L16 28z"/>',
    ),
    (
        "ribbon", "Ribbon (for comparison)",
        "A notebook's bookmark. Included only as the baseline.",
        "Flawless at every size -- and it is the universal bookmark glyph, so it "
        "is recognisable without being distinctive. Keep it as the fallback.",
        '<path d="M10 5.5h12a1.6 1.6 0 011.6 1.6v20.4l-7.6-5.7-7.6 5.7V7.1A1.6 1.6 0 0110 5.5z"/>',
        '<path d="M10 4h12a2.5 2.5 0 012.5 2.5V29l-8.5-6.4L7.5 29V6.5A2.5 2.5 0 0110 4z"/>',
    ),
]


def svg(contents, size, colour, stroke=True, weight=2.0):
    style = (f'fill="none" stroke="{colour}" stroke-width="{weight}" '
             'stroke-linecap="round" stroke-linejoin="round"') if stroke else f'fill="{colour}"'
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
            f'xmlns="http://www.w3.org/2000/svg"><g {style}>{contents}</g></svg>')


def main():
    here = pathlib.Path(__file__).parent
    cards = []
    for slug, name, idea, why, stroke_body, solid_body in MARKS:
        # Standalone files, the two versions anyone actually needs.
        (here / f"{slug}-line.svg").write_text(svg(stroke_body, 64, INK, True))
        (here / f"{slug}-solid.svg").write_text(svg(solid_body, 64, ACCENT, False))

        row = "".join([
            f'<div class="size"><div class="lbl">128</div>{svg(stroke_body, 128, INK, True)}</div>',
            f'<div class="size"><div class="lbl">32</div>{svg(stroke_body, 32, INK, True)}</div>',
            f'<div class="size"><div class="lbl">16</div>{svg(stroke_body, 16, INK, True, 2.4)}</div>',
            f'<div class="size"><div class="lbl">solid</div>{svg(solid_body, 56, ACCENT, False)}</div>',
            f'<div class="size"><div class="lbl">tile</div>'
            f'<div class="tile">{svg(solid_body, 40, "#fff", False)}</div></div>',
            f'<div class="size dark"><div class="lbl">dark</div>{svg(stroke_body, 40, DARK_INK, True)}</div>',
        ])
        cards.append(f"""
  <section class="card">
    <div class="meta">
      <h2>{name}</h2>
      <p class="idea">{idea}</p>
      <p class="why">{why}</p>
      <p class="files"><code>{slug}-line.svg</code> · <code>{slug}-solid.svg</code></p>
    </div>
    <div class="sizes">{row}</div>
  </section>""")

    html = f"""<!DOCTYPE html>
<meta charset="utf-8"><title>FiloFax — logo candidates</title>
<style>
  body {{ margin: 0; padding: 36px 40px; background: {BG}; color: {INK};
         font: 14px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; }}
  h1 {{ font-family: Georgia, serif; font-size: 24px; margin: 0 0 4px; }}
  .sub {{ color: #6b655e; margin: 0 0 28px; max-width: 70ch; }}
  .card {{ display: flex; gap: 28px; align-items: center; background: #fff;
           border: 1px solid {ACCENT}22; border-radius: 12px;
           padding: 20px 24px; margin-bottom: 16px; }}
  .meta {{ flex: 0 0 300px; }}
  .meta h2 {{ font-family: Georgia, serif; font-size: 17px; margin: 0 0 6px; }}
  .idea {{ margin: 0 0 6px; }}
  .why {{ margin: 0 0 8px; color: #6b655e; font-size: 13px; }}
  .files {{ margin: 0; font-size: 11px; color: #9a9288; }}
  code {{ font-family: ui-monospace, Menlo, monospace; }}
  .sizes {{ display: flex; gap: 22px; align-items: flex-end; flex-wrap: wrap; }}
  .size {{ display: flex; flex-direction: column; align-items: center; gap: 7px; }}
  .lbl {{ font-size: 10px; color: #9a9288; letter-spacing: .04em; }}
  .tile {{ width: 56px; height: 56px; border-radius: 13px; background: {ACCENT};
           display: grid; place-items: center; }}
  .size.dark {{ background: {DARK_BG}; padding: 10px 14px 12px; border-radius: 10px; }}
  .size.dark .lbl {{ color: #8a827a; }}
</style>
<h1>FiloFax — logo candidates, round 2</h1>
<p class="sub">One shape each, same geometry at every size. The 16px column is the
real test: if it survives there it works as a favicon and a taskbar icon.
Deliberately avoids ring-binder holes, punched pages and a stylised “F”, all of
which sit closest to the existing Filofax brand in the same product category.</p>
<p class="sub"><strong>Withdrawn:</strong> a “tab” came out as a plain file
folder; an “open leaf” came out as the standard open-book glyph; two offset
leaves turned out to be the universal copy/duplicate icon. All three were
recognisable but not distinctive, which is the opposite of the brief.</p>
{''.join(cards)}
"""
    (here / "logo-candidates.html").write_text(html)
    print("wrote logo-candidates.html and", len(MARKS) * 2, "svg files")


main()

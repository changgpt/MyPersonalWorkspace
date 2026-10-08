"""Round 3: spine takes, ribbon takes, wordmark lockups, font specimens."""
import pathlib
from faces import FACES

ACCENT, INK, BG, DARK_BG, DARK_INK = "#b8604a", "#2a2724", "#f7f5f2", "#211e1b", "#efe9e1"
NAME = "Filofacts"

MARKS = [
    ("spine-side", "Spine, edge-on",
     "A bound spine seen from the side: the board, and the sewing bands across it.",
     "The most literal 'notebook' of the three and still an unusual silhouette — "
     "tall and narrow, which no other app icon in this space is.",
     '<path d="M11.5 4.5h9a1.8 1.8 0 011.8 1.8v19.4a1.8 1.8 0 01-1.8 1.8h-9a1.8 1.8 0 01-1.8-1.8V6.3a1.8 1.8 0 011.8-1.8z"/>'
     '<path d="M9.7 11h12.6M9.7 21h12.6"/>',
     '<path d="M11 4h10a2.6 2.6 0 012.6 2.6v18.8A2.6 2.6 0 0121 28H11a2.6 2.6 0 01-2.6-2.6V6.6A2.6 2.6 0 0111 4z"/>'
     '<path d="M8.4 10.6h15.2v2.4H8.4zM8.4 20h15.2v2.4H8.4z" fill="' + BG + '"/>'),
    ("spine-front", "Spine, head-on",
     "A closed cover with the spine strip running down its left edge.",
     "Reads as 'a notebook' fastest of the set. Closest to a generic book icon, "
     "so the spine strip is doing all the differentiating.",
     '<path d="M7 7.2A2.7 2.7 0 019.7 4.5h13.1A2.7 2.7 0 0125.5 7.2v17.6a2.7 2.7 0 01-2.7 2.7H9.7A2.7 2.7 0 017 24.8V7.2z"/>'
     '<path d="M12.6 4.5v23"/>',
     '<path d="M6 7A3 3 0 019 4h14a3 3 0 013 3v18a3 3 0 01-3 3H9a3 3 0 01-3-3V7z"/>'
     '<path d="M12.2 4h2.4v24h-2.4z" fill="' + BG + '"/>'),
    ("spine-thread", "Spine, abstracted",
     "The spine as a bare rule with two entries hung off it.",
     "The most ownable and the least literal. Busiest at 16px of the three.",
     '<path d="M8.5 4.5v23"/><path d="M8.5 12h8"/><path d="M8.5 21h8"/>'
     '<circle cx="21.5" cy="12" r="3.4"/><circle cx="21.5" cy="21" r="3.4"/>',
     '<path d="M6.8 4h3.4v24H6.8z"/><path d="M10.2 10.1h6.4v3.4h-6.4zM10.2 19.1h6.4v3.4h-6.4z"/>'
     '<circle cx="22" cy="11.8" r="4.3"/><circle cx="22" cy="21.3" r="4.3"/>'),
    ("ribbon", "Ribbon, plain",
     "The bookmark, as-is.",
     "Reads at any size — but it is the standard save/bookmark glyph in more or "
     "less every interface, and Pocket's mark is a close cousin. Legible, not ownable.",
     '<path d="M10 5.5h12a1.6 1.6 0 011.6 1.6v20.4l-7.6-5.7-7.6 5.7V7.1A1.6 1.6 0 0110 5.5z"/>',
     '<path d="M10 4h12a2.5 2.5 0 012.5 2.5V29l-8.5-6.4L7.5 29V6.5A2.5 2.5 0 0110 4z"/>'),
    ("ribbon-f", "Ribbon + F",
     "The bookmark with an F knocked out of it.",
     "You asked for it, so here it is — but read the note: Filofax's own "
     "registered mark is literally an F. This is the riskiest option on the sheet.",
     '<path d="M10 5.5h12a1.6 1.6 0 011.6 1.6v20.4l-7.6-5.7-7.6 5.7V7.1A1.6 1.6 0 0110 5.5z"/>'
     '<path d="M13.2 18.5V9.8h6.4M13.2 14h5"/>',
     '<path d="M10 4h12a2.5 2.5 0 012.5 2.5V29l-8.5-6.4L7.5 29V6.5A2.5 2.5 0 0110 4z"/>'
     '<path d="M12.4 19.4V9h7.8v2.5h-5.3v2.3h4.3v2.5h-4.3v3.1z" fill="' + BG + '"/>'),
]


def svg(body, size, colour, stroke=True, weight=2.0):
    style = (f'fill="none" stroke="{colour}" stroke-width="{weight}" '
             'stroke-linecap="round" stroke-linejoin="round"') if stroke else f'fill="{colour}"'
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 32 32" '
            f'xmlns="http://www.w3.org/2000/svg"><g {style}>{body}</g></svg>')


def main():
    here = pathlib.Path(__file__).parent
    cards = []
    for slug, name, idea, why, line_body, solid_body in MARKS:
        (here / f"{slug}-line.svg").write_text(svg(line_body, 64, INK, True))
        (here / f"{slug}-solid.svg").write_text(svg(solid_body, 64, ACCENT, False))
        sizes = "".join([
            f'<div class="size"><div class="lbl">112</div>{svg(line_body, 112, INK, True)}</div>',
            f'<div class="size"><div class="lbl">32</div>{svg(line_body, 32, INK, True)}</div>',
            f'<div class="size"><div class="lbl">16</div>{svg(line_body, 16, INK, True, 2.4)}</div>',
            f'<div class="size"><div class="lbl">solid</div>{svg(solid_body, 52, ACCENT, False)}</div>',
            f'<div class="size"><div class="lbl">tile</div><div class="tile">{svg(solid_body, 38, "#fff", False)}</div></div>',
            f'<div class="size dark"><div class="lbl">dark</div>{svg(line_body, 38, DARK_INK, True)}</div>',
        ])
        flag = ' <span class="warn">trademark risk</span>' if slug == "ribbon-f" else ""
        cards.append(f'<section class="card"><div class="meta"><h2>{name}{flag}</h2>'
                     f'<p class="idea">{idea}</p><p class="why">{why}</p>'
                     f'<p class="files"><code>{slug}-line.svg</code></p></div>'
                     f'<div class="sizes">{sizes}</div></section>')

    # --- lockups: mark + wordmark, in the fonts worth considering for it ---
    ribbon = dict(MARKS[3:4] and {m[0]: m for m in MARKS})["ribbon"]
    lock_fonts = ["Fraunces", "Instrument Serif", "Space Grotesk", "Plus Jakarta Sans"]
    lockups = "".join(
        f'<div class="lock"><div class="lock-row">{svg(ribbon[4], 34, ACCENT, True, 2.2)}'
        f'<span style="font-family:\'{f}\';font-weight:600">{NAME}</span></div>'
        f'<div class="lbl">{f}</div></div>' for f in lock_fonts)

    # --- font specimens ---
    seen, specimens = set(), []
    for family, weight, _ in FACES:
        if family in seen:
            continue
        seen.add(family)
        heavy = max(w for fam, w, _ in FACES if fam == family)
        specimens.append(
            f'<div class="spec"><div class="spec-big" style="font-family:\'{family}\';'
            f'font-weight:{heavy}">{NAME}</div>'
            f'<div class="spec-mid" style="font-family:\'{family}\';font-weight:400">'
            f'{NAME} · FILOFACTS · Today, 9 Oct</div>'
            f'<div class="lbl">{family}</div></div>')

    faces_css = "".join(
        f"@font-face{{font-family:'{fam}';font-weight:{w};font-display:block;"
        f"src:url('fonts/{file}') format('woff2');}}" for fam, w, file in FACES)

    html = f"""<!DOCTYPE html>
<meta charset="utf-8"><title>Filofacts — marks, lockups, fonts</title>
<style>
  {faces_css}
  body {{ margin:0; padding:36px 40px; background:{BG}; color:{INK};
          font:14px/1.5 -apple-system,"Segoe UI",system-ui,sans-serif; }}
  h1 {{ font-family:Georgia,serif; font-size:24px; margin:0 0 4px; }}
  h3 {{ font-family:Georgia,serif; font-size:18px; margin:34px 0 12px; }}
  .sub {{ color:#6b655e; margin:0 0 10px; max-width:74ch; }}
  .card {{ display:flex; gap:28px; align-items:center; background:#fff;
           border:1px solid {ACCENT}22; border-radius:12px; padding:18px 22px; margin-bottom:14px; }}
  .meta {{ flex:0 0 310px; }}
  .meta h2 {{ font-family:Georgia,serif; font-size:16px; margin:0 0 6px; }}
  .idea {{ margin:0 0 6px; }} .why {{ margin:0 0 8px; color:#6b655e; font-size:12.5px; }}
  .files {{ margin:0; font-size:11px; color:#9a9288; }}
  code {{ font-family:ui-monospace,Menlo,monospace; }}
  .warn {{ font-family:system-ui; font-size:10px; font-weight:600; color:#fff;
           background:#b03a2e; border-radius:999px; padding:2px 7px; vertical-align:2px; }}
  .sizes {{ display:flex; gap:20px; align-items:flex-end; flex-wrap:wrap; }}
  .size {{ display:flex; flex-direction:column; align-items:center; gap:6px; }}
  .lbl {{ font-size:10px; color:#9a9288; letter-spacing:.04em; }}
  .tile {{ width:52px; height:52px; border-radius:12px; background:{ACCENT};
           display:grid; place-items:center; }}
  .size.dark {{ background:{DARK_BG}; padding:9px 13px 11px; border-radius:10px; }}
  .size.dark .lbl {{ color:#8a827a; }}
  .locks {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }}
  .lock {{ background:#fff; border:1px solid {ACCENT}22; border-radius:12px; padding:18px 22px; }}
  .lock-row {{ display:flex; align-items:center; gap:11px; font-size:27px; color:{INK}; }}
  .lock .lbl {{ margin-top:10px; }}
  .specs {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }}
  .spec {{ background:#fff; border:1px solid {ACCENT}22; border-radius:12px; padding:16px 20px; }}
  .spec-big {{ font-size:38px; line-height:1.1; color:{INK}; }}
  .spec-mid {{ font-size:15px; color:#6b655e; margin-top:6px; }}
  .spec .lbl {{ margin-top:10px; }}
</style>
<h1>Filofacts — marks, lockups and fonts</h1>
<p class="sub">Spine read three ways, the ribbon plain and with an F, then the
mark paired with the wordmark, then the wordmark alone in ten licensable faces.</p>
{''.join(cards)}
<h3>Lockups — mark beside the wordmark</h3>
<div class="locks">{lockups}</div>
<h3>The wordmark on its own</h3>
<p class="sub">All ten are OFL (free for commercial use), downloaded into
<code>fonts/</code> so this page renders the same offline.</p>
<div class="specs">{''.join(specimens)}</div>
"""
    (here / "round3.html").write_text(html)
    print("built round3.html,", len(MARKS), "marks,", len(specimens), "specimens")


main()

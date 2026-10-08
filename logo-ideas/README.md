# FiloFax — logo candidates

Open `logo-candidates.html` in a browser (or look at `logo-candidates.png`).
Each mark is one shape on a 32×32 grid, shown at 128 / 32 / 16px, as a solid
fill, as an app tile, and on the dark theme. The **16px column is the test**:
an icon that only reads large isn't a logo.

`build.py` is the generator — all five geometries live in its `MARKS` list, so
tweaking a curve and re-running regenerates every size and both SVG variants
at once. `<slug>-line.svg` and `<slug>-solid.svg` are the usable assets.

## The name is the real collision

**Filofax is a registered trademark**, in continuous use since 1930, for
exactly this category — personal organisers, diaries, notebooks. The icons
here avoid the three things closest to that brand's own identity:
**ring-binder holes, punched pages, and a stylised "F"**. The shapes are clear
of it; the *name* is not, and no logo fixes that.

**See `NAMING.md`** — including why "Filofacts" is *closer* to the mark rather
than further from it, and three alternatives that keep the wit.

## Rounds

- `logo-candidates.html` — round 2: folded day, spine (abstract), clasp, ribbon.
- `round3.html` — round 3: spine read three ways, ribbon plain and with an F,
  mark+wordmark lockups, and the wordmark in ten licensable faces.
  Fonts are downloaded into `fonts/` so the page renders identically offline.

## Candidates

| Mark | Reads as | Verdict |
|---|---|---|
| **Folded day** | a page mid-turn | Most distinctive *and* legible small. Lead candidate. |
| **Spine** | a day as a thread with entries | Most ownable silhouette; busiest at 16px. |
| **Clasp** | a notebook strap, one stroke | Most "logo", least self-explanatory. |
| **Ribbon** | a bookmark | Flawless at every size, but it's the universal bookmark glyph — recognisable, not distinctive. Baseline only. |

## Withdrawn, and why

Three earlier ideas were cut after rendering them, because they turned out to
be standard UI glyphs rather than brand marks — recognisable but not
distinctive, which is the opposite of the brief:

- **Tab** (divider tab) rendered as a plain file folder.
- **Open leaf** rendered as the standard open-book icon.
- **Shuffled days** (two offset leaves) is the universal copy/duplicate icon.

Noted here so the next pass doesn't rediscover them.

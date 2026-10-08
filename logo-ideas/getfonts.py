"""Download real woff2 files for the wordmark candidates.

Downloaded rather than linked so the specimen sheet renders identically
offline and nothing in the repo depends on a CDN at view time. Latin
subset, two weights each -- enough to judge a short wordmark.
"""
import pathlib, re, subprocess

# All OFL / free for commercial use. Chosen to span the real choices for a
# short wordmark rather than to be a long list.
FAMILIES = [
    "Fraunces:wght@400;600",
    "Instrument+Serif:wght@400",
    "Newsreader:wght@400;600",
    "EB+Garamond:wght@400;600",
    "DM+Serif+Display:wght@400",
    "Inter:wght@400;600",
    "Plus+Jakarta+Sans:wght@400;700",
    "Space+Grotesk:wght@400;700",
    "Outfit:wght@400;600",
    "Bricolage+Grotesque:wght@400;700",
]
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
out = pathlib.Path("fonts")
faces = []

for spec in FAMILIES:
    url = f"https://fonts.googleapis.com/css2?family={spec}&display=swap"
    css = subprocess.run(["curl", "-sS", "-A", UA, url], capture_output=True,
                         text=True, timeout=60).stdout
    # Keep only the latin block (the last @font-face per weight), so we
    # don't pull cyrillic/vietnamese subsets we'll never render.
    blocks = re.findall(r"@font-face \{(.*?)\}", css, re.S)
    family = spec.split(":")[0].replace("+", " ")
    kept = {}
    for block in blocks:
        if "U+0000-00FF" not in block:        # latin subset marker
            continue
        weight = re.search(r"font-weight:\s*(\d+)", block)
        src = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        if not src:
            continue
        kept[weight.group(1) if weight else "400"] = src.group(1)
    for weight, src in kept.items():
        name = f"{family.replace(' ', '')}-{weight}.woff2"
        subprocess.run(["curl", "-sS", "-o", str(out / name), src], timeout=60, check=True)
        faces.append((family, weight, name))
    print(f"{family:24s} weights {sorted(kept) or 'NONE'}")

pathlib.Path("faces.py").write_text("FACES = " + repr(faces) + "\n")

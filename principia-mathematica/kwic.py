# -*- coding: utf-8 -*-
"""
Created on Thu Feb 26 21:10:51 2026

@author: pascaliensis with Claude Sonnet 4.6
"""

"""
KWIC (Keywords in Context) Index Generator
Reads corpus.txt and produces a styled HTML index grouped by keyword,
with a dispersion plot showing where each keyword appears in the corpus.
"""

import re
import html

# ── Configuration ──────────────────────────────────────────────────────────────
CORPUS_FILE = "corpus.txt"
OUTPUT_FILE = "kwic_index.html"
CONTEXT_WINDOW = 300         # characters on each side of the keyword
CASE_SENSITIVE  = True      # set True to match exact case only

target_names = [
"Horrox", "Egyptians", "Romans", "Anaximander", "Pythagoreans", "Pompilius", "Democritus", "Eudoxus", "Calippus", "Crabtrie", "Marius", "Townley", "Romer", "Ricciolus", "Kircher", "Pappus", "Halley", "Royal Society", "Galileo", "Wren", "Wallis", "Huygens", "Huygenian", "Hugenius", "Mariotte", "Euclid", "Hook", "Hooke", "Apollonius", "Archimedes", "Snellius", "Des Cartes", "Grimaldus", "Collins", "Slusius", "Huddens", "Desaguliers", "Sauveur", "Copernicus", "Copernican", "Borelli", "Townly", "Cassini", "Pound", "Kepler", "Keplerian", "Bullialdus", "Ptolemy", "Vendelin", "Street", "Tycho", "Mercator", "Norwood", "Picart", "Richer", "Varin", "des Hayes", "Couplet", "Feuillé", "de la Hire", "Colepress", "Sturmy", "Machin", "Pemberton", "Flamsted", "Hevelius", "Cysatus", "Bayer", "Kirch", "Julius Cæsar", "Ponthæus", "Cellius", "Galletius", "Ango", "Storer", "Montenari", "Zimmerman", "Estancius", "Simeon", "Matthew Paris", "Aristotle", "Auzout", "Petit", "Gottignies", "Bradley", "Hipparchus", "Cornelius Gemma", "God", "Pocock", "John", "Moses", "Aaron", "Pythagoras", "Cicer.", "Thales", "Anaxagoros", "Virgil", "Aratus", "St. Paul", "David", "Solomon", "Job", "Jeremiah", "Pharaoh", "Philolaus", "Aristarchus", "Plato", "Leibnitz",
]
# ──────────────────────────────────────────────────────────────────────────────

# Colour palette for keywords (one per keyword, cycles if more than 8)
COLORS = [
    "#c0392b", "#2471a3", "#1e8449", "#d4ac0d",
    "#7d3c98", "#ca6f1e", "#117a65", "#2e4057",
]


def load_corpus(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def find_occurrences(corpus: str, keyword: str, window: int, case_sensitive: bool):
    """Return list of (left_context, keyword_match, right_context, char_pos) tuples."""
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(keyword), flags)
    occurrences = []
    for m in pattern.finditer(corpus):
        start, end = m.start(), m.end()
        left  = corpus[max(0, start - window): start]
        right = corpus[end: min(len(corpus), end + window)]
        if start - window > 0:
            left = re.sub(r'^\S+', '', left, flags=flags)
        if end + window < len(corpus):
            right = re.sub(r'\S+$', '', right, flags=flags)
        occurrences.append((left, m.group(), right, start))
    return occurrences


def render_passage(left: str, match: str, right: str) -> str:
    """Render a passage as HTML, preserving line breaks, with keyword highlighted."""
    def escape_with_breaks(text: str) -> str:
        return html.escape(text).replace('\n', '<br>\n')

    return escape_with_breaks(left) + \
           f'<mark class="kw-highlight">{html.escape(match)}</mark>' + \
           escape_with_breaks(right)


def build_dispersion_svg(data: dict, keywords: list, corpus_len: int,
                          colors: list) -> str:
    """Build an SVG dispersion plot of keyword positions."""
    n      = len(keywords)
    W      = 760          # inner plot width (px)
    row_h  = 36           # height per keyword row
    pad_l  = 110          # left padding for labels
    pad_r  = 20
    pad_t  = 30
    pad_b  = 30
    dot_r  = 4

    total_w = pad_l + W + pad_r
    total_h = pad_t + n * row_h + pad_b

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" viewBox="0 0 {total_w} {total_h}" '
        f'style="display:block;font-family:\'Source Serif 4\',Georgia,serif;">',

        # background
        f'<rect width="{total_w}" height="{total_h}" fill="#f0ead8" rx="6"/>',

        # title
        f'<text x="{pad_l}" y="18" font-size="11" fill="#7a6a52" '
        f'letter-spacing="1" text-anchor="start">DISPERSION PLOT</text>',

        # axis line at bottom of rows
        f'<line x1="{pad_l}" y1="{pad_t + n * row_h}" '
        f'x2="{pad_l + W}" y2="{pad_t + n * row_h}" '
        f'stroke="#c8b89a" stroke-width="1"/>',

        # 0% and 100% labels
        f'<text x="{pad_l}" y="{pad_t + n * row_h + 14}" '
        f'font-size="9" fill="#aaa" text-anchor="middle">0%</text>',
        f'<text x="{pad_l + W}" y="{pad_t + n * row_h + 14}" '
        f'font-size="9" fill="#aaa" text-anchor="middle">100%</text>',
    ]

    # vertical grid lines at 25 / 50 / 75 %
    for pct in (25, 50, 75):
        gx = pad_l + int(W * pct / 100)
        lines.append(
            f'<line x1="{gx}" y1="{pad_t}" x2="{gx}" '
            f'y2="{pad_t + n * row_h}" stroke="#c8b89a" '
            f'stroke-width="1" stroke-dasharray="3,3"/>'
        )
        lines.append(
            f'<text x="{gx}" y="{pad_t + n * row_h + 14}" '
            f'font-size="9" fill="#aaa" text-anchor="middle">{pct}%</text>'
        )

    for i, kw in enumerate(keywords):
        color = colors[i % len(colors)]
        cy = pad_t + i * row_h + row_h // 2

        # zebra stripe
        if i % 2 == 0:
            lines.append(
                f'<rect x="{pad_l}" y="{pad_t + i * row_h}" '
                f'width="{W}" height="{row_h}" fill="rgba(0,0,0,0.03)"/>'
            )

        # keyword label
        lines.append(
            f'<text x="{pad_l - 8}" y="{cy + 4}" font-size="12" '
            f'fill="{color}" text-anchor="end" font-weight="600">'
            f'{html.escape(kw)}</text>'
        )

        # dots
        for (_, _, _, pos) in data[kw]:
            cx = pad_l + int(W * pos / corpus_len)
            lines.append(
                f'<circle cx="{cx}" cy="{cy}" r="{dot_r}" '
                f'fill="{color}" opacity="0.85">'
                f'<title>{html.escape(kw)} @ {pos}/{corpus_len} '
                f'({100*pos//corpus_len}%)</title>'
                f'</circle>'
            )

    lines.append('</svg>')
    return '\n'.join(lines)


def build_html(corpus: str, keywords: list, window: int, case_sensitive: bool) -> str:
    data = {}
    for kw in keywords:
        data[kw] = find_occurrences(corpus, kw, window, case_sensitive)

    # sort by descending count
    keywords = sorted(keywords, key=lambda kw: len(data[kw]), reverse=True)

    total      = sum(len(v) for v in data.values())
    corpus_len = len(corpus)

    dispersion_svg = build_dispersion_svg(data, keywords, corpus_len, COLORS)

    # ── keyword color map for highlights ──
    kw_color_map = {kw: COLORS[i % len(COLORS)] for i, kw in enumerate(keywords)}

    sections_html = ""
    for i, kw in enumerate(keywords):
        occurrences = data[kw]
        count       = len(occurrences)
        color       = COLORS[i % len(COLORS)]

        entries_html = ""
        if not occurrences:
            entries_html = '<p class="empty"><em>Aucune occurrence trouvée.</em></p>'
        else:
            for j, (left, match, right, _pos) in enumerate(occurrences):
                passage = render_passage(left, match, right)
                entries_html += f"""
        <div class="entry">
            <span class="entry-num">#{j + 1}</span>
            <p class="passage">{passage}</p>
        </div>"""

        sections_html += f"""
    <section class="kw-section" style="--kw-color:{color}">
        <h2 class="kw-heading">
            <span class="kw-name">{html.escape(kw)}</span>
            <span class="kw-count">{count} occurrence{'s' if count != 1 else ''}</span>
        </h2>
        <div class="entries">
{entries_html}
        </div>
    </section>"""

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KWIC Index</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;1,8..60,300&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink:       #1a1410;
    --paper:     #f8f4ec;
    --cream:     #f0ead8;
    --rule:      #c8b89a;
    --accent:    #8b3a0f;
    --highlight: #e8c547;
    --section:   #2c1a0e;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Source Serif 4', Georgia, serif;
    background: var(--paper);
    color: var(--ink);
    font-size: 15px;
    line-height: 1.75;
  }}

  header {{
    background: var(--section);
    color: #f8f4ec;
    padding: 2.5rem 3rem 2rem;
    border-bottom: 4px solid var(--accent);
  }}

  header h1 {{
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: .02em;
    margin-bottom: .4rem;
  }}

  header .subtitle {{ font-size: .9rem; opacity: .7; font-style: italic; }}

  header .stats {{
    margin-top: 1rem;
    font-size: .82rem;
    opacity: .8;
    letter-spacing: .06em;
    text-transform: uppercase;
  }}

  /* ── Dispersion plot ── */
  .dispersion-wrap {{
    max-width: 900px;
    margin: 2rem auto 0;
    padding: 0 2rem;
  }}

  .dispersion-wrap h2 {{
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.1rem;
    color: var(--accent);
    margin-bottom: .8rem;
    border-top: 2px solid var(--rule);
    padding-top: .8rem;
  }}

  /* ── Main content ── */
  main {{
    max-width: 820px;
    margin: 0 auto;
    padding: 2.5rem 2rem 5rem;
  }}

  .kw-section {{
    margin-bottom: 3rem;
    border-top: 3px solid var(--kw-color, var(--accent));
    padding-top: 1.2rem;
  }}

  .kw-heading {{
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--kw-color, var(--accent));
    margin-bottom: 1.2rem;
    display: flex;
    align-items: baseline;
    gap: .8rem;
  }}

  .kw-count {{
    font-family: 'Source Serif 4', serif;
    font-size: .8rem;
    font-weight: 400;
    font-style: italic;
    color: #888;
  }}

  .entry {{
    position: relative;
    margin-bottom: 1.4rem;
    padding: .9rem 1.1rem .9rem 2.8rem;
    background: var(--cream);
    border-left: 3px solid var(--rule);
    border-radius: 0 4px 4px 0;
    transition: border-color .15s;
  }}

  .entry:hover {{ border-left-color: var(--kw-color, var(--accent)); }}

  .entry-num {{
    position: absolute;
    left: .6rem;
    top: .9rem;
    font-size: .72rem;
    color: #aaa;
    font-style: italic;
    user-select: none;
  }}

  .passage {{ font-size: .93rem; line-height: 1.8; color: #3a2e22; }}

  mark.kw-highlight {{
    background: var(--highlight);
    color: var(--section);
    font-weight: 700;
    padding: .05em .3em;
    border-radius: 2px;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
  }}

  .passage::before, .passage::after {{
    content: '…';
    color: #bbb;
    font-style: italic;
  }}

  .empty {{ color: #999; font-style: italic; padding-left: .5rem; }}

  footer {{
    text-align: center;
    padding: 1.2rem;
    font-size: .78rem;
    color: #999;
    border-top: 1px solid var(--rule);
    background: var(--cream);
  }}
</style>
</head>
<body>

<header>
  <h1>KWIC Index</h1>
  <p class="subtitle">Keywords in Context — fenêtre ±{window} caractères</p>
  <p class="stats">{total} occurrence{'s' if total != 1 else ''} &nbsp;·&nbsp; {len(keywords)} mot{'s' if len(keywords)>1 else ''}-clé{'s' if len(keywords)>1 else ''}</p>
</header>

<div class="dispersion-wrap">
  <h2>Dispersion dans le corpus</h2>
  {dispersion_svg}
</div>

<main>
{sections_html}
</main>

<footer>Généré automatiquement depuis <code>{CORPUS_FILE}</code></footer>
</body>
</html>"""
    return page


def main():
    corpus = load_corpus(CORPUS_FILE)
    html_output = build_html(corpus, target_names, CONTEXT_WINDOW, CASE_SENSITIVE)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"✓ Index KWIC généré : {OUTPUT_FILE}")
    print(f"  Mots-clés : {', '.join(target_names)}")
    print(f"  Fenêtre   : ±{CONTEXT_WINDOW} caractères")


if __name__ == "__main__":
    main()

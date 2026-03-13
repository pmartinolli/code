# -*- coding: utf-8 -*-
# author : pascaliensis with Claude Sonnet 4.6
"""
KWIC (Keywords in Context) Index Generator
Reads corpus.txt and query.csv, then produces a styled HTML index grouped by
canonical entity (Wikidata ID), merging all aliases under the same entry.
Includes a dispersion plot showing where each entity appears in the corpus.
"""

import re
import html
import csv
import os
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────────
CORPUS_FILE   = "corpus.txt"
CSV_FILE      = "query.csv"
OUTPUT_FILE   = "kwic_index-v2.html"
CONTEXT_WINDOW = 300    # characters on each side of the keyword
CASE_SENSITIVE = True  # set True to match exact case only
# ──────────────────────────────────────────────────────────────────────────────

COLORS = [
    "#c0392b", "#2471a3", "#1e8449", "#d4ac0d",
    "#7d3c98", "#ca6f1e", "#117a65", "#2e4057",
]


# ── Load entity definitions from CSV ─────────────────────────────────────────
def load_entities(csv_path: str) -> tuple[dict, dict, dict]:
    """
    Returns:
        id_to_label   : {entity_id: canonical_label}
        id_to_aliases : {entity_id: [alias, ...]}   (insertion-ordered, no dupes)
        alias_to_id   : {alias: entity_id}
    """
    id_to_label   = {}
    id_to_aliases = defaultdict(list)
    alias_to_id   = {}

    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            eid   = row['value'].strip()
            label = row['valueLabel'].strip()
            alias = row['qualifierValue'].strip()

            id_to_label[eid] = label
            if alias not in id_to_aliases[eid]:   # no duplicate aliases per entity
                id_to_aliases[eid].append(alias)
            alias_to_id[alias] = eid              # last row wins on true collision

    return id_to_label, dict(id_to_aliases), alias_to_id


# ── Corpus loading ────────────────────────────────────────────────────────────
def load_corpus(path: str) -> str:
    with open(path, encoding='utf-8', errors='ignore') as f:
        return f.read()


# ── Find occurrences for all aliases, grouped by entity ID ───────────────────
def find_all_occurrences(
    corpus: str,
    id_to_aliases: dict,
    alias_to_id: dict,
    window: int,
    case_sensitive: bool,
) -> dict:
    """
    Returns {entity_id: [(left, matched_alias, right, char_pos), ...]}
    sorted by char_pos within each entity.

    Uses a single combined pass (all aliases sorted longest-first) so that a
    longer alias like "Mr. Horrox" is consumed before the shorter "Horrox" can
    match the same text — no double-counting.
    """
    flags = 0 if case_sensitive else re.IGNORECASE

    # Sort all aliases longest-first so longer strings match before substrings
    all_pairs = sorted(
        [(alias, eid) for eid, aliases in id_to_aliases.items() for alias in aliases],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    alias_to_eid = {alias: eid for alias, eid in all_pairs}

    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(a) for a, _ in all_pairs) + r')\b',
        flags,
    )

    results = defaultdict(list)

    for m in pattern.finditer(corpus):
        matched   = m.group(1)
        entity_id = alias_to_eid.get(matched)
        if entity_id is None:
            for alias, eid in alias_to_eid.items():
                if alias.lower() == matched.lower():
                    entity_id = eid
                    break
        if entity_id is None:
            continue

        start, end = m.start(), m.end()
        left  = corpus[max(0, start - window): start]
        right = corpus[end: min(len(corpus), end + window)]

        if start - window > 0:
            left = re.sub(r'^\S+', '', left)
        if end + window < len(corpus):
            right = re.sub(r'\S+$', '', right)

        results[entity_id].append((left, matched, right, start))

    for eid in results:
        results[eid].sort(key=lambda t: t[3])

    return dict(results)


# ── HTML helpers ──────────────────────────────────────────────────────────────
def render_passage(left: str, match: str, right: str) -> str:
    def esc(text: str) -> str:
        return html.escape(text).replace('\n', '<br>\n')
    return esc(left) + f'<mark class="kw-highlight">{html.escape(match)}</mark>' + esc(right)


# ── Dispersion SVG ────────────────────────────────────────────────────────────
def build_dispersion_svg(
    data: dict,
    entity_ids: list,
    id_to_label: dict,
    corpus_len: int,
    colors: list,
) -> str:
    n      = len(entity_ids)
    W      = 760
    row_h  = 36
    pad_l  = 160
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
        f'<rect width="{total_w}" height="{total_h}" fill="#f0ead8" rx="6"/>',
        f'<text x="{pad_l}" y="18" font-size="11" fill="#7a6a52" '
        f'letter-spacing="1" text-anchor="start">DISPERSION PLOT</text>',
        f'<line x1="{pad_l}" y1="{pad_t + n * row_h}" '
        f'x2="{pad_l + W}" y2="{pad_t + n * row_h}" stroke="#c8b89a" stroke-width="1"/>',
        f'<text x="{pad_l}" y="{pad_t + n * row_h + 14}" '
        f'font-size="9" fill="#aaa" text-anchor="middle">0%</text>',
        f'<text x="{pad_l + W}" y="{pad_t + n * row_h + 14}" '
        f'font-size="9" fill="#aaa" text-anchor="middle">100%</text>',
    ]

    for pct in (25, 50, 75):
        gx = pad_l + int(W * pct / 100)
        lines += [
            f'<line x1="{gx}" y1="{pad_t}" x2="{gx}" y2="{pad_t + n * row_h}" '
            f'stroke="#c8b89a" stroke-width="1" stroke-dasharray="3,3"/>',
            f'<text x="{gx}" y="{pad_t + n * row_h + 14}" '
            f'font-size="9" fill="#aaa" text-anchor="middle">{pct}%</text>',
        ]

    for i, eid in enumerate(entity_ids):
        color = colors[i % len(colors)]
        cy    = pad_t + i * row_h + row_h // 2
        label = id_to_label.get(eid, eid)

        if i % 2 == 0:
            lines.append(
                f'<rect x="{pad_l}" y="{pad_t + i * row_h}" '
                f'width="{W}" height="{row_h}" fill="rgba(0,0,0,0.03)"/>'
            )

        lines.append(
            f'<text x="{pad_l - 8}" y="{cy + 4}" font-size="12" '
            f'fill="{color}" text-anchor="end" font-weight="600">'
            f'{html.escape(label)}</text>'
        )

        for (_, _, _, pos) in data.get(eid, []):
            cx = pad_l + int(W * pos / corpus_len)
            lines.append(
                f'<circle cx="{cx}" cy="{cy}" r="{dot_r}" '
                f'fill="{color}" opacity="0.85">'
                f'<title>{html.escape(label)} @ {pos}/{corpus_len} '
                f'({100 * pos // corpus_len}%)</title>'
                f'</circle>'
            )

    lines.append('</svg>')
    return '\n'.join(lines)


# ── Full HTML page ────────────────────────────────────────────────────────────
def build_html(
    corpus: str,
    data: dict,
    id_to_label: dict,
    id_to_aliases: dict,
) -> str:
    corpus_len = len(corpus)

    # Sort entities by descending occurrence count
    entity_ids = sorted(data.keys(), key=lambda eid: len(data[eid]), reverse=True)
    total      = sum(len(v) for v in data.values())

    dispersion_svg = build_dispersion_svg(
        data, entity_ids, id_to_label, corpus_len, COLORS
    )

    sections_html = ""
    for i, eid in enumerate(entity_ids):
        occurrences = data[eid]
        count       = len(occurrences)
        color       = COLORS[i % len(COLORS)]
        label       = id_to_label.get(eid, eid)
        aliases     = id_to_aliases.get(eid, [])

        alias_pills = " ".join(
            f'<span class="alias-pill">{html.escape(a)}</span>' for a in aliases
        )

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
            <span class="kw-name">{html.escape(label)}</span>
            <span class="kw-count">{count} occurrence{'s' if count != 1 else ''}</span>
        </h2>
        <div class="alias-bar">{alias_pills}</div>
        <div class="entries">
{entries_html}
        </div>
    </section>"""

    return f"""<!DOCTYPE html>
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

  .dispersion-wrap {{
    max-width: 960px;
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
    margin-bottom: .5rem;
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

  .alias-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: .35rem;
    margin-bottom: 1rem;
  }}

  .alias-pill {{
    font-size: .72rem;
    background: var(--cream);
    border: 1px solid var(--rule);
    color: #666;
    padding: .1em .55em;
    border-radius: 20px;
    font-style: italic;
    letter-spacing: .02em;
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
  <p class="subtitle">Keywords in Context — fenêtre ±{CONTEXT_WINDOW} caractères</p>
  <p class="stats">{total} occurrence{'s' if total != 1 else ''} &nbsp;·&nbsp; {len(entity_ids)} entité{'s' if len(entity_ids) > 1 else ''}</p>
</header>

<div class="dispersion-wrap">
  <h2>Dispersion dans le corpus</h2>
  {dispersion_svg}
</div>

<main>
{sections_html}
</main>

<footer>Généré automatiquement depuis <code>{CORPUS_FILE}</code> · entités depuis <code>{CSV_FILE}</code></footer>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    # Resolve file paths
    base      = os.path.dirname(__file__)
    csv_path  = os.path.join(base, CSV_FILE)
    corp_path = os.path.join(base, CORPUS_FILE)

    if not os.path.exists(corp_path):
        corp_path = os.path.join(base, '..', CORPUS_FILE)
    if not os.path.exists(csv_path):
        csv_path = os.path.join(base, '..', CSV_FILE)

    print(f"Loading entities from : {csv_path}")
    print(f"Loading corpus from   : {corp_path}")

    id_to_label, id_to_aliases, alias_to_id = load_entities(csv_path)
    corpus = load_corpus(corp_path)

    print(f"  {len(id_to_label)} entities, {len(alias_to_id)} aliases total")
    print("Searching corpus...")

    data = find_all_occurrences(
        corpus, id_to_aliases, alias_to_id, CONTEXT_WINDOW, CASE_SENSITIVE
    )

    total_hits = sum(len(v) for v in data.values())
    print(f"  {total_hits} occurrences found across {len(data)} entities")

    html_output = build_html(corpus, data, id_to_label, id_to_aliases)

    out_path = os.path.join(base, OUTPUT_FILE)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"✓ Index KWIC généré : {out_path}")


if __name__ == "__main__":
    main()

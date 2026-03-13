# -*- coding: utf-8 -*-
"""
Alias Frequency Counter
Reads corpus.txt and query.csv, then outputs a CSV table with:
  Column 1 : QID + canonical label   (e.g. Q354631 – Jeremiah Horrocks)
  Column 2 : alias
  Column 3 : number of times that alias appears in the corpus
Rows are sorted by entity ID, then descending count.
"""

import re
import csv
import os
from collections import defaultdict

# ── Configuration ─────────────────────────────────────────────────────────────
CORPUS_FILE = "corpus.txt"
CSV_FILE    = "query.csv"
OUTPUT_FILE = "alias_counts.csv"
CASE_SENSITIVE = False
# ─────────────────────────────────────────────────────────────────────────────


def load_entities(csv_path: str):
    id_to_label   = {}
    id_to_aliases = defaultdict(list)

    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            eid   = row['value'].strip()
            label = row['valueLabel'].strip()
            alias = row['qualifierValue'].strip()
            id_to_label[eid] = label
            if alias not in id_to_aliases[eid]:   # avoid duplicate aliases
                id_to_aliases[eid].append(alias)

    return id_to_label, dict(id_to_aliases)


def count_aliases(corpus: str, id_to_aliases: dict, case_sensitive: bool) -> dict:
    """
    Returns {entity_id: {alias: count}}

    Uses a single combined pass over the corpus (all aliases across all entities,
    sorted longest-first) so that a longer alias like "Mr. Horrox" is matched
    before the shorter "Horrox" can consume the same text — no double-counting.
    """
    flags = 0 if case_sensitive else re.IGNORECASE

    # Collect every (alias, entity_id) pair, longest alias first
    all_aliases = []
    for eid, aliases in id_to_aliases.items():
        for alias in aliases:
            all_aliases.append((alias, eid))
    all_aliases.sort(key=lambda x: len(x[0]), reverse=True)

    # Build one combined pattern; each branch is a named group isn't practical
    # at this scale, so we capture the match text and look up which entity owns it.
    alias_to_eid = {alias: eid for alias, eid in all_aliases}
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(a) for a, _ in all_aliases) + r')\b',
        flags,
    )

    # Initialise counts to zero for every alias
    counts = {eid: {alias: 0 for alias in aliases}
              for eid, aliases in id_to_aliases.items()}

    for m in pattern.finditer(corpus):
        matched = m.group(1)
        # Resolve owning entity (case-insensitive lookup)
        eid = alias_to_eid.get(matched)
        if eid is None:
            for alias, e in alias_to_eid.items():
                if alias.lower() == matched.lower():
                    eid = e
                    break
        if eid is None:
            continue
        # Find the canonical alias key (may differ in case)
        for alias in counts[eid]:
            if alias.lower() == matched.lower():
                counts[eid][alias] += 1
                break

    return counts


def main():
    base      = os.path.dirname(__file__)
    csv_path  = os.path.join(base, CSV_FILE)
    corp_path = os.path.join(base, CORPUS_FILE)

    # Fallback to parent directory
    if not os.path.exists(csv_path):
        csv_path = os.path.join(base, '..', CSV_FILE)
    if not os.path.exists(corp_path):
        corp_path = os.path.join(base, '..', CORPUS_FILE)

    print(f"Loading entities from : {csv_path}")
    print(f"Loading corpus from   : {corp_path}")

    id_to_label, id_to_aliases = load_entities(csv_path)

    with open(corp_path, encoding='utf-8', errors='ignore') as f:
        corpus = f.read()

    print(f"Counting aliases in corpus ({len(corpus):,} characters)…")
    counts = count_aliases(corpus, id_to_aliases, CASE_SENSITIVE)

    out_path = os.path.join(base, OUTPUT_FILE)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["QID + Label", "Alias", "Count"])

        for eid in id_to_label:
            label     = id_to_label[eid]
            qid_label = f"{eid.split('/')[-1]} – {label}"   # e.g. Q354631 – Jeremiah Horrocks

            # Sort aliases by descending count
            alias_counts = counts.get(eid, {})
            for alias, count in sorted(alias_counts.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([qid_label, alias, count])

            # Total row for this entity
            total = sum(alias_counts.values())
            writer.writerow([qid_label, "Total", total])

    print(f"✓ Table written to: {out_path}")


if __name__ == "__main__":
    main()

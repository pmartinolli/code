import numpy as np
import matplotlib.pyplot as plt
import re
import os
import csv
from scipy.stats import kstest
from collections import Counter, defaultdict

# ── Load entity definitions from CSV ────────────────────────────────────────
# Expected columns: value (Wikidata ID), valueLabel (canonical label), qualifierValue (alias)
csv_path = os.path.join(os.path.dirname(__file__), "query.csv")
if not os.path.exists(csv_path):
    csv_path = "query.csv"

# Build mappings:  alias → entity_id,  entity_id → canonical label
alias_to_id = {}          # alias string  → Wikidata ID
id_to_label = {}          # Wikidata ID   → canonical label
id_to_aliases = defaultdict(list)  # Wikidata ID → list of aliases

with open(csv_path, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity_id = row['value'].strip().replace("http://www.wikidata.org/entity/","")
        label     = row['valueLabel'].strip()
        alias     = row['qualifierValue'].strip()

        id_to_label[entity_id] = label
        id_to_aliases[entity_id].append(alias)
        alias_to_id[alias] = entity_id   # last alias row wins if duplicated

# All unique aliases to search for
all_aliases = list(alias_to_id.keys())

# ── Load corpus ──────────────────────────────────────────────────────────────
filename = "corpus.txt"
filepath = os.path.join("..", filename)
if not os.path.exists(filepath):
    filepath = filename
    if not os.path.exists(filepath):
        print(f"Error: File {filename} not found.")
        exit(1)

print(f"Loading dataset from: {filepath}")
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# ── Find occurrences ─────────────────────────────────────────────────────────
print("Identifying name occurrences...")

# Sort aliases longest-first so longer strings match before shorter substrings
sorted_aliases = sorted(all_aliases, key=len, reverse=True)
escaped = [re.escape(a) for a in sorted_aliases]
pattern = r'\b(' + '|'.join(escaped) + r')\b'

matches = list(re.finditer(pattern, text, re.IGNORECASE))

occurrences = []       # character positions
found_ids   = []       # entity ID for each match

for match in matches:
    matched_alias = match.group(1)
    # Look up entity ID (case-insensitive fallback)
    entity_id = alias_to_id.get(matched_alias)
    if entity_id is None:
        for alias, eid in alias_to_id.items():
            if alias.lower() == matched_alias.lower():
                entity_id = eid
                break
    if entity_id:
        occurrences.append(match.start())
        found_ids.append(entity_id)

if not occurrences:
    print("No target names found in the text.")
    exit()

positions      = np.array(occurrences)
total_length   = len(text)
normalized_pos = positions / total_length

# ── KS Test ──────────────────────────────────────────────────────────────────
stat, p_value = kstest(normalized_pos, 'uniform')

# ── Dispersion of inter-mention distances ────────────────────────────────────
intervals = np.diff(positions)
if len(intervals) > 0:
    mean_interval      = np.mean(intervals)
    var_interval       = np.var(intervals, ddof=1)
    dispersion_metric  = var_interval / mean_interval
    cv                 = np.std(intervals, ddof=1) / mean_interval
else:
    mean_interval = var_interval = dispersion_metric = cv = 0

# ── Count mentions per entity ID ─────────────────────────────────────────────
id_counts = Counter(found_ids)

# ── Print results ─────────────────────────────────────────────────────────────
print("\n##### Analysis Results #####")
print(f"Total Named Entity Mentions: {len(positions)}")
print(f"Unique Entities Mentioned:   {len(id_counts)}")

print("\nTop 10 Most Mentioned Entities (grouped by ID):")
for entity_id, count in id_counts.most_common(10):
    label   = id_to_label.get(entity_id, entity_id)
    #aliases = ', '.join(id_to_aliases[entity_id])
    print(f"  [{entity_id}] {label} ({count}x)")

print("\n##### Statistical Test Results #####")
print(f"KS Test Statistic: {stat:.4f}")
print(f"KS Test p-value:   {p_value:.4e}")
if p_value < 0.05:
    print("Result: Distribution significantly differs from Uniform (p < 0.05).")
else:
    print("Result: Distribution is consistent with Uniform.")

print(f"\nMean Distance between Mentions: {mean_interval:.2f} characters")
print(f"Variance of Distances:          {var_interval:.2f}")
print(f"Dispersion Metric (Var/Mean):   {dispersion_metric:.2f}")
print(f"Coefficient of Variation:       {cv:.2f}")
if   cv > 1: print("Interpretation: CV > 1 → clustering / burstiness.")
elif cv < 1: print("Interpretation: CV < 1 → regularity.")
else:        print("Interpretation: CV ~ 1 → random Poisson process.")

# ── Visualisations ────────────────────────────────────────────────────────────
plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
plt.eventplot(positions, orientation='horizontal', colors='black', linewidths=0.5)
plt.title("Rug Plot of Scientific Authority Mentions")
plt.xlabel("Position in Text (Characters)")
plt.yticks([])
plt.xlim(0, total_length)

plt.subplot(1, 2, 2)
plt.hist(positions, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
plt.title("Histogram of Mentions Density")
plt.xlabel("Position in Text (Characters)")
plt.ylabel("Frequency")

plt.tight_layout()
plt.savefig('figure-v2.png', format='png', dpi=300)
plt.show()

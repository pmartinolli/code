
import numpy as np
import matplotlib.pyplot as plt
import re
import os
from scipy.stats import kstest
from collections import Counter

# Define the target names of historical scientists
# Using a predefined list as suggested to avoid NER model dependency issues
target_names = [
"Horrox", "Egyptians", "Romans", "Anaximander", "Pythagoreans", "Numa Pompilius", "Democritus", "Eudoxus", "Calippus", "Crabtrie", "Marius", "Townley", "Romer", "Ricciolus", "Kircher", "Pappus", "Halley", "Royal Society", "Galileo", "Wren", "Wallis", "Huygens", "Huygenian", "Hugenius", "Mariotte", "Euclid", "Hook", "Hooke", "Apollonius", "Archimedes", "Snellius", "Des Cartes", "Grimaldus", "Collins", "Slusius", "Huddens", "Desaguliers", "Sauveur", "Copernicus", "Copernican", "Borelli", "Townly", "Cassini", "Pound", "Kepler", "Keplerian", "Bullialdus", "Ptolemy", "Vendelin", "Street", "Tycho", "Mercator", "Norwood", "Picart", "Richer", "Varin", "des Hayes", "Couplet", "Feuillé", "de la Hire", "Colepress", "Sturmy", "Machin", "Pemberton", "Flamsted", "Hevelius", "Cysatus", "Bayer", "Kirch", "Julius Cæsar", "Ponthæus", "Cellius", "Galletius", "Ango", "Storer", "Montenari", "Zimmerman", "Estancius", "Simeon", "Matthew Paris", "Aristotle", "Auzout", "Petit", "Gottignies", "Bradley", "Hipparchus", "Cornelius Gemma", "God", "Pocock", "John", "Moses", "Aaron", "Pythagoras", "Cicer.", "Thales", "Anaxagoros", "Virgil", "Philo Allegor.", "Aratus", "St. Paul", "David", "Solomon", "Job", "Jeremiah", "Pharaoh", "Philolaus", "Aristarchus", "Plato"
]

# File path setup
filename = "corpus.txt"
filepath = os.path.join("..", filename)

# Check if file exists in parent dir, otherwise check current dir
if not os.path.exists(filepath):
    filepath = filename
    if not os.path.exists(filepath):
        print(f"Error: File {filename} not found in .. or current directory.")
        exit(1)

print(f"Loading dataset from: {filepath}")

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# 1. Identify locations of names
print("Identifying name occurrences...")
# Use regex with word boundaries for robustness
pattern = r'\b(' + '|'.join(target_names) + r')\b'
matches = list(re.finditer(pattern, text, re.IGNORECASE))

occurrences = []
found_names = []

for match in matches:
    occurrences.append(match.start())
    # Normalize name to Title Case for counting
    found_names.append(match.group(1).title())

if not occurrences:
    print("No target names found in the text.")
    exit()

# Convert to numpy array
positions = np.array(occurrences)
total_length = len(text)

# 2. Time-series-like array (positions are the events)
# Normalize positions to [0, 1] for KS test against uniform distribution
normalized_positions = positions / total_length

# 3. Kolmogorov-Smirnov Test
# Test if the observed normalized positions follow a uniform distribution [0, 1]
stat, p_value = kstest(normalized_positions, 'uniform')

# 4. Dispersion Index of distances
# Calculate distances (inter-arrival times) between consecutive names
intervals = np.diff(positions)
if len(intervals) > 0:
    mean_interval = np.mean(intervals)
    var_interval = np.var(intervals, ddof=1)
    # The user requested variance/mean of the distances
    dispersion_metric = var_interval / mean_interval
    
    # Also calculating Coefficient of Variation (CV) which is dimensionless
    cv = np.std(intervals, ddof=1) / mean_interval
else:
    mean_interval = 0
    var_interval = 0
    dispersion_metric = 0
    cv = 0

# Generate Summary
counts = Counter(found_names)

print("\n##### Analysis Results #####")
print(f"Total Citations Found: {len(positions)}")
print(f"Unique Scientists Cited: {len(counts)}")
print("\nTop 10 Most Cited Scientists:")
for name, count in counts.most_common(10):
    print(f"  {name}: {count}")

print("\n##### Statistical Test Results #####")
print(f"KS Test Statistic: {stat:.4f}")
print(f"KS Test p-value: {p_value:.4e}")
if p_value < 0.05:
    print("Result: The distribution of names is significantly different from Uniform (p < 0.05).")
else:
    print("Result: The distribution is consistent with Uniform.")

print(f"\nMean Distance between citations: {mean_interval:.2f} characters")
print(f"Variance of Distances: {var_interval:.2f}")
print(f"Dispersion Metric (Var/Mean of distances): {dispersion_metric:.2f}")
print(f"Coefficient of Variation (Std/Mean): {cv:.2f}")
if cv > 1:
    print("Interpretation: CV > 1 suggests clustering/burstiness.")
elif cv < 1:
    print("Interpretation: CV < 1 suggests regularity.")
else:
    print("Interpretation: CV ~ 1 suggests random Poisson process.")

# Visualizations
plt.figure(figsize=(15, 6))

# Subplot 1: Rug Plot
plt.subplot(1, 2, 1)
plt.eventplot(positions, orientation='horizontal', colors='black', linewidths=0.5)
plt.title("Rug Plot of Scientific Authority Citations")
plt.xlabel("Position in Text (Characters)")
plt.yticks([])
plt.xlim(0, total_length)

# Subplot 2: Histogram
plt.subplot(1, 2, 2)
plt.hist(positions, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
plt.title("Histogram of Citation Density")
plt.xlabel("Position in Text (Characters)")
plt.ylabel("Frequency")

plt.tight_layout()
plt.show()
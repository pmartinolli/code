# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 11:35:15 2026

@author: pascaliensis, with Gemini 
"""

# Installation: pip install gliner
# https://github.com/urchade/GLiNER
# https://urchade.github.io/GLiNER/

from gliner import GLiNER
import os

########## Importing the model #############
model = GLiNER.from_pretrained("urchade/gliner_base")

########## Importing the data ##############
CORPUS_FILE = "corpus.txt"
base      = os.path.dirname(__file__)
corp_path = os.path.join(base, CORPUS_FILE)
with open(corp_path, encoding='utf-8', errors='ignore') as f:
    text = f.read()

########### Define the labels you want to extract ####
labels = ["person", "organization"]

########## Processing the data by chunks #############
def get_chunks_with_offsets(text, chunk_size=384, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append((text[start:end], start))
        start += (chunk_size - overlap)
    return chunks

def process_large_text(large_text, model, labels):
    chunks = get_chunks_with_offsets(large_text)
    all_extracted_entities = []
    for chunk_text, global_start in chunks:
        entities = model.predict_entities(chunk_text, labels)
        for ent in entities:
            # Convertir en position globale
            global_ent = {
                'start': ent['start'] + global_start,
                'end': ent['end'] + global_start,
                'label': ent['label'],
                'text': ent['text']
            }
            all_extracted_entities.append(global_ent)

    # Dédoublonnage simple (par position exacte)
    unique_entities = { (e['start'], e['end'], e['label']): e for e in all_extracted_entities }.values()
    # Trier par position de départ
    final_entities = sorted(unique_entities, key=lambda x: x['start'])
    return final_entities

extracted_entities = process_large_text(text, model, labels)

########## Exporting in CSV #############
import csv

output_file = "entities_extracted.csv"
# Configuration des colonnes (Header)
fieldnames = ['type', 'text', 'startPosition', 'endPosition']

with open(output_file, mode='w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    # Écriture de l'en-tête
    writer.writeheader()
    
    # Écriture des données
    for ent in extracted_entities:
        writer.writerow({
            'type': ent['label'],
            'text': ent.get('text', ''), # 'text' est souvent déjà dans la sortie GLiNER
            'startPosition': ent['start'],
            'endPosition': ent['end']
        })

print(f"Fichier CSV généré avec succès : {output_file}")



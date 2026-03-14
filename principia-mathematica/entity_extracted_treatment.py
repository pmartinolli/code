# -*- coding: utf-8 -*-
"""
Created on Fri Mar 13 14:52:19 2026

@author: pascaliensis with Claude Sonnet 4.6
"""

import pandas as pd
import re

# Load CSV with correct types
df = pd.read_csv("entities_extracted.csv", dtype={"type": str, "text": str, "startPosition": int, "endPosition": int})

# Normalize line breaks (\r\n, \r, \n) to a single space
df["text"] = df["text"].str.replace(r"\r\n|\r|\n", " ", regex=True)

# Remove rows where the count of a-z letters (case-insensitive) is 3 or less
df = df[df["text"].str.count(r"[a-zA-Z]") > 3]

# Remove rows containing specific words (truncated before and after)
exclude = ["LEMME", 
           "LEMMA",
           "SCHOLIUM", 
           "Cor.", 
           "Q.E.D.",
           "COROLLARY",
           "Prop.",
           "Theor",
           "Lem",
           ]
pattern = "|".join(re.escape(word) for word in exclude)
df = df[~df["text"].str.contains(pattern, na=False)]

# Remove rows where text starts by small cap
# J'ai remarqué que souvent ce sont des mots tronqués. ex: elves pour themselves 
df = df[df["text"].str.match(r"[A-Z]")]

# For each group with the same startPosition, keep only the row with the longest text
df = (
    df.assign(text_len=df["text"].str.len())
      .sort_values("text_len", ascending=False)
      .drop_duplicates(subset="startPosition", keep="first")
      .drop(columns="text_len")
      .reset_index(drop=True)
)

#print(df)


#df.to_csv("entities_extracted_cleaned.csv", index=False)


df_text = df[["text"]]

# regroup and count rows with same text value
df_text = (
    df.groupby("text", as_index=False)
      .agg(NER_count=("text", "count"))
      .sort_values("NER_count", ascending=False)
      .reset_index(drop=True)
)

# count how many time the text is present in the original corpus
with open("corpus.txt", encoding="utf-8") as f:
    corpus = f.read()
df_text["corpus_count"] = df_text["text"].apply(lambda x: corpus.count(x))


####### Check if there is Named entities found by hand and not by NER
# read query.csv and add rows for qualifierValues not already in df_text
df_query = pd.read_csv("query.csv")
existing = set(df_text["text"])
new_rows = df_query[~df_query["qualifierValue"].isin(existing)][["qualifierValue"]].drop_duplicates()
new_rows = new_rows.rename(columns={"qualifierValue": "text"})
new_rows["onlyManual"] = "ManualOverNER"

df_text = pd.concat([df_text, new_rows], ignore_index=True)

######### Export the compared data ##############
df_text.to_csv("entities_extracted_compared.csv", index=False)

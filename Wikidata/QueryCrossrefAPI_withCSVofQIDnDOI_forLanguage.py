# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 19:06:21 2025

@author: pascaliensis
"""

import csv
import requests
import time

def fetch_crossref_languages(input_csv, output_csv, chunk_size=1000):
    """
    - A lot of Wikidata scholarly items with DOI doesn't have P407 (language used) 
    - I queried Qlever (because no division of the Wikidata graph) to retrieve pairs of QID & DOI where P407 is missing in the hope the data is available in CrossRef and could be used to improve back Wikidata.
    
    - Reads a input.csv CSV with columns qid and DOI. Input of 150 Mb was done without problem.
       Example : 
             qid,doi
             Q132142173,10.1086/1000006
             Q113847548,10.1086/100002
    - Fetches JSON from Crossref API for each DOI,
    - Extracts message.language,
    - And writes results incrementally every `chunk_size` rows into output_languages.csv
        Example : 
             qid,language
             Q132142173,en
             Q113847548,
    - Later the output_languages.csv needs to be treated 
        - to turn the language code into a QID
        - to change the header into "qid,P407"
    """
    results = []
    counter = 0
    
    with open(input_csv, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            qid = row.get("qid")
            print(qid, end=": ")
            doi = row.get("doi", "")
            print(doi, end="= ")
            language = None

            if doi:
                url = "https://api.crossref.org/works/" + doi
                try:
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                    language = data.get("message", {}).get("language")
                    print(language)
                except Exception as e:
                    language = e
                    print(f"Error fetching {doi}: {e}")
                
                # Rate limit: wait 50 ms
                time.sleep(0.05)
            
            results.append({"qid": qid, "language": language})
            counter += 1

            # Every `chunk_size` rows, flush to CSV
            if counter % chunk_size == 0:
                with open(output_csv, "a", newline='', encoding="utf-8") as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=["qid", "language"])
                    if counter == chunk_size:  # write header only once
                        writer.writeheader()
                    writer.writerows(results)
                results = []  # reset buffer
                print(f"✅ Wrote {counter} rows to {output_csv}")

    # Write any remaining rows
    if results:
        with open(output_csv, "a", newline='', encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=["qid", "language"])
            if counter <= chunk_size:  # in case file never got header
                writer.writeheader()
            writer.writerows(results)
        print(f"✅ Finished: wrote total {counter} rows to {output_csv}")


# Example usage:
fetch_crossref_languages("input.csv", "output_languages.csv")

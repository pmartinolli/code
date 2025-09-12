# -*- coding: utf-8 -*-
"""
Created on Wed Sep 10 15:03:10 2025

@author: Pascaliensis

This script converts a partial export of MarcXML file into a RIS file for Zotero

Input : 
    - MARCXML is produced by OCLC WMS catalog
    - All the thesis in History are exported
    - Duplicates are kept
    - Homemade fields are used (999 = URL, etc.)

Output : 
    - RIS file (export_2_zotero.ris) to use with Zotero 
    - Duplicates remains in the RIS file and need to be treated in Zotero

Documentation : 
    - Mapping Zotero / RIS https://github.com/aurimasv/zotero-import-export-formats/blob/master/RIS.ris
    - More about RIS format https://en.wikipedia.org/wiki/RIS_(file_format) 
    - MarcXML https://www.loc.gov/standards/marcxml/ 
    - MarcXML (readable) https://scoap3.org/scoap3-repository/marcxml/


"""





from pymarc import parse_xml_to_array
from itertools import groupby
import unicodedata







def strip_end_spaces(lignes):
    return [ligne.rstrip() for ligne in lignes]


def remove_consecutive_duplicates(lignes):
    return [key for key, _ in groupby(lignes)]






records = parse_xml_to_array("MarcXML_input.xml")



# creating a temporary RIS file with the maximum data retrievable 

with open("temporary.ris", "w", encoding="utf-8") as f:
    for record in records:
        

        ris_entries = []

        # Reference type (default thesis for this project)
        ris_entries.append("TY  - THES")

        for field in record.get_fields():
            tag = field.tag
            
            # Special handling for title
            if tag == '245':
                title = " ".join(field.get_subfields('a', 'b')).strip(" /")
                title = title.rstrip('.')
                ris_entries.append(f"TI  - {title}")
                
            # Titre et/ou Résumé bis
            elif tag == '880':
                title = " ".join(field.get_subfields('a', 'b')).strip(" /")
                link = field.get_subfields('6')
                if link and (link[0].startswith("500") or link[0].startswith("520")):
                    for sn in field.get_subfields('a'):
                        # Here we treat it as an abstract instead of a generic note
                        ris_entries.append(f"AB  - {sn}")
                else :
                    title = title.rstrip('.')
                    ris_entries.append(f"TI  - {title}")
                

            # Authors
            elif tag in ['100']:
                for author in field.get_subfields('a'):
                    author = author.rstrip(',')
                    author = author.rstrip('.')
                    ris_entries.append(f"AU  - {author}")

            # Supervisors
            elif tag in ['700']:
                for author in field.get_subfields('a'):
                    author = author.rstrip(',')
                    author = author.rstrip('.')
                    ris_entries.append(f"A3  - {author}")


            # Keywords
            elif tag == '650':
                for kw in field.get_subfields('a'):
                    kw = kw.rstrip('.')
                    ris_entries.append(f"KW  - {kw}")


            # Identifiers
            elif tag in ['020', '022']:
                for sn in field.get_subfields('a'):
                    ris_entries.append(f"SN  - {sn}")

            # Date
            elif tag in ['260']:
                for sn in field.get_subfields('c'):
                    sn = sn.rstrip('.')
                    ris_entries.append(f"DA  - {sn}")
                    

            # Publication Year
            elif tag in ['260']:
                for sn in field.get_subfields('a'):
                    ris_entries.append(f"CY  - {sn}")

                    
            # Grade type
            elif tag in ['502']:    
                for sn in field.get_subfields('a'):
                    sn = sn.replace('"',"")                    
                    sn = sn.rstrip('.')
                    ris_entries.append(f"M3  - {sn}")         
                for sm in field.get_subfields('d'):
                    sm = sm.rstrip(' ')
                    sm = sm.rstrip('.')
                    sm = sm.rstrip(':')
                    ris_entries.append(f"DA  - {sm}")

            elif tag in ['500']:      
                for sn in field.get_subfields('a'):
                    sn = sn.replace('"',"") 
                    sn = sn.rstrip('.')
                    ris_entries.append(f"AN  - {sn}")         
                for sm in field.get_subfields('d'):
                    sm = sm.rstrip(' ')
                    sm = sm.rstrip('.')
                    sm = sm.rstrip(':')
                    ris_entries.append(f"DA  - {sm}")
                    
            elif tag in ['490']:    
                for sn in field.get_subfields('a'):
                    sn = sn.replace('"',"")                    
                    sn = sn.rstrip('.')
                    ris_entries.append(f"M3  - {sn}")   
                   

            # URL
            elif tag in ['999']:
                for sn in field.get_subfields('a'):
                    ris_entries.append(f"UR  - {sn}")

            
            # Call number
            elif tag in ['852']:
                for sn in field.get_subfields('h'):
                    ris_entries.append(f"CN  - {sn}")      
                    
            # OCLC number
            elif tag in ['001']:
                for sn in record.get_fields(tag):
                    sn = str(sn)
                    sn = sn.replace("=001  ","")
                    ris_entries.append(f"ID  - {sn}")  

            # Nb pages
            elif tag in ['300']:
                for sn in field.get_subfields('a'):
                    sn = sn.rstrip(':')
                    sn = sn.rstrip('+')
                    if "ressource" in sn : sn = ""
                    ris_entries.append(f"SP  - {sn}")          
                    
                    
            # Language
            elif tag in ['041']:
                for sn in field.get_subfields('a'):
                    if ("fre" in sn) : 
                        ris_entries.append("LA  - Français") 
                    if ("eng" in sn) : 
                        ris_entries.append("LA  - Anglais")     

            # Language bis
            elif tag in ['040']:
                for sn in field.get_subfields('b'):
                    if ("fre" in sn) : 
                        ris_entries.append("LA  - Français") 
                    if ("eng" in sn) : 
                        ris_entries.append("LA  - Anglais")  

            # Abstract
            elif tag in ['520']:
                for sn in field.get_subfields('a'):
                   ris_entries.append(f"AB  - {sn}")
                   
            # Permanent URL 
            elif tag in ['586']:
                for sn in field.get_subfields('u'):
                   ris_entries.append(f"UR  - {sn}")
                    
        # Place & Publisher
        ris_entries.append("CY  - Montréal")
        ris_entries.append("PB  - Université de Montréal")
        
        # End of Record 
        ris_entries.append("ER  - \n")
        
        
        
        # merge identical lines 
        strip_end_spaces(ris_entries)
        remove_consecutive_duplicates(ris_entries)  
        
        ris_str = "\n".join(ris_entries)

        f.write(ris_str + "\n")
   







"""
Read the temporary RIS file, process each record separately:
- reorder lines alphabetically inside the record
- remove duplicate lines inside the record
- normalize Unicode (NFC) to treat visually identical characters as identical
- standardize M3 (type of thesis: MA or PhD)
- Merge Abstracts from different languages into one
"""




with open("temporary.ris", "r", encoding="utf-8") as f:
    lines = [line.rstrip("\n") for line in f]

records = []
current = []

# Split RIS file into records
for line in lines:
    if line.strip().startswith("TY  -"):  # new record
        if current:
            records.append(current)
        current = [line]
    elif line.strip().startswith("ER  -"):  # end record
        current.append(line)
        records.append(current)
        current = []
    else:
        current.append(line)

# Process each record
processed_records = []
for rec in records:
    if not rec:
        continue

    # Keep first "TY  -" and last "ER  -"
    ty = rec[0]
    er = rec[-1]
    body = rec[1:-1]

    # Normalize all lines to NFC
    body_norm = [unicodedata.normalize("NFC", l) for l in body]

    # Remove duplicates & sort
    body_norm = sorted(set(body_norm))


    # --- Merge long abstracts ---
    long_abstracts = []
    new_body = []
    
    for line in body_norm:
        if line.startswith("AB  -"):
            content = line[6:].strip()
            # Count words instead of sentences
            word_count = len(content.split())
            if word_count > 40:
                long_abstracts.append(content)
                continue  # ✅ skip adding this line (removes old AB lines)
        new_body.append(line)
    
    # Merge into one AB line if we collected any long abstracts
    if long_abstracts:
        merged_abstract = "AB  - " + "\n\n".join(long_abstracts)
        new_body.append(merged_abstract)


    processed_records.append([ty] + new_body + [er])


####### rewrite the fild M3 (MA & PHD)

# prefixes to replace
prefixesMA = ("M3  - Histoire (M. Sc.)", 
              "M3  - Histoire (M.A.)", 
              "M3  - Maitrise es arts en histoire",
              "M3  - Maîtrise (M.A. Hist.)",
              "M3  - Mémoire (M.A.)",
              "M3  - These (M.A.)",
              "M3  - Thèse (D.E.S.",
              "M3  - Thèse (M. A.)",
              "M3  - Thèse (M. Sc.)",
              "M3  - Thèse (M.A.",
              "M3  - Thèse (de maîtrise",
              "M3  - Thèse. (M.A.)", 
              "M3  - Thèse. (M.A.)",
              "M3  - Tḧse (M.A.)",
              )
prefixesPHD = ("M3  - Histoire (Ph. D.)", 
              "M3  - Thèse (D. ès L.)", 
              "M3  - Thèse (D.L.)",
              "M3  - Thèse (Ph. D.",
              "M3  - Thèse (Ph.D.",
              "M3  - Thèse présentée pour l'obtention du grade de Docteur en Philosophie (Ph. D.)",
              "M3  - Thèse présentée à la Faculté des études supérieures en vue de l'obtention du grade de Phil",
              )

# Process each record
final_records = []

for record in processed_records:
    new_record = []
    for line in record:
        # Convert to string if line is a list
        if isinstance(line, list):
            line = " ".join(line)
        
        line = unicodedata.normalize("NFC", line)
        
        # Replace MA / PhD lines
        if line.startswith(prefixesMA):
            line = "M3  - Mémoire de maîtrise (M.A.)"
        elif line.startswith(prefixesPHD):
            line = "M3  - Thèse de doctorat (Ph.D.)"
        
        new_record.append(line)
    final_records.append(new_record)









# Write back
with open("export_2_zotero.ris", "w", encoding="utf-8") as f:
    for rec in final_records:
        for line in rec:
            f.write(line + "\n")
        f.write("\n")  # blank line between records












"""


Beginning of the MarcXML file : 
    
<?xml version="1.0" encoding="UTF-8" ?>
    <marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">
        <marc:record>
            <marc:leader>01599cam a22003377a 4500</marc:leader>
                <marc:controlfield tag="001">48825601</marc:controlfield>
                <marc:controlfield tag="003">OCoLC</marc:controlfield>
                <marc:controlfield tag="005">20250903183125.0</marc:controlfield>
                <marc:controlfield tag="008">000224s1999    qucab    bm   000 0 fre d</marc:controlfield>
                <marc:datafield tag="040" ind1=" " ind2=" ">
                    <marc:subfield code="a">MUQ</marc:subfield>
                    <marc:subfield code="b">fre</marc:subfield>
                    <marc:subfield code="c">MUQ</marc:subfield>
                    <marc:subfield code="d">OCLCQ    
                ...





"""


    
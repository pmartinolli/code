pip install pandas beautifulsoup4 lxml python-docx ebooklib pymupdf

import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from docx import Document
from ebooklib import epub
import ebooklib
import fitz


# ----------------------------
# HTML / XML / TEI
# ----------------------------
def parse_html_like(text, filetype):

    soup = BeautifulSoup(text, "lxml")
    plain = soup.get_text()

    spans = []
    pos = 0

    tags = soup.find_all(["i", "em"])

    if filetype == "tei":
        tags += soup.find_all("hi", {"rend": "italic"})

    for tag in tags:
        s = tag.get_text()
        start = plain.find(s, pos)

        if start >= 0:
            spans.append((s, start, start + len(s)))
            pos = start + len(s)

    return spans


# ----------------------------
# Markdown
# ----------------------------
def parse_markdown(text):

    spans = []
    pattern = r"\*(.*?)\*|_(.*?)_"

    for m in re.finditer(pattern, text):
        s = m.group(1) or m.group(2)
        spans.append((s, m.start(), m.end()))

    return spans


# ----------------------------
# DOCX
# ----------------------------
def parse_docx(path):

    doc = Document(path)

    spans = []
    pos = 0

    for p in doc.paragraphs:
        for run in p.runs:

            t = run.text

            if run.italic and t.strip():
                spans.append((t, pos, pos + len(t)))

            pos += len(t)

    return spans


# ----------------------------
# EPUB
# ----------------------------
def parse_epub(path):

    book = epub.read_epub(path)

    spans = []
    pos = 0

    for item in book.get_items():

        if item.get_type() == ebooklib.ITEM_DOCUMENT:

            html = item.get_content()
            soup = BeautifulSoup(html, "lxml")

            plain = soup.get_text()

            for tag in soup.find_all(["i", "em"]):

                s = tag.get_text()
                start = plain.find(s)

                if start >= 0:
                    spans.append((s, pos + start, pos + start + len(s)))

            pos += len(plain)

    return spans


# ----------------------------
# RTF
# ----------------------------
def parse_rtf(text):

    spans = []

    pattern = r"\\i\s(.*?)\\i0"

    for m in re.finditer(pattern, text, re.DOTALL):
        s = m.group(1)
        spans.append((s, m.start(), m.end()))

    return spans


# ----------------------------
# PDF (font detection)
# ----------------------------
def parse_pdf(path):

    doc = fitz.open(path)

    spans = []
    pos = 0

    for page in doc:

        blocks = page.get_text("dict")["blocks"]

        for block in blocks:

            for line in block.get("lines", []):

                for span in line.get("spans", []):

                    font = span["font"]
                    text = span["text"]

                    if "Italic" in font or "Oblique" in font:

                        spans.append((text, pos, pos + len(text)))

                    pos += len(text)

    return spans


# ----------------------------
# Main extractor
# ----------------------------
def extract_italics(path, filetype):

    if filetype in ["html", "xml", "tei"]:
        with open(path, encoding="utf8") as f:
            text = f.read()
        spans = parse_html_like(text, filetype)

    elif filetype == "markdown":
        with open(path, encoding="utf8") as f:
            text = f.read()
        spans = parse_markdown(text)

    elif filetype == "docx":
        spans = parse_docx(path)

    elif filetype == "epub":
        spans = parse_epub(path)

    elif filetype == "rtf":
        with open(path, encoding="utf8", errors="ignore") as f:
            text = f.read()
        spans = parse_rtf(text)

    elif filetype == "pdf":
        spans = parse_pdf(path)

    else:
        raise ValueError("Unsupported format")

    df = pd.DataFrame(spans, columns=["string", "start", "end"])
    df["file"] = os.path.basename(path)
    df["format"] = filetype

    return df[["file", "format", "string", "start", "end"]]


# ----------------------------
# Corpus processor
# ----------------------------
def extract_italics_corpus(folder):

    formats = {
        ".html": "html",
        ".xml": "xml",
        ".tei": "tei",
        ".md": "markdown",
        ".docx": "docx",
        ".epub": "epub",
        ".rtf": "rtf",
        ".pdf": "pdf"
    }

    all_tables = []

    for root, dirs, files in os.walk(folder):

        for f in files:

            ext = os.path.splitext(f)[1].lower()

            if ext in formats:

                path = os.path.join(root, f)
                fmt = formats[ext]

                try:
                    df = extract_italics(path, fmt)
                    all_tables.append(df)

                except Exception as e:
                    print("error:", f, e)

    if all_tables:
        return pd.concat(all_tables, ignore_index=True)

    return pd.DataFrame(columns=["file","format","string","start","end"])

# Single file
df = extract_italics("article.xml", "xml")
print(df)

# Whole corpus
dfc = extract_italics_corpus("my_corpus")

dfc.to_csv("italic_spans.csv", index=False)
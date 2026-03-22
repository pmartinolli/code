import re
import pandas as pd
from bs4 import BeautifulSoup
from docx import Document
import zipfile
import ebooklib
from ebooklib import epub
import pdfminer.high_level


def extract_italics(content, filetype):
    """
    Extract italic strings from structured content.

    Parameters
    ----------
    content : str
        Either the structured string OR a file path depending on format
    filetype : str
        One of: html, xml, tei, markdown, docx, pdf, rtf, epub

    Returns
    -------
    pandas.DataFrame
        columns = ["string", "start", "end"]
    """

    results = []

    def build_df(matches):
        return pd.DataFrame(matches, columns=["string", "start", "end"])

    # ------------------------
    # HTML / XML / TEI
    # ------------------------
    if filetype in ["html", "xml", "tei"]:
        soup = BeautifulSoup(content, "lxml")

        text = soup.get_text()
        pos = 0

        for tag in soup.find_all(["i", "em"]):
            s = tag.get_text()
            start = text.find(s, pos)
            end = start + len(s)
            pos = end
            results.append((s, start, end))

        # TEI specific
        if filetype == "tei":
            for tag in soup.find_all("hi", {"rend": "italic"}):
                s = tag.get_text()
                start = text.find(s, pos)
                end = start + len(s)
                pos = end
                results.append((s, start, end))

        return build_df(results)

    # ------------------------
    # Markdown
    # ------------------------
    elif filetype == "markdown":

        pattern = r"\*(.*?)\*|_(.*?)_"
        matches = []

        for m in re.finditer(pattern, content):
            text = m.group(1) or m.group(2)
            start = m.start()
            end = m.end()
            matches.append((text, start, end))

        return build_df(matches)

    # ------------------------
    # DOCX
    # ------------------------
    elif filetype == "docx":

        doc = Document(content)

        full_text = ""
        pos = 0

        for p in doc.paragraphs:
            for run in p.runs:
                run_text = run.text
                if run.italic:
                    start = pos
                    end = pos + len(run_text)
                    results.append((run_text, start, end))
                pos += len(run_text)

        return build_df(results)

    # -----------------------
    # EPUB
    # -----------------------
    elif filetype == "epub":

        book = epub.read_epub(content)
        pos = 0

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:

                html = item.get_content()
                soup = BeautifulSoup(html, "lxml")
                plain = soup.get_text()

                for tag in soup.find_all(["i", "em"]):
                    t = tag.get_text()
                    start = plain.find(t)
                    add(t, pos + start)

                pos += len(plain)

    # -----------------------
    # RTF
    # -----------------------
    elif filetype == "rtf":

        text = content

        # italic blocks \i ... \i0
        pattern = r"\\i\s(.*?)\\i0"

        for m in re.finditer(pattern, text, re.DOTALL):
            t = m.group(1)
            add(t, m.start())


    # ------------------------
    # PDF
    # ------------------------
    elif filetype == "pdf":

        text = pdfminer.high_level.extract_text(content)

        # crude heuristic: italic detection not preserved in plain PDF text
        # placeholder: detect words usually marked by italics markers if present
        # (many PDFs lose this info)

        pattern = r"\*(.*?)\*"
        for m in re.finditer(pattern, text):
            results.append((m.group(1), m.start(), m.end()))

        return build_df(results)

    else:
        raise ValueError("Unsupported filetype")



with open("corpus.rtf") as f:
    rtf = f.read()

df = extract_italics(rtf, "rtf")

print(df) 
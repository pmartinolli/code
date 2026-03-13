# -*- coding: utf-8 -*-
"""
Created on Thu Nov 27 21:49:37 2025

@author: pascaliensis, with Claude Sonnet 4.2
"""

# pip install ocrmypdf
# pip install ghostscript

import ocrmypdf
import tempfile
import os
import shutil
from pathlib import Path
import pytesseract
import ghostscript


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    # Check Tesseract
    if not shutil.which('pytesseract'):
        missing.append('Tesseract OCR')
    
    # Check Ghostscript (gs on Linux/Mac, gswin64c or gswin32c on Windows)
    gs_names = ['gs', 'gswin64c', 'gswin32c']
    if not any(shutil.which(gs) for gs in gs_names):
        missing.append('Ghostscript')
    
    if missing:
        deps_str = ' and '.join(missing)
        raise Exception(
            f"Missing dependencies: {deps_str}\n\n"
            f"Installation instructions:\n"
            f"- Ghostscript: https://ghostscript.com/releases/gsdnld.html\n"
            f"- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
            f"After installation, restart your Python environment."
        )


def process_pdf_with_ocr(input_pdf_path, output_pdf_path=None, language='lat', 
                         deskew=True, remove_background=False, 
                         force_ocr=False, skip_text=False, redo_ocr=False,
                         check_deps=True, **kwargs):
    """
    Process a PDF with OCRmyPDF to add an OCR text layer.
    
    Parameters:
    -----------
    input_pdf_path : str or Path
        Path to the input PDF file
    output_pdf_path : str or Path, optional
        Path for the output PDF. If None, creates a temporary file
    language : str, default='eng'
        OCR language code (e.g., 'eng', 'fra', 'spa', 'deu')
    deskew : bool, default=True
        Whether to deskew crooked pages
    remove_background : bool, default=False
        Whether to remove background from pages
    force_ocr : bool, default=False
        Force OCR even if PDF already has text (keeps existing text + OCR)
    skip_text : bool, default=False
        Skip OCR on pages that already have text
    redo_ocr : bool, default=False
        Remove existing text and redo OCR from scratch
    check_deps : bool, default=True
        Whether to check for dependencies before processing
    **kwargs : dict
        Additional OCRmyPDF parameters
        
    Returns:
    --------
    str : Path to the output PDF file
    
    Notes:
    ------
    - force_ocr: Use for scanned PDFs incorrectly marked as having text
    - skip_text: Use to only OCR image-only pages in mixed PDFs  
    - redo_ocr: Use to replace poor quality existing text with new OCR
    
    Example:
    --------
    >>> # For a scanned PDF marked as Tagged PDF
    >>> output = process_pdf_with_ocr('input.pdf', 'output.pdf', force_ocr=True)
    >>> print(f"OCR processed PDF saved to: {output}")
    """
    
    # Check dependencies first
    if check_deps:
        check_dependencies()
    
    # Convert input path to Path object
    input_path = Path(input_pdf_path)
    
    # Validate input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf_path}")
    
    # Handle output path
    if output_pdf_path is None:
        # Create temporary file if no output path specified
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        output_path = temp_file.name
        temp_file.close()
    else:
        output_path = str(output_pdf_path)
    
    try:
        # Run OCRmyPDF
        ocrmypdf.ocr(
            input_path,
            output_path,
            language=language,
            deskew=deskew,
            remove_background=remove_background,
            force_ocr=force_ocr,
            skip_text=skip_text,
            redo_ocr=redo_ocr,
            **kwargs
        )
        
        print(f"✓ OCR processing complete: {output_path}")
        return output_path
        
    except ocrmypdf.exceptions.PriorOcrFoundError:
        print("⚠ PDF already contains OCR text layer")
        return str(input_path)
    
    except ocrmypdf.exceptions.MissingDependencyError as e:
        # Clean up temp file if created
        if output_pdf_path is None and os.path.exists(output_path):
            os.unlink(output_path)
        
        error_msg = str(e)
        if 'ghostscript' in error_msg.lower() or 'gs' in error_msg.lower():
            raise Exception(
                "Ghostscript not found!\n\n"
                "Install from: https://ghostscript.com/releases/gsdnld.html\n"
                "After installation, restart your Python environment."
            )
        elif 'tesseract' in error_msg.lower():
            raise Exception(
                "Tesseract OCR not found!\n\n"
                "Install from: https://github.com/UB-Mannheim/tesseract/wiki\n"
                "After installation, restart your Python environment."
            )
        else:
            raise Exception(f"Missing dependency: {error_msg}")
        
    except Exception as e:
        # Clean up temp file if created and error occurred
        if output_pdf_path is None and os.path.exists(output_path):
            os.unlink(output_path)
        raise Exception(f"OCR processing failed: {str(e)}")


# Example usage
if __name__ == "__main__":
    # For a scanned PDF that's marked as Tagged PDF (your case)
    output = process_pdf_with_ocr(
        'corpus-latin.pdf', 
        #'output_with_ocr2.pdf',
        language='lat',  # French language (based on filename)
        deskew=True,
        rotate_pages=True,
        #remove_background=True,
        optimize=1,  # PDF optimization level (0-3)
        force_ocr=True,  # Force OCR even though it's marked as Tagged PDF
    )

    
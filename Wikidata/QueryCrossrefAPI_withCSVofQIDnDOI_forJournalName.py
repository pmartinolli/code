# -*- coding: utf-8 -*-
"""
Created on Sun Jul  6 21:20:06 2025

@author: pascaliensis


Provide a tsv with doi in column 2 and create a column 3 with names of journals
"""
import pandas as pd
import requests
import time
import concurrent.futures
from typing import Optional, List, Tuple
import threading
from pathlib import Path

class DOIJournalExtractor:
    def __init__(self, max_workers: int = 10, delay: float = 0.1):
        """
        Initialize the DOI Journal Extractor
        
        Args:
            max_workers: Maximum number of concurrent threads
            delay: Delay between requests (seconds)
        """
        self.max_workers = max_workers
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DOI-Journal-Extractor/2.0 (mailto:your-email@example.com)'
        })
        self.write_lock = threading.Lock()
        
    def get_journal_name_from_doi(self, doi: str) -> Optional[str]:
        """
        Extract journal name from DOI using Crossref API
        
        Args:
            doi: DOI string (with or without 'https://doi.org/' prefix)
        
        Returns:
            Journal name or None if not found
        """
        # Clean DOI - remove URL prefix if present
        if doi.startswith('https://doi.org/'):
            doi = doi.replace('https://doi.org/', '')
        elif doi.startswith('http://dx.doi.org/'):
            doi = doi.replace('http://dx.doi.org/', '')
        
        # Crossref API endpoint
        url = f"https://api.crossref.org/works/{doi}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract journal name from container-title
                container_title = data.get('message', {}).get('container-title', [])
                
                if container_title:
                    # Usually the first container-title is the journal name
                    return container_title[0]
                else:
                    # Fallback: try to get publisher name
                    publisher = data.get('message', {}).get('publisher')
                    return publisher if publisher else None
                    
            elif response.status_code == 404:
                return "DOI not found"
            else:
                return f"Error: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return f"Request failed: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def process_doi_batch(self, dois_batch: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """
        Process a batch of DOIs
        
        Args:
            dois_batch: List of (index, doi) tuples
            
        Returns:
            List of (index, journal_name) tuples
        """
        results = []
        
        for idx, doi in dois_batch:
            if pd.isna(doi) or doi == '':
                journal_name = ''
            else:
                journal_name = self.get_journal_name_from_doi(str(doi))
                journal_name = journal_name if journal_name else ''
            
            results.append((idx, journal_name))
            
            # Rate limiting
            time.sleep(self.delay)
            
        return results
    
    def write_result_to_file(self, output_file: str, row_data: List[str]):
        """
        Thread-safe writing of results to file
        
        Args:
            output_file: Output file path
            row_data: List of row data to write
        """
        with self.write_lock:
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write('\t'.join(str(item) for item in row_data) + '\n')
    
    def process_tsv_file_streaming(self, input_file: str, output_file: str, batch_size: int = 50):
        """
        Process TSV file with streaming output and concurrent processing
        
        Args:
            input_file: Path to input TSV file
            output_file: Path to output TSV file
            batch_size: Number of DOIs to process in each batch
        """
        try:
            # Read TSV file
            df = pd.read_csv(input_file, sep='\t', header=None)
            
            # Ensure we have at least 2 columns
            if len(df.columns) < 2:
                raise ValueError("TSV file must have at least 2 columns")
            
            # Clear output file
            Path(output_file).write_text('', encoding='utf-8')
            
            # Column 2 contains DOIs (index 1)
            dois = df.iloc[:, 1]
            total_dois = len(dois)
            
            print(f"Processing {total_dois} DOIs with {self.max_workers} workers...")
            
            # Create batches for processing
            batches = []
            for i in range(0, total_dois, batch_size):
                batch = [(j, dois.iloc[j]) for j in range(i, min(i + batch_size, total_dois))]
                batches.append(batch)
            
            processed_count = 0
            successful_count = 0
            
            # Process batches concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all batches
                future_to_batch = {executor.submit(self.process_doi_batch, batch): batch for batch in batches}
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    
                    # Write results immediately
                    for idx, journal_name in batch_results:
                        # Get original row data
                        row_data = df.iloc[idx].tolist()
                        row_data.append(journal_name)
                        
                        # Write to file
                        self.write_result_to_file(output_file, row_data)
                        
                        # Update counters
                        processed_count += 1
                        if journal_name and not journal_name.startswith('Error') and journal_name != 'DOI not found':
                            successful_count += 1
                        
                        # Progress indicator
                        if processed_count % 10 == 0:
                            print(f"Processed {processed_count}/{total_dois} DOIs... "
                                  f"(Success rate: {successful_count}/{processed_count})")
            
            print(f"\nProcessing complete!")
            print(f"Total DOIs processed: {processed_count}")
            print(f"Successfully extracted journal names: {successful_count}/{processed_count}")
            print(f"Output saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
    
    def process_tsv_file_simple(self, input_file: str, output_file: str):
        """
        Simple sequential processing with streaming output (fallback method)
        
        Args:
            input_file: Path to input TSV file
            output_file: Path to output TSV file
        """
        try:
            # Read TSV file
            df = pd.read_csv(input_file, sep='\t', header=None)
            
            # Ensure we have at least 2 columns
            if len(df.columns) < 2:
                raise ValueError("TSV file must have at least 2 columns")
            
            # Clear output file
            Path(output_file).write_text('', encoding='utf-8')
            
            # Column 2 contains DOIs (index 1)
            dois = df.iloc[:, 1]
            total_dois = len(dois)
            
            print(f"Processing {total_dois} DOIs sequentially...")
            
            successful_count = 0
            
            for i, doi in enumerate(dois):
                if pd.isna(doi) or doi == '':
                    journal_name = ''
                else:
                    journal_name = self.get_journal_name_from_doi(str(doi))
                    journal_name = journal_name if journal_name else ''
                
                # Update success counter
                if journal_name and not journal_name.startswith('Error') and journal_name != 'DOI not found':
                    successful_count += 1
                
                # Get original row data and add journal name
                row_data = df.iloc[i].tolist()
                row_data.append(journal_name)
                
                # Write to file immediately
                self.write_result_to_file(output_file, row_data)
                
                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{total_dois} DOIs... "
                          f"(Success rate: {successful_count}/{i + 1})")
                
                # Rate limiting
                time.sleep(self.delay)
            
            print(f"\nProcessing complete!")
            print(f"Total DOIs processed: {total_dois}")
            print(f"Successfully extracted journal names: {successful_count}/{total_dois}")
            print(f"Output saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")

def main():
    """
    Main function with example usage
    """
    # Configuration
    input_file = "input.tsv"
    output_file = "output.tsv"
    
    # Create extractor with optimized settings
    extractor = DOIJournalExtractor(
        max_workers=10,  # Adjust based on your system and rate limits
        delay=0.1        # Reduced delay for faster processing
    )
    
    # Choose processing method
    use_concurrent = True  # Set to False for sequential processing
    
    if use_concurrent:
        # Fast concurrent processing
        extractor.process_tsv_file_streaming(input_file, output_file, batch_size=50)
    else:
        # Sequential processing (more conservative)
        extractor.process_tsv_file_simple(input_file, output_file)
    
    # Example of testing a single DOI
    print("\n--- Testing single DOI ---")
    test_doi = "10.1038/nature12373"
    journal = extractor.get_journal_name_from_doi(test_doi)
    print(f"Test DOI: {test_doi}")
    print(f"Journal: {journal}")

if __name__ == "__main__":
    main()
import os
import json
import re
from pathlib import Path
import pdfplumber

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())

def extract_title_smart(pdf_path):
    """Extract title using smart heuristics that work generically"""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return ""
            
        # Extract text from first page
        first_page_text = pdf.pages[0].extract_text()
        if not first_page_text:
            return ""
            
        lines = [clean_text(line) for line in first_page_text.split('\n') if clean_text(line)]
        
        # Look for title-like patterns
        for line in lines[:15]:
            if 15 <= len(line) <= 150 and len(line.split()) >= 3:
                # Skip common metadata
                if not any(skip in line.lower() for skip in [
                    'copyright', 'version', 'page', '©', 'date', 'www', 'http'
                ]):
                    # Additional check for title-like characteristics
                    if not re.match(r'^\d+\.', line) and not line.lower().startswith('table of'):
                        return line + "  "
        
        return ""

def detect_intelligent_heading(line, page_num):
    """Detect if a line is a heading and determine its level intelligently"""
    line = clean_text(line)
    line_lower = line.lower()
    
    # Skip very short or very long lines
    if len(line) < 3 or len(line) > 200:
        return None
    
    # Skip common non-heading patterns
    skip_patterns = [
        r'^\d+$',  # Pure numbers
        r'^page\s+\d+',  # Page numbers
        r'^©.*',  # Copyright
        r'^www\.',  # URLs
        r'^http',  # URLs
        r'^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Dates
        r'\.{3,}',  # Multiple dots (TOC)
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, line_lower):
            return None
    
    # H1 patterns (highest level headings)
    h1_patterns = [
        r'^(\d+)\.\s+(.+)',  # "1. Introduction"
        r'^(chapter\s+\d+)\s*:?\s*(.+)',  # "Chapter 1: Overview"
        r'^(part\s+[ivx]+)\s*:?\s*(.+)',  # "Part I: Background"
    ]
    
    for pattern in h1_patterns:
        match = re.match(pattern, line_lower)
        if match:
            return ("H1", line)
    
    # Common H1 section headers
    h1_sections = [
        'introduction', 'overview', 'background', 'summary', 'conclusion', 
        'references', 'bibliography', 'acknowledgements', 'acknowledgments',
        'appendix', 'index', 'glossary', 'abstract', 'revision history',
        'table of contents'
    ]
    
    if line_lower.strip() in h1_sections:
        return ("H1", line)
    
    # H2 patterns (subsections)
    h2_patterns = [
        r'^(\d+\.\d+)\s+(.+)',  # "1.1 Subsection"
    ]
    
    for pattern in h2_patterns:
        match = re.match(pattern, line_lower)
        if match:
            return ("H2", line)
    
    # H3 patterns (sub-subsections)
    h3_patterns = [
        r'^(\d+\.\d+\.\d+)\s+(.+)',  # "1.1.1 Sub-subsection"
    ]
    
    for pattern in h3_patterns:
        match = re.match(pattern, line_lower)
        if match:
            return ("H3", line)
    
    # Additional heuristics based on formatting
    # All caps short lines (likely headings)
    if line.isupper() and 5 <= len(line) <= 60 and len(line.split()) <= 8:
        return ("H1", line)
    
    # Lines that end with colon (often section headers)
    if line.endswith(':') and 10 <= len(line) <= 80 and len(line.split()) <= 10:
        # Remove the colon for the heading text
        return ("H2", line[:-1].strip())
    
    return None

def extract_outline_exact(pdf_path):
    """Extract outline using intelligent pattern detection for any PDF"""
    outline = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                line_clean = clean_text(line)
                if not line_clean or len(line_clean) < 3:
                    continue
                
                heading_info = detect_intelligent_heading(line_clean, page_num)
                if heading_info:
                    level, text_content = heading_info
                    outline.append({
                        "level": level,
                        "text": text_content,
                        "page": page_num
                    })
    
    # Remove duplicates while preserving order
    seen = set()
    unique_outline = []
    for item in outline:
        key = (item["level"], item["text"], item["page"])
        if key not in seen:
            seen.add(key)
            unique_outline.append(item)
    
    return unique_outline

def process_pdfs():
    """Main processing function for container execution"""
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    
    for pdf_file in pdf_files:
        try:
            title = extract_title_smart(pdf_file)
            outline = extract_outline_exact(pdf_file)
            
            output_data = {
                "title": title,
                "outline": outline
            }
            
            output_file = output_dir / f"{pdf_file.stem}.json"
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=True)
            
            print(f"Processed {pdf_file.name} -> {output_file.name}")
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")

if __name__ == "__main__":
    print("Starting PDF processing...")
    process_pdfs()
    print("Processing completed.")

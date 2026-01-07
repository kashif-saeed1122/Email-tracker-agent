import PyPDF2
import pdfplumber
from typing import Dict
import os


class PDFParser:
    """Parse PDF documents and extract raw text for LLM processing"""
    
    def __init__(self):
        """Initialize PDF Parser"""
        self.ocr_available = False
        try:
            import pytesseract
            self.ocr_available = True
        except ImportError:
            pass
    
    def parse_pdf(
        self,
        pdf_path: str,
        use_ocr: bool = False
    ) -> Dict:
        """
        Parse PDF and extract text
        """
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"PDF file not found: {pdf_path}",
                "extracted_text": "",
                "file_path": pdf_path
            }
        
        try:
            # Try pdfplumber first (best for tables)
            text = self._extract_with_pdfplumber(pdf_path)
            
            # Fallback to PyPDF2
            if not text.strip():
                text = self._extract_with_pypdf2(pdf_path)
            
            # Fallback to OCR
            if not text.strip() and use_ocr and self.ocr_available:
                text = self._extract_with_ocr(pdf_path)
            
            return {
                "success": True,
                "extracted_text": text,
                "file_path": pdf_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "file_path": pdf_path
            }
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber, preserving tables"""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract tables to preserve structure
                    tables = page.extract_tables()
                    page_text = page.extract_text() or ""
                    
                    if tables:
                        for table in tables:
                            # Format table rows clearly
                            table_str = "\n".join([" | ".join([str(cell) for cell in row if cell]) for row in table])
                            page_text += f"\n[TABLE DATA]\n{table_str}\n[/TABLE DATA]\n"
                    
                    text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber extraction error: {e}")
        return text
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PyPDF2 extraction error: {e}")
        return text
    
    def _extract_with_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR (for scanned PDFs)"""
        if not self.ocr_available:
            return ""
        
        text = ""
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            images = convert_from_path(pdf_path)
            for image in images:
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
                
        except Exception as e:
            print(f"OCR extraction error: {e}")
        
        return text
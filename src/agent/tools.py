"""
LangChain Tools for Bill Tracker Agent.

This module provides the interface tools that the AI agent uses to interact with
external systems (Gmail, PDF parsing, RAG/Vector Store, Web Search).

Key Changes:
- Replaced SQL Database tools with RAG-based storage and retrieval.
- Added comprehensive docstrings for better Agent decision-making.
"""

from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
from src.modules.email_scanner import scan_emails as _scan_emails_impl
from src.config.settings import settings


# ==================== Tool Implementations ====================

@tool
def scan_emails(
    date_from: str,
    date_to: str,
    keywords: List[str],
    max_results: int = 50,
    require_attachments: bool = True,
    use_filtering: bool = True
) -> Dict[str, Any]:
    """
    Scans the user's Gmail inbox for emails matching specific criteria.

    Use this tool when you need to find recent bills, invoices, promotions, or 
    order confirmations directly from the source.

    Args:
        date_from (str): Start date for the search in 'YYYY-MM-DD' format.
        date_to (str): End date for the search in 'YYYY-MM-DD' format.
        keywords (List[str]): A list of keywords to filter emails (e.g., ["invoice", "netflix"]).
        max_results (int): Maximum number of emails to retrieve (default: 50).
        require_attachments (bool): If True, only returns emails that have files attached (good for PDF bills).
        use_filtering (bool): If True, applies content relevance checks.

    Returns:
        Dict: A dictionary containing 'success' status, counts, and a list of 'results' 
              (emails with body, sender, and attachment paths).
    """
    return _scan_emails_impl(
        date_from=date_from,
        date_to=date_to,
        keywords=keywords,
        max_results=max_results,
        require_attachments=require_attachments,
        use_filtering=use_filtering
    )


@tool
def parse_pdf(pdf_path: str, use_ocr: bool = False) -> Dict[str, Any]:
    """
    Parses a PDF file from a local path and extracts its raw text content.

    Use this tool after downloading a file from an email to read its contents.
    It attempts to extract text normally first, then falls back to OCR if needed.

    Args:
        pdf_path (str): The absolute local file path to the PDF.
        use_ocr (bool): Set to True if the PDF is a scanned image and requires Optical Character Recognition.

    Returns:
        Dict: Contains 'success' status and the 'extracted_text' string.
    """
    from src.modules.pdf_parser import PDFParser
    
    try:
        parser = PDFParser()
        result = parser.parse_pdf(
            pdf_path=pdf_path,
            use_ocr=use_ocr
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "extracted_text": ""
        }


@tool
def extract_data(text: str, extraction_type: str = "bills") -> Dict[str, Any]:
    """
    Uses an LLM to extract structured data fields from raw text.

    Use this tool to convert messy email bodies or PDF text into clean JSON 
    data (e.g., extracting Vendor, Amount, Due Date).

    Args:
        text (str): The raw text content to analyze.
        extraction_type (str): The schema type to extract. Options:
                               'bills' (for invoices), 
                               'promotions' (for offers/discounts), 
                               'orders' (for shopping receipts), 
                               'general' (for summaries).

    Returns:
        Dict: Contains 'success' status and an 'extracted_data' dictionary with fields 
              matching the requested type.
    """
    from src.modules.llm_interface import LLMInterface
    
    try:
        llm = LLMInterface(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.GEMINI_MODEL
        )
        
        result = llm.extract_data(text=text, extraction_type=extraction_type)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "extracted_data": {}}


@tool
def classify_intent(user_query: str) -> Dict[str, Any]:
    """
    Analyzes a user's natural language query to determine their intent and extract entities.

    Use this tool at the start of a conversation to understand what the user wants 
    (e.g., "scan_bills", "query_history") and to identify parameters like date ranges 
    or specific vendors.

    Args:
        user_query (str): The raw input string from the user.

    Returns:
        Dict: Contains 'intent', 'confidence', and 'entities' (e.g., scan_type, dates).
    """
    from src.modules.llm_interface import LLMInterface
    
    try:
        llm = LLMInterface(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.GEMINI_MODEL
        )
        
        result = llm.classify_intent(user_query=user_query)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "intent": "unknown"}


# ==================== RAG / Storage Tools (Replacing Database) ====================

@tool
def save_bill(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves extracted item data (bills, promos, etc.) into the local RAG Vector Store.

    Use this tool to persist information so it can be queried later. 
    It replaces the old SQL database 'save' functionality.

    Args:
        bill_data (Dict): A dictionary of the extracted data. Must contain meaningful 
                          keys like 'vendor', 'amount', 'date', or 'summary'.

    Returns:
        Dict: Contains 'success' status and the generated 'document_id'.
    """
    from src.modules.rag_system import RAGSystem
    
    try:
        rag = RAGSystem(settings.VOYAGE_API_KEY, settings.VECTOR_STORE_PATH)
        
        # Convert structured data into a descriptive text block for embedding
        # This ensures the RAG system can semantically search the content.
        type_label = bill_data.get('type', 'Document')
        text_content = f"--- {type_label} Data ---\n"
        
        for key, value in bill_data.items():
            if value:
                text_content += f"{key}: {value}\n"
        
        # Add to Vector Store
        return rag.add_document(text=text_content, metadata=bill_data)
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def query_database(query_type: str, filters: Dict = {}, days: int = 7) -> Dict[str, Any]:
    """
    Queries historical data from the local RAG system.
    
    NOTE: This tool replaces the SQL query tool. It converts structured query types 
    into semantic search queries for the Vector Store.

    Args:
        query_type (str): The intent of the query (e.g., "upcoming", "overdue", "by_category").
        filters (Dict): specific filters like {'vendor': 'Netflix'} or {'category': 'utilities'}.
        days (int): Time horizon for the query (used to filter results in post-processing if needed).

    Returns:
        Dict: Contains 'success' status and a list of 'results' (documents found).
    """
    from src.modules.rag_system import RAGSystem
    
    try:
        rag = RAGSystem(settings.VOYAGE_API_KEY, settings.VECTOR_STORE_PATH)
        
        # Transform structural query intentions into semantic search strings
        search_query = ""
        
        if query_type == "upcoming":
            search_query = "bills with upcoming due dates or payment due soon"
        elif query_type == "overdue":
            search_query = "overdue bills, past due payments, unpaid invoices"
        elif query_type == "by_category":
            category = filters.get("category", "expenses")
            search_query = f"spending history for {category} bills"
        else:
            search_query = f"{query_type} documents"
            
        # Append vendor filter to query if present
        if filters.get("vendor"):
            search_query += f" from {filters['vendor']}"
            
        # Perform RAG search
        return rag.search(query=search_query, filters=filters, top_k=10)
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def rag_search(query: str, filters: Optional[Dict] = None, top_k: int = 5) -> Dict[str, Any]:
    """
    Performs a direct semantic search over all stored documents.

    Use this tool when the user asks a natural language question about their history
    (e.g., "How much did I spend on electricity last summer?").

    Args:
        query (str): The natural language search query.
        filters (Optional[Dict]): Metadata filters (e.g., {'vendor': 'Amazon'}).
        top_k (int): Number of most relevant results to return.

    Returns:
        Dict: Contains 'success' status and 'results' (list of relevant documents).
    """
    from src.modules.rag_system import RAGSystem
    
    try:
        rag = RAGSystem(settings.VOYAGE_API_KEY, settings.VECTOR_STORE_PATH)
        return rag.search(query=query, filters=filters, top_k=top_k)
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


@tool
def add_to_rag(text: str, metadata: Dict, doc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Directly adds a text block to the RAG Vector Store.

    Use this tool to index raw text content, such as the full body of a PDF 
    or a long email, so it can be searched later.

    Args:
        text (str): The content to index.
        metadata (Dict): Structured data to attach (e.g., {'source': 'file.pdf'}).
        doc_id (Optional[str]): A unique ID. If None, one is generated automatically.

    Returns:
        Dict: Contains 'success' status and 'document_id'.
    """
    from src.modules.rag_system import RAGSystem
    
    try:
        rag = RAGSystem(settings.VOYAGE_API_KEY, settings.VECTOR_STORE_PATH)
        return rag.add_document(text=text, metadata=metadata, doc_id=doc_id)
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Web & Reminder Tools ====================

@tool
def web_search(query: str, search_type: str = "general", max_results: int = 5) -> Dict[str, Any]:
    """
    Searches the public web using DuckDuckGo.

    Use this tool to find information *outside* the user's data, such as 
    verifying a vendor, finding coupons, or looking up reviews.

    Args:
        query (str): Search keywords.
        search_type (str): Context hint ('general', 'alternatives', 'reviews').
        max_results (int): Number of results to return.

    Returns:
        Dict: Contains 'results' list with titles, snippets, and links.
    """
    from src.modules.web_search import WebSearchTool
    
    try:
        return WebSearchTool().search(query=query, search_type=search_type, max_results=max_results)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def find_alternatives(service_name: str, current_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Specialized web search to find cheaper alternatives for a service.

    Args:
        service_name (str): The service to replace (e.g., "Netflix", "Verizon").
        current_price (Optional[float]): The user's current cost to compare against.

    Returns:
        Dict: List of alternative services found.
    """
    from src.modules.web_search import WebSearchTool
    
    try:
        return WebSearchTool().find_alternatives(service_name=service_name, current_price=current_price)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def create_reminder(bill_id: str, bill_data: Dict, days_before: List[int] = [3, 1]) -> Dict[str, Any]:
    """
    Calculates reminder dates for a specific bill.

    Args:
        bill_id (str): Unique identifier of the bill.
        bill_data (Dict): Must contain a 'due_date'.
        days_before (List[int]): Days before the due date to trigger alerts.

    Returns:
        Dict: List of created reminder objects.
    """
    from src.modules.reminder_system import ReminderSystem
    
    try:
        return ReminderSystem(
            settings.EMAIL_ADDRESS, 
            settings.EMAIL_PASSWORD
        ).create_reminders(bill_id, bill_data, days_before)
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def send_reminder(recipient_email: str, reminder_data: Dict, method: str = "email") -> Dict[str, Any]:
    """
    Sends an actual notification (via Email) to the user.

    Args:
        recipient_email (str): The destination email address.
        reminder_data (Dict): The content of the reminder.
        method (str): Currently supports 'email'.

    Returns:
        Dict: Status of the send operation.
    """
    from src.modules.reminder_system import ReminderSystem
    
    try:
        return ReminderSystem(
            settings.EMAIL_ADDRESS, 
            settings.EMAIL_PASSWORD
        ).send_reminder(recipient_email, reminder_data, method)
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Tool Registry ====================

def get_all_tools() -> List[BaseTool]:
    """
    Returns a list of all available tools for the Agent.
    """
    return [
        scan_emails,
        extract_data,
        classify_intent,
        parse_pdf,
        query_database,
        save_bill,
        rag_search,
        add_to_rag,
        web_search,
        find_alternatives,
        create_reminder,
        send_reminder
    ]
from typing import TypedDict, List, Dict, Optional, Annotated
from operator import add
from datetime import datetime


class AgentState(TypedDict):
    """    
    This state flows through all nodes in the graph and accumulates information
    """
    user_query: str
    user_id: str
    session_id: str
    
    # Intent & Planning
    intent: Optional[str]  
    intent_confidence: float
    entities: Dict  
    plan: List[str]
    
    # Email Processing
    email_scan_results: Optional[Dict]
    downloaded_files: List[str]
    
    # PDF Processing
    pdf_parse_results: List[Dict]
    extracted_bills: List[Dict]
    
    # Database Operations
    database_results: Optional[Dict]
    saved_bill_ids: List[str]
    
    # RAG System
    rag_query: Optional[str]
    retrieved_documents: List[Dict]
    relevance_scores: List[float]
    
    # Web Search
    web_search_results: List[Dict]
    alternatives_found: List[Dict]
    
    # LLM Processing
    llm_extractions: List[Dict]
    llm_responses: List[str]
    
    # Reminders
    reminders_created: List[Dict]
    reminders_sent: int
    
    # Execution Tracking
    current_step: int
    completed_steps: Annotated[List[str], add]  
    tools_used: Annotated[List[str], add]  
    errors: Annotated[List[str], add]
    
    # Response Generation
    context_for_llm: Dict
    final_response: str
    
    # Metadata
    retry_count: int
    max_retries: int
    execution_start_time: float
    requires_human_input: bool
    human_feedback: Optional[str]


class BillData(TypedDict):
    """Structure for bill information"""
    bill_id: Optional[str]
    vendor: str
    amount: float
    currency: str
    due_date: str
    bill_date: str
    category: str
    status: str
    source: str
    document_path: Optional[str]
    account_number: Optional[str]
    confidence: float


class EmailResult(TypedDict):
    """Structure for email scan results"""
    email_id: str
    subject: str
    sender: str
    date: str
    attachments: List[Dict]


class RAGResult(TypedDict):
    """Structure for RAG search results"""
    document_id: str
    document: str
    metadata: Dict
    score: float


def create_initial_state(user_query: str, user_id: str = "default") -> AgentState:
    """
    Create initial state for agent execution
    
    Args:
        user_query: User's input query
        user_id: User identifier
        
    Returns:
        AgentState: Initial state
    """
    return {
        # User Input
        "user_query": user_query,
        "user_id": user_id,
        "session_id": f"{user_id}_{int(datetime.now().timestamp())}",
        
        # Intent & Planning
        "intent": None,
        "intent_confidence": 0.0,
        "entities": {},
        "plan": [],
        
        # Module Results
        "email_scan_results": None,
        "downloaded_files": [],
        "pdf_parse_results": [],
        "extracted_bills": [],
        "database_results": None,
        "saved_bill_ids": [],
        "rag_query": None,
        "retrieved_documents": [],
        "relevance_scores": [],
        "web_search_results": [],
        "alternatives_found": [],
        "llm_extractions": [],
        "llm_responses": [],
        "reminders_created": [],
        "reminders_sent": 0,
        
        # Execution Tracking
        "current_step": 0,
        "completed_steps": [],
        "tools_used": [],
        "errors": [],
        
        # Response
        "context_for_llm": {},
        "final_response": "",
        
        # Metadata
        "retry_count": 0,
        "max_retries": 3,
        "execution_start_time": datetime.now().timestamp(),
        "requires_human_input": False,
        "human_feedback": None
    }
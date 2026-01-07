from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Type
import json


# --- Data Models ---

class BillData(BaseModel):
    """Structured data for bills and invoices"""
    vendor: Optional[str] = Field(description="Company or vendor name")
    amount: Optional[float] = Field(description="Total amount due")
    currency: str = Field(default="USD", description="Currency code")
    due_date: Optional[str] = Field(description="Due date in YYYY-MM-DD format")
    bill_date: Optional[str] = Field(description="Invoice date in YYYY-MM-DD format")
    category: Optional[str] = Field(description="Category (utility, subscription, etc.)")
    invoice_number: Optional[str] = Field(description="Invoice or account number")
    line_items: List[str] = Field(default=[], description="Summary of main line items")


class PromotionData(BaseModel):
    """Structured data for marketing emails and offers"""
    vendor: str = Field(description="Company offering the promotion")
    promo_code: Optional[str] = Field(description="Discount code if available")
    discount_details: str = Field(description="Description of the discount (e.g., '50% off')")
    expiration_date: Optional[str] = Field(description="Expiration date YYYY-MM-DD")
    product_category: Optional[str] = Field(description="What products are on sale")


class OrderData(BaseModel):
    """Structured data for order confirmations"""
    vendor: str = Field(description="Store name")
    order_number: Optional[str] = Field(description="Order ID")
    order_date: Optional[str] = Field(description="Date of purchase YYYY-MM-DD")
    total_amount: Optional[float] = Field(description="Total cost")
    items: List[str] = Field(description="List of items purchased")
    delivery_status: Optional[str] = Field(description="Estimated delivery or status")


class GeneralData(BaseModel):
    """Fallback for unknown types"""
    summary: str = Field(description="Brief summary of the email content")
    key_dates: List[str] = Field(default=[], description="Any important dates mentioned")
    entities: List[str] = Field(default=[], description="Names of companies or people")


class IntentClassification(BaseModel):
    """User intent classification"""
    intent: str = Field(description="Primary intent: scan_bills, scan_emails, query_history, analyze_spending, set_reminder, manual_add")
    scan_type: Optional[str] = Field(description="Specific type if scanning: bills, promotions, orders, banking, etc.")
    confidence: float = Field(description="Confidence score between 0 and 1")
    entities: Dict = Field(default={}, description="Extracted parameters (dates, amounts, vendors)")


class RelevanceEvaluation(BaseModel):
    """Document relevance evaluation"""
    is_relevant: bool = Field(description="Whether document is relevant to query")
    relevance_score: float = Field(description="Relevance score between 0 and 1")
    reasoning: str = Field(description="Brief explanation of relevance")


class LLMInterface:
    """LLM interface using LangChain's Gemini integration"""
    
    def __init__(
        self, 
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1
    ):
        self.model_name = model
        self.temperature = temperature
        
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True
        )
        
        # Registry mapping string types to Pydantic models
        self.extraction_registry = {
            "bills": BillData,
            "invoice": BillData,
            "promotions": PromotionData,
            "discounts": PromotionData,
            "orders": OrderData,
            "receipts": OrderData,
            "shipping": OrderData,
            "general": GeneralData
        }

    def _get_model_for_type(self, extraction_type: str) -> Type[BaseModel]:
        return self.extraction_registry.get(extraction_type.lower(), GeneralData)
        
    def extract_data(self, text: str, extraction_type: str = "bills") -> Dict:
        """
        Extract structured data based on the specific type (bill, promo, etc.)
        """
        pydantic_model = self._get_model_for_type(extraction_type)
        parser = PydanticOutputParser(pydantic_object=pydantic_model)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are an expert data extractor for {extraction_type} documents."),
            ("human", """Extract structured information from the text below.

{format_instructions}

Text to extract from:
{text}

Provide the structured data:""")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({
                "text": text,
                "format_instructions": parser.get_format_instructions()
            })
            
            return {
                "success": True,
                "extracted_data": result.dict(),
                "type": extraction_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extracted_data": {}
            }
    
    def classify_intent(self, user_query: str) -> Dict:
        """
        Classify user intent and identifying scan types.
        """
        parser = PydanticOutputParser(pydantic_object=IntentClassification)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query classifier for a bill tracking system.
Classify user intents into these categories:
- scan_bills: User wants to scan email for new bills/invoices.
- scan_emails: User wants to scan for OTHER email types (promos, orders, etc.).
- query_history: User is asking about past bills.
- analyze_spending: User wants spending analysis.
- set_reminder: User wants to set reminders.
- manual_add: User wants to manually add a bill.

IMPORTANT: If the user mentions "promotions", "orders", "shipping", etc., extract that as 'scan_type'.
"""),
            ("human", """Classify this query and extract entities.

{format_instructions}

User query: {query}

Provide classification:""")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({
                "query": user_query,
                "format_instructions": parser.get_format_instructions()
            })
            
            # Merge scan_type into entities for downstream use
            entities = result.entities
            if result.scan_type:
                entities['email_scan_type'] = result.scan_type
            
            return {
                "success": True,
                "intent": result.intent,
                "confidence": result.confidence,
                "entities": entities
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {}
            }
    
    def generate_response(
        self, 
        user_query: str,
        context: Dict,
        system_prompt: Optional[str] = None
    ) -> Dict:
        if not system_prompt:
            system_prompt = """You are a helpful bill tracking assistant. 
Provide clear, concise, and friendly answers based on the given context.
If bills were found, summarize them clearly.
If alternatives were found, present them with savings calculations.
If errors occurred, mention them politely.
Always be helpful and informative."""
        
        context_str = json.dumps(context, indent=2, default=str)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Context:
{context}

User Question: {query}

Provide a helpful response based on the context above.""")
        ])
        
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({
                "context": context_str,
                "query": user_query
            })
            
            return {
                "success": True,
                "response": result.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error generating a response."
            }
            
    def evaluate_relevance(self, query: str, document: str) -> Dict:
        parser = PydanticOutputParser(pydantic_object=RelevanceEvaluation)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at evaluating document relevance."),
            ("human", """Evaluate if this document is relevant to the query.

{format_instructions}

Query: {query}
Document: {document}

Provide evaluation:""")
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({
                "query": query,
                "document": document,
                "format_instructions": parser.get_format_instructions()
            })
            
            return {
                "success": True,
                "is_relevant": result.is_relevant,
                "relevance_score": result.relevance_score,
                "reasoning": result.reasoning
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_relevant": False,
                "relevance_score": 0.0,
                "reasoning": "Error evaluating relevance"
            }
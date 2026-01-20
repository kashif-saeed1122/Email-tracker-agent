from langgraph.graph import StateGraph, END
from src.agent.state import AgentState, create_initial_state
from src.agent.nodes import (
    intent_classifier_node,
    planner_node,
    email_scanner_node,
    pdf_processor_node,
    data_extractor_node,
    database_saver_node,
    rag_indexer_node,
    rag_retriever_node,
    database_query_node,
    web_searcher_node,
    reminder_creator_node,
    response_generator_node,
    error_handler_node,
    should_continue,
    route_after_intent,
    route_after_plan
)
from typing import Dict
from datetime import datetime


def build_graph() -> StateGraph:
    """
    Build the complete agent workflow graph.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    workflow = StateGraph(AgentState)
    
    # Core nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("response_generator", response_generator_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # Email & PDF processing nodes
    workflow.add_node("email_scanner", email_scanner_node)
    workflow.add_node("pdf_processor", pdf_processor_node)
    workflow.add_node("data_extractor", data_extractor_node)
    
    # Database nodes
    workflow.add_node("database_saver", database_saver_node)
    workflow.add_node("database_query", database_query_node)
    
    # RAG nodes
    workflow.add_node("rag_indexer", rag_indexer_node)
    workflow.add_node("rag_retriever", rag_retriever_node)
    
    # Web & Reminders
    workflow.add_node("web_searcher", web_searcher_node)
    workflow.add_node("reminder_creator", reminder_creator_node)
    
    workflow.set_entry_point("intent_classifier")
        
    # After intent classification, route based on intent
    workflow.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "planner": "planner",
            "error_handler": "error_handler"
        }
    )
    
    workflow.add_conditional_edges(
        "planner",
        route_after_plan,
        {
            "email_scanner": "email_scanner",
            "pdf_processor": "pdf_processor",
            "data_extractor": "data_extractor",
            "database_saver": "database_saver",
            "rag_indexer": "rag_indexer",
            "rag_retriever": "rag_retriever",
            "database_query": "database_query",
            "web_searcher": "web_searcher",
            "reminder_creator": "reminder_creator",
            "response_generator": "response_generator"
        }
    )
        
    COMPREHENSIVE_STEP_MAPPING = {
        "email_scanner": "email_scanner",
        "pdf_processor": "pdf_processor",
        "data_extractor": "data_extractor",
        "database_saver": "database_saver",
        "rag_indexer": "rag_indexer",
        "rag_retriever": "rag_retriever",
        "database_query": "database_query",
        "web_searcher": "web_searcher",
        "reminder_creator": "reminder_creator",
        "response_generator": "response_generator",
        "error_handler": "error_handler",
        "end": END
    }
    
    workflow.add_conditional_edges(
        "email_scanner",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "pdf_processor",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "data_extractor",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "database_saver",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "rag_indexer",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "rag_retriever",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "database_query",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "web_searcher",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_conditional_edges(
        "reminder_creator",
        should_continue,
        COMPREHENSIVE_STEP_MAPPING
    )
    
    workflow.add_edge("response_generator", END)
    workflow.add_edge("error_handler", END)
    
    return workflow.compile()


class BillTrackerAgent:
    
    def __init__(self):
        """Initialize the agent with compiled graph"""
        print("🚀 Initializing Bill Tracker Agent...")
        self.graph = build_graph()
        print("✅ Agent initialized successfully!")
    
    def invoke(
        self, 
        user_query: str, 
        user_id: str = "default",
        verbose: bool = True
    ) -> Dict:
        """
        Process user query through the agent workflow.
        """
        start_time = datetime.now()
        
        if verbose:
            print("\n" + "="*70)
            print(f"🤖 BILL TRACKER AGENT")
            print("="*70)
            print(f"🔍 Query: {user_query}")
            print(f"👤 User: {user_id}")
            print("="*70)
        
        # Create initial state
        initial_state = create_initial_state(user_query=user_query, user_id=user_id)
        
        try:
            # Execute the graph
            final_state = self.graph.invoke(initial_state)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if verbose:
                print("\n" + "="*70)
                print("✅ EXECUTION COMPLETE")
                print("="*70)
                print(f"⏱️  Time: {execution_time:.2f}s")
                print(f"🎯 Intent: {final_state.get('intent', 'unknown')}")
                print(f"🔧 Tools: {', '.join(final_state.get('tools_used', []))}")
                print(f"📊 Steps: {len(final_state.get('completed_steps', []))}")
                if final_state.get('errors'):
                    print(f"⚠️  Errors: {len(final_state['errors'])}")
                print("="*70)
            
            return {
                "success": True,
                "response": final_state.get("final_response", ""),
                "intent": final_state.get("intent", "unknown"),
                "intent_confidence": final_state.get("intent_confidence", 0.0),
                "tools_used": final_state.get("tools_used", []),
                "completed_steps": final_state.get("completed_steps", []),
                "execution_time": execution_time,
                "errors": final_state.get("errors", []),
                "metadata": {
                    "saved_bills": len(final_state.get("saved_bill_ids", [])),
                    "retrieved_docs": len(final_state.get("retrieved_documents", [])),
                    "reminders_created": len(final_state.get("reminders_created", []))
                }
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if verbose:
                print(f"\n❌ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
            
            return {
                "success": False,
                "response": f"I encountered an error: {str(e)}",
                "intent": "error",
                "intent_confidence": 0.0,
                "tools_used": [],
                "completed_steps": [],
                "execution_time": execution_time,
                "errors": [str(e)],
                "metadata": {}
            }


def create_agent() -> BillTrackerAgent:
    """Factory function to create a new agent instance."""
    return BillTrackerAgent()


if __name__ == "__main__":
    def test_agent():
        print("\n" + "="*70)
        print("TESTING BILL TRACKER AGENT")
        print("="*70)
        
        agent = create_agent()
        result = agent.invoke("Show me all my upcoming bills", verbose=True)
        print(f"\n📤 RESPONSE: {result['response']}")

    test_agent()
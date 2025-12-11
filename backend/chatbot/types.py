"""
Shared type definitions for the chatbot module.
This file prevents circular imports by centralizing type definitions.
"""
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import AnyMessage, AIMessage
from typing import Optional, Union, List, Dict, Any
import operator


class MessageState(TypedDict):
    """State object for the health RAG workflow"""
    # Query fields
    original_query: str
    rewritten_query: str
    messages: Annotated[list[AnyMessage], operator.add]
    
    # Patient identification
    pseudonym_id: Optional[str]
    user_email: Optional[str]
    
    # UI state
    step: int
    image_regions: list
    
    # Input paths
    image_path: Optional[str]
    pdf_path: Optional[str]
    
    # OCR & NER results
    ocr_result: str
    ner_result: list[dict]
    medicines: list[str]
    suggested_medicines: list[str]

    # Analysis results
    pathology_report: list[str]
    medgemma_report: str
    llm_report: Annotated[list[AIMessage], operator.add]
    
    # Clinical recommendations
    analyze_medications: str
    suggest_tests: str
    suspected: Union[str, list, dict]
    symptoms: Union[str, list, dict]
    
    # PubMed search results
    pubmed_results: list[dict]
    pubmed_rag_docs: list[dict]
    pubmed_query: str
    
    # Web search results
    web_search_results: list[dict]
    web_search_query: str
    sources: list[dict]

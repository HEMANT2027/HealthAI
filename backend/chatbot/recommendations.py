# clinical_safety.py
from typing import Optional, List, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
import os

# Import from types to avoid circular import
from .types import MessageState

load_dotenv()

class ClinicalSafetyAssistant:
    """Lightweight assistant for clinical safety analysis using Gemini via LangChain."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.3,
    ):
        self.llm: BaseChatModel = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
    

    def analyze_medications(
        self,
        medications: List[str],
        patient_conditions: Any,
        additional_context: Optional[str] = None,
        concise: bool = False,   # new flag
        state:MessageState=None
    ) -> MessageState:
        print("\n   🔬 MEDICATION ANALYSIS FUNCTION")
        print("   " + "-"*56)
        
        meds_display = ", ".join(medications) if medications else "Not provided"
        cond_display = ", ".join(patient_conditions) if patient_conditions else "Not provided"
        
        print(f"   💊 Medications: {meds_display}")
        print(f"   🏥 Conditions: {cond_display}")
        print(f"   📝 Concise mode: {concise}")
        print(f"   ℹ️  Additional context: {additional_context or 'None'}")

        if concise:
            # Strong, explicit instruction for short plain text output
            prompt = f"""
You are a clinical pharmacology expert. Keep your answer very short and plain.
Medications: {meds_display}
Patient Conditions: {cond_display}
Additional Context: {additional_context or 'None'}

Respond in ONE short paragraph (1-3 sentences), simple language, no headings, no lists, avoid technical jargon, and do not use JSON. Focus on the single biggest safety issue and one clear action.
"""
            print("   📋 Using concise prompt template")
        else:
            # original, more detailed prompt
            prompt = f"""
You are a clinical pharmacology expert helping a doctor analyze a patient's medication list.

Medications: {meds_display}
Patient Conditions: {cond_display}
Additional Context: {additional_context or 'None'}

Please provide a clear natural-language report describing:
- Major and moderate drug–drug interactions (plain English)
- Drug–disease contraindications
- Severity of concerns (High/Moderate/Low)
- Clinical actions (avoid, monitor, substitute)
- Overall medication safety summary

Respond in plain text (no JSON).
"""
            print("   📋 Using detailed prompt template")
        
        print(f"   📄 Prompt length: {len(prompt)} chars")
        print("   🤖 Invoking Gemini LLM...")
        response = self.llm.invoke(prompt)
        result = response.content.strip() if hasattr(response, "content") else str(response).strip()
        print(f"   ✅ Analysis complete - {len(result)} chars")
        print(f"   📄 Result preview: {result[:100]}...")
        
        state["analyze_medications"] = result
        return state
    

    def suggest_tests(
        self,
        symptoms: Any,
        suspected_conditions: Any,
        current_results: Optional[str] = None,
        concise: bool = False,
        state:MessageState=None #maybe i am the error
    ) -> MessageState:
        print("\n   🧪 TEST SUGGESTION FUNCTION")
        print("   " + "-"*56)
        
        suspected = ", ".join(suspected_conditions) if suspected_conditions else "Not specified"
        
        print(f"   🩺 Symptoms: {symptoms}")
        print(f"   🔍 Suspected conditions: {suspected}")
        print(f"   📊 Current results: {current_results or 'None'}")
        print(f"   📝 Concise mode: {concise}")

        if concise:
            prompt = f"""
You are a diagnostic medicine specialist. Keep your answer very short and plain.
Symptoms: {symptoms}
Suspected Conditions: {suspected}
Current Results: {current_results or 'None'}

Provide ONE short paragraph (1-3 sentences) listing the top immediate test(s) to order in the ED and the urgency. No headings, no lists, no extra commentary.
"""
            print("   📋 Using concise prompt template")
        else:
            prompt = f"""
You are a diagnostic medicine specialist.

Symptoms: {symptoms}
Suspected Conditions: {suspected}
Current Results: {current_results or 'None'}

Provide a text-based recommendation of essential and follow-up tests, imaging to consider, and urgency.
"""
            print("   📋 Using detailed prompt template")

        print(f"   📄 Prompt length: {len(prompt)} chars")
        print("   🤖 Invoking Gemini LLM...")
        response = self.llm.invoke(prompt)
        result = response.content.strip() if hasattr(response, "content") else str(response).strip()
        print(f"   ✅ Suggestions complete - {len(result)} chars")
        print(f"   📄 Result preview: {result[:100]}...")
        
        state["suggest_tests"] = result
        return state


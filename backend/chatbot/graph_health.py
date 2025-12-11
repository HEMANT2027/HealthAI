from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Union, Optional,Any
import operator
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import os
from .types import MessageState
from .disease_identifier import parse_medgemma_output, GeminiDiseaseExtractor
 
load_dotenv()

try:
    mongo_client = MongoClient(os.getenv('MONGODB_KEY'))
    db = mongo_client['medicotourism']
    reports_collection = db['ocr_medsam_reports']
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongo_client = None

def get_cached_report(pseudonym_id: str) -> dict:
    """Fetch cached analysis results from MongoDB."""
    if not mongo_client:
        return {}
    
    try:
        result = reports_collection.find_one({"pseudonym_id": pseudonym_id})
        return result or {}
    except Exception as e:
        print(f"❌ MongoDB query failed: {e}")
        return {}

def save_analysis_results(state: MessageState, cached_doc: dict = None):
    """Save or update analysis results in MongoDB."""
    if not mongo_client or not state.get("pseudonym_id"):
        return

    try:
        doc = {
            "pseudonym_id": state["pseudonym_id"],
            "prescription_ocr": state.get("ocr_result", ""),
            "pathology_ocr": "\n".join(state.get("pathology_report", [])),
            "medgemma_analysis": state.get("medgemma_report", ""),
            "medicines": state.get("medicines", []),  # Save extracted medicines
            "suspected": state.get("suspected", []),  # Save suspected conditions
            "symptoms": state.get("symptoms", []),    # Save symptoms
            "images": [{
                "url": state.get("image_path", ""),
                "name": os.path.basename(state.get("image_path", "")) if state.get("image_path") else "",
                "regions": state.get("image_regions", [])
            }] if state.get("image_path") else [],
            "meta": {
                "step_completed": state.get("step", 0),
                "timestamp": datetime.utcnow().isoformat()
            },
            "created_by": state.get("user_email"),
            "updated_at": datetime.utcnow()
        }

        # Update existing or insert new
        if cached_doc and "_id" in cached_doc:
            reports_collection.update_one(
                {"_id": cached_doc["_id"]},
                {"$set": doc}
            )
        else:
            doc["created_at"] = datetime.utcnow()
            reports_collection.insert_one(doc)
            
        print("✅ Analysis results saved to MongoDB")
    except Exception as e:
        print(f"❌ Failed to save to MongoDB: {e}")

# ==========================================================
# 📹 Initialize foundation models
# ==========================================================

try:
    llm = ChatOpenAI()
except Exception as e:
    raise RuntimeError("Error initializing Anthropic LLM") from e

try:
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
except Exception as e:
    raise RuntimeError("Error initializing OpenAI embeddings") from e

api_key = os.getenv("GEMINI_API_KEY")
assert api_key is not None, "GEMINI_API_KEY not set in environment"

# ==========================================================
# 📹 Query Rewriting Node
# ==========================================================

def rewrite_query(state: MessageState) -> MessageState:
    """Step 1: Rewrite the initial query for better retrieval."""
    print("\n" + "="*60)
    print("🔄 NODE 1: QUERY REWRITING")
    print("="*60)
    print(f"📥 Original query: {state['original_query']}")
    
    prompt = PromptTemplate.from_template(
        """You are an expert medical language assistant.
        Rewrite the following query to be more specific, clear, and context-rich.

        Original query:
        {query}
        """
    )

    try:
        chain = prompt | llm | StrOutputParser()
        state["rewritten_query"] = chain.invoke({"query": state["original_query"]})
        print(f"📤 Rewritten query: {state['rewritten_query']}")
        print("✅ Query rewriting complete\n")
    except Exception as e:
        print(f"⚠️ Query rewrite failed: {e}")
        state["rewritten_query"] = state["original_query"]
        print(f"📤 Using original query as fallback\n")

    return state


# ==========================================================
# 📹 OCR & NER Processing Node
# ==========================================================

def process_ocr_ner(state: MessageState) -> MessageState:
    """Step 2: Extract text and medical entities from prescription images."""
    print("\n" + "="*60)
    print("📋 NODE 2: OCR & NER PROCESSING")
    print("="*60)
    
    from models.ocr_ner import MedicalOCRPipeline
    
    image_path = state.get("image_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    print(f"👤 Patient ID: {pseudonym_id}")
    print(f"🖼️  Image path: {image_path or 'None'}")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping OCR/NER\n")
        return state
    
    # Check MongoDB cache first
    print("🔍 Checking MongoDB cache...")
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("prescription_ocr"):
        print("✅ Using cached OCR results from MongoDB")
        state["ocr_result"] = cached["prescription_ocr"]
        print(f"📄 OCR text length: {len(state['ocr_result'])} chars")
        # Also restore medicines if available
        if cached.get("medicines"):
            state["medicines"] = cached["medicines"]
            print(f"💊 Restored {len(cached['medicines'])} medicines from cache: {cached['medicines']}")
        print("✅ OCR/NER cache restored\n")
        return state
    
    if not image_path:
        print("⚠️ No image path provided, skipping OCR/NER")
        return state

    try:
        print("\n================ OCR & NER Stage ================")
        pipeline = MedicalOCRPipeline(
            image_path=image_path,
            gcp_key_path=os.getenv("GCP_FILE_PATH"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )

        out_state = pipeline.run(state if isinstance(state, dict) else {})  # type: ignore[assignment]
        state["ocr_result"] = out_state.get("ocr_result", state.get("ocr_result", ""))
        state["ner_result"] = out_state.get("ner_result", state.get("ner_result", []))
        
        # Handle both extracted and suggested medicines
        state["medicines"] = out_state.get("medicines", state.get("medicines", []))
        
        save_analysis_results(state, cached)
        print("✅ OCR & NER processing complete.")
    except Exception as e:
        print(f"❌ OCR/NER processing failed: {e}")
        state["ocr_result"] = ""
        state["ner_result"] = []
        state["medicines"] = []
    
    return state


# ==========================================================
# 📹 Pathology Report Processing Node
# ==========================================================

def process_pathology(state: MessageState) -> MessageState:
    """Step 3: Extract and analyze pathology reports from PDFs."""
    print("\n" + "="*60)
    print("🧪 NODE 3: PATHOLOGY REPORT PROCESSING")
    print("="*60)
    
    from models.patho import PDFPathologyPipeline
    
    pdf_path = state.get("pdf_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    print(f"👤 Patient ID: {pseudonym_id}")
    print(f"📄 PDF path: {pdf_path or 'None'}")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping pathology\n")
        return state
    
    # Check MongoDB cache first
    print("🔍 Checking MongoDB cache...")
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("pathology_ocr"):
        print("✅ Using cached pathology results from MongoDB")
        state["pathology_report"] = cached["pathology_ocr"]
        print(f"📄 Pathology report length: {len(str(state['pathology_report']))} chars")
        print("✅ Pathology cache restored\n")
        return state
    
    if not pdf_path:
        print("⚠️ No pdf path provided, skipping pathology\n")
        return state
    
    try:
        print("🚀 Starting fresh pathology analysis...")
        pipeline = PDFPathologyPipeline(
            pdf_path=pdf_path,
            gcp_key_path=os.getenv("GCP_FILE_PATH"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        print("⚙️  Configuring GCP and Gemini...")
        pipeline.configure_gcp()
        pipeline.configure_gemini()
        
        print("📄 Converting PDF to images...")
        image_paths = pipeline.convert_pdf_to_images()
        print(f"✅ Converted to {len(image_paths)} images")
        
        print("🔍 Running OCR on images...")
        pipeline.run_ocr_on_images(image_paths)
        print(f"✅ OCR complete - Extracted {len(pipeline.ocr_text)} chars")
        
        print("🤖 Running Gemini NER...")
        pipeline.run_gemini_ner()
        print(f"✅ NER complete - Found {len(pipeline.entities)} entities")
        
        state["pathology_report"] = [pipeline.ocr_text]
        # Merge pathology entities with existing NER results
        existing_ner = state.get("ner_result", [])
        state["ner_result"] = existing_ner + pipeline.entities
        print(f"📊 Total NER entities: {len(state['ner_result'])}")
        
        print("💾 Saving results to MongoDB...")
        save_analysis_results(state, cached)
        print("✅ Pathology processing complete\n")
    except Exception as e:
        print(f"❌ Pathology processing failed: {e}")
        import traceback
        traceback.print_exc()
        state["pathology_report"] = []
    
    return state


# ==========================================================
# 📹 MedGemma Multimodal Analysis Node
# ==========================================================

def process_medgemma(state: MessageState) -> MessageState:
    """Step 4: Run multimodal medical analysis using MedGemma."""
    print("\n" + "="*60)
    print("🤖 NODE 4: MEDGEMMA MULTIMODAL ANALYSIS")
    print("="*60)
    
    from models.medgemma import MedGemmaMultiInputClient
    
    image_path = state.get("image_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    print(f"👤 Patient ID: {pseudonym_id}")
    print(f"🖼️  Image path: {image_path or 'None'}")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping MedGemma\n")
        return state
    
    # Check MongoDB cache first
    print("🔍 Checking MongoDB cache...")
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("medgemma_analysis"):
        print("✅ Using cached MedGemma results from MongoDB")
        state["medgemma_report"] = cached["medgemma_analysis"]
        print(f"📄 MedGemma report length: {len(state['medgemma_report'])} chars")
        # Also restore image regions if available
        if cached.get("images"):
            for img in cached["images"]:
                if img.get("url") == image_path and img.get("regions"):
                    state["image_regions"] = img["regions"]
                    print(f"📍 Restored {len(img['regions'])} image regions")
                    break
        print("✅ MedGemma cache restored\n")
        return state
    
    if not image_path :
        print("⚠️ No image path provided, skipping MedGemma\n")
        return state

    try:
        print("\n" + "="*60)
        print("🤖 NODE 4: MEDGEMMA MULTIMODAL ANALYSIS")
        print("="*60)
        print("🚀 Starting fresh MedGemma analysis...")
        
        endpoint_name = os.getenv("MEDGEMMA_ENDPOINT", "jumpstart-dft-hf-vlm-gemma-3-27b-in-20251026-050912")
        print(f"🔗 Using endpoint: {endpoint_name}")
        client = MedGemmaMultiInputClient(endpoint_name=endpoint_name)
        
        # Prepare inputs
        prescription_text = state.get("ocr_result", "No prescription text available")
        pathology_text = "\n".join(state.get("pathology_report", ["No pathology report available"]))
        doctor_prompt = state.get("rewritten_query", state.get("original_query", "Analyze the medical images"))
        
        print(f"📊 Input data:")
        print(f"   - Prescription: {len(prescription_text)} chars")
        print(f"   - Pathology: {len(pathology_text)} chars")
        print(f"   - Doctor prompt: {doctor_prompt[:100]}...")
        
        payload = client.build_payload(
            system_prompt=
            """
You are MedGemma — a multimodal medical reasoning model specialized in interpreting complex patient data, including prescriptions, pathology reports, and medical images. 
You assist doctors by synthesizing information into structured, clinically useful summaries.

=== SYSTEM INSTRUCTIONS ===
- Always maintain a professional, evidence-based medical tone.
- When interpreting data, explicitly mention assumptions or uncertainties.
- Avoid definitive diagnosis unless strongly supported.
- Summarize findings in a structured way.
- When multiple possibilities exist, rank them by likelihood.

=== CONTEXT PROVIDED ===
🧾 Doctor’s Prompt:
{doctor_prompt}

💊 Prescription Text (OCR Extracted):
{prescription_text}

🧪 Pathology Report:
{pathology_text}

🩻 Attached Medical Image(s):
(You have access to visual diagnostic features from the uploaded image(s)).

=== TASK ===
1. Analyze: the image(s) for medically relevant findings.  
2. Correlate: visual observations with the prescription and pathology text.  
3. Reason:through potential diagnoses, conditions, or abnormalities.  
4. Summarize: the key insights clearly for a clinician.  
5. Output: the following structured report:

---

### 🩺 MedGemma Report

1. Observations (Image Analysis):
- [Findings from medical image(s)]

2. Correlation with Prescription:
- [Relevant matches or contradictions]

3. Correlation with Pathology Report:
- [Key overlaps or discrepancies]

4. Differential Diagnoses (Ranked):
1. [Condition A] – [Rationale]
2. [Condition B] – [Rationale]
3. [Condition C] – [Rationale]

5. Recommendations:
- [Next diagnostic or clinical steps]

---

⚠️ If any input (image, text, or report) is missing, state it explicitly and proceed with available data.""",
            doctor_prompt=doctor_prompt,
            prescription_text=prescription_text,
            pathology_text=pathology_text,
            image_paths=[image_path],
            max_tokens=1024
        )
        
        print("🤖 Invoking MedGemma model...")
        response = client.invoke(payload)
        state["medgemma_report"] = response
        print(f"✅ MedGemma analysis complete - Generated {len(response)} chars")
        print(f"📄 Response preview: {response[:150]}...")
        
        # After successful processing, save results
        print("💾 Saving results to MongoDB...")
        save_analysis_results(state, cached)
        print("✅ MedGemma processing complete\n")
    except Exception as e:
        print(f"❌ MedGemma processing failed: {e}")
        import traceback
        traceback.print_exc()
        state["medgemma_report"] = ""
    
    return state


# # ==========================================================
# # 📹 Report Fusion Node
# # ==========================================================

# def fuse_reports(state: MessageState) -> MessageState:
#     """Step 5: Combine reports into unified summary."""
#     print("\n" + "="*60)
#     print("🔀 NODE 5: REPORT FUSION")
#     print("="*60)

#     ocr = state.get("ocr_result", "")
#     ner = json.dumps(state.get("ner_result", []), indent=2)
#     patho = "\n".join(state.get("pathology_report", []))
#     medgemma = state.get("medgemma_report", "")
    
#     print(f"📊 Input data lengths:")
#     print(f"   - OCR text: {len(ocr)} chars")
#     print(f"   - NER entities: {len(state.get('ner_result', []))} items")
#     print(f"   - Pathology: {len(patho)} chars")
#     print(f"   - MedGemma: {len(medgemma)} chars")

#     prompt = PromptTemplate.from_template(
#         """
# You are a  AI clinical Medical expert .Further doctor will ask you some question based on this report as well his general knowledge about the same .
#         Your work is to answer him in concise and precise manner as well think before you answer about the question .
#        This is the context for thresponses .Don't solely stick on them but use your general medical knowledge as well to answer the doctor in best possible manner .
#             Use the following extracted data to write a concise medical summary for a doctor.
# --- OCR Prescription ---
# {ocr}

# --- Medical Entities (NER) ---
# {ner}

# --- Pathology Report ---
# {patho}

# --- MedGemma Analysis ---
# {medgemma}

# **Output Format:**
# 1. Primary Diagnosis:
# 2. Key Lab Findings:
# 3. Imaging Findings:
# 4. Current Medications:
# 5. Recommendations:

# Be concise and factual.
# """
#     )

#     try:
#         print("🤖 Invoking LLM for report fusion...")
#         fused = (prompt | llm).invoke({
#             "ocr": ocr,
#             "ner": ner,
#             "patho": patho,
#             "medgemma": medgemma
#         })
#         state["fused_report"] = fused.content if hasattr(fused, "content") else str(fused)
#         print(f"✅ Report fusion complete - Generated {len(state['fused_report'])} chars")
#         print(f"📄 Fused report preview: {state['fused_report'][:150]}...\n")
#     except Exception as e:
#         print(f"❌ Report fusion failed: {e}")
#         state["fused_report"] = ""

#     return state

def analyze_medications_node(state: MessageState) -> MessageState:
    """Analyze medications extracted from prescriptions"""
    print("\n" + "="*60)
    print("💊 NODE 6: MEDICATION ANALYSIS")
    print("="*60)
    
    # Import here to avoid circular import
    from .recommendations import ClinicalSafetyAssistant
    
    assistant = ClinicalSafetyAssistant()
    # Use extracted medicines from OCR/NER instead of hardcoded
    medications = state.get('medicines', [])
    
    print(f"💊 Medications to analyze: {medications}")
    
    if not medications:
        print("⚠️ No medications found, skipping medication analysis\n")
        state["analyze_medications"] = "No medications found in prescription."
        return state
    
    conditions = state.get('suspected', [])
    print(f"🔍 Suspected conditions: {conditions}")
    print("🤖 Running medication safety analysis...")
    
    result = assistant.analyze_medications(medications, conditions, concise=True, state=state)
    print(f"✅ Medication analysis complete")
    print(f"📄 Analysis preview: {result.get('analyze_medications', '')[:150]}...\n")
    return result

def suggest_tests_node(state: MessageState) -> MessageState:
    """Suggest diagnostic tests based on symptoms and suspected conditions"""
    print("\n" + "="*60)
    print("🧪 NODE 7: TEST RECOMMENDATIONS")
    print("="*60)
    
    # Import here to avoid circular import
    from .recommendations import ClinicalSafetyAssistant
    
    assistant = ClinicalSafetyAssistant()
    symptoms = state.get('suspected', '')
    suspected = state.get('suspected', [])
    
    print(f"🩺 Symptoms: {symptoms}")
    print(f"🔍 Suspected conditions: {suspected}")
    
    if not symptoms and not suspected:
        print("⚠️ No symptoms or suspected conditions, skipping test suggestions\n")
        state["suggest_tests"] = "Insufficient information to suggest tests."
        return state
    
    print("🤖 Generating test recommendations...")
    result = assistant.suggest_tests(symptoms, suspected, concise=True, state=state)
    print(f"✅ Test recommendations complete")
    print(f"📄 Recommendations preview: {result.get('suggest_tests', '')[:150]}...\n")
    return result


def find_test_recommendations(state: MessageState) -> MessageState:
    print("\n" + "="*60)
    print("🔬 NODE 4.5: DISEASE IDENTIFICATION")
    print("="*60)
    
    import os, json
    from typing import cast
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key is not None, "GEMINI_API_KEY not set in environment"
    # Assistant = GeminiDiseaseExtractor(api_key)
    
    example_medgemma_output = state.get('medgemma_report', '')
    print(f"📥 MedGemma report length: {len(example_medgemma_output)} chars")
    
    if isinstance(example_medgemma_output, (dict, list)):
        example_medgemma_output = json.dumps(example_medgemma_output)
    
    print("🤖 Parsing MedGemma output for symptoms and suspected conditions...", example_medgemma_output)
    symptoms, suspected = parse_medgemma_output(example_medgemma_output, api_key)

    print(f"✅ Extracted symptoms: {symptoms}")
    print(f"✅ Suspected conditions: {suspected}")
    
    state["symptoms"] = symptoms
    state['suspected'] = suspected
    print("✅ Disease identification complete\n")
    return state

# ==========================================================
# 📹 Build Complete RAG Workflow with Checkpointing
# ==========================================================

def build_health_rag_graph(checkpointer=None):
    """
    Constructs the complete end-to-end Health AI RAG workflow.
    
    Args:
        checkpointer: Optional LangGraph checkpointer for conversation memory
                     (use MemorySaver() for in-memory or SqliteSaver() for persistence)
    """
    
    workflow = StateGraph(MessageState)
    # Add validation node to ensure required fields
    def validate_state(state: MessageState) -> MessageState:
        if not state.get("pseudonym_id"):
            raise ValueError("pseudonym_id is required")
        state["step"] = state.get("step", 0)
        return state
    
    # Add all processing nodes in sequence
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("ocr_ner", process_ocr_ner)
    workflow.add_node("pathology", process_pathology)
    workflow.add_node("medgemma", process_medgemma)
    # workflow.add_node("fuse_reports", fuse_reports)
    # workflow.add_node("rag_retrieval", context_retrieve)
    workflow.add_node("find_test_recommendations",find_test_recommendations)
    workflow.add_node("analyze_medications", analyze_medications_node)
    workflow.add_node("suggest_tests", suggest_tests_node)
 
    workflow.add_edge(START, "rewrite_query")
    workflow.add_edge("rewrite_query", "ocr_ner")
    workflow.add_edge("ocr_ner", "pathology")
    workflow.add_edge("pathology", "medgemma")
    workflow.add_edge("medgemma","find_test_recommendations")
    workflow.add_edge("find_test_recommendations", "analyze_medications")
    workflow.add_edge("analyze_medications", "suggest_tests")
    workflow.add_edge("suggest_tests", END)
    # workflow.add_edge("suggest_tests", "fuse_reports")
    # workflow.add_edge("fuse_reports", "rag_retrieval")
    # workflow.add_edge("rag_retrieval", END)
    
    # Compile with checkpointer for conversation memory
    return workflow.compile(checkpointer=checkpointer)

# 📹 Initialize graphs with and without memory
# ==========================================================

# For FastAPI: Use memory checkpointer
memory_checkpointer = MemorySaver()
health_rag_graph_with_memory = build_health_rag_graph(checkpointer=memory_checkpointer)

# For simple usage without memory
health_rag_graph = build_health_rag_graph()
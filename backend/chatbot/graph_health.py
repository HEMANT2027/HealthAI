from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import operator
from typing import Union, Optional
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import os
 
load_dotenv()

# ==========================================================
# 📹 MessageState definition with conversation memory
# ==========================================================

class MessageState(TypedDict):
    original_query: str
    rewritten_query: str
    messages: Annotated[list[AnyMessage], operator.add]
    
    # File paths (set externally by FastAPI endpoints)
    image_path: Optional[str]
    pdf_path: Optional[str]

    pseudonym_id: str
    user_email: str
    step: int
    image_regions: list[dict]

    # Core model outputs
    ocr_result: str
    ner_result: list[dict]
    pathology_report: list[str]
    medgemma_report: str

    # Unified & final reasoning output
    fused_report: Union[str, dict, list]
    llm_report: Annotated[list[AIMessage], operator.add]

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
            "images": [{
                "url": state.get("image_path", ""),
                "name": os.path.basename(state.get("image_path", "")),
                "regions": state.get("image_regions", [])
            }] if state.get("image_path") else [],
            "meta": {
                "step_completed": state.get("step", 0),
                "timestamp": datetime.utcnow().isoformat()
            },
            "created_by": state.get("user_email"),
            "created_at": datetime.utcnow()
        }

        # Update existing or insert new
        if cached_doc and "_id" in cached_doc:
            reports_collection.update_one(
                {"_id": cached_doc["_id"]},
                {"$set": doc}
            )
        else:
            reports_collection.insert_one(doc)
            
        print("✅ Analysis results saved to MongoDB")
    except Exception as e:
        print(f"❌ Failed to save to MongoDB: {e}")

# ==========================================================
# 📹 Initialize foundation models
# ==========================================================

try:
    llm = ChatAnthropic(
        model_name="claude-3-haiku-20240307",
        temperature=0,
        timeout=60,
        max_retries=3,
        stop=None
    )
except Exception as e:
    raise RuntimeError("Error initializing Anthropic LLM") from e

try:
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
except Exception as e:
    raise RuntimeError("Error initializing OpenAI embeddings") from e


# ==========================================================
# 📹 Query Rewriting Node
# ==========================================================

def rewrite_query(state: MessageState) -> MessageState:
    """Step 1: Rewrite the initial query for better retrieval."""
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
    except Exception as e:
        print(f"⚠️ Query rewrite failed: {e}")
        state["rewritten_query"] = state["original_query"]

    return state


# ==========================================================
# 📹 OCR & NER Processing Node
# ==========================================================

def process_ocr_ner(state: MessageState) -> MessageState:
    """Step 2: Extract text and medical entities from prescription images."""
    from models.ocr_ner import MedicalOCRPipeline
    
    image_path = state.get("image_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping OCR/NER")
        return state
    
    # Check MongoDB cache first
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("prescription_ocr"):
        print("✅ Using cached OCR results")
        state["ocr_result"] = cached["prescription_ocr"]
        return state
    
    if not image_path :
        print("⚠️ No image path provided, skipping OCR/NER")
        return state

    try:
        print("\n================ OCR & NER Stage ================")
        pipeline = MedicalOCRPipeline(image_path=image_path)
        pipeline.verify_image()
        pipeline.preprocess_image()
        state = pipeline.extract_text_with_vision(state)
        pipeline.configure_gemini()
        state = pipeline.extract_medical_entities(state)
        save_analysis_results(state, cached)
        print("✅ OCR & NER processing complete.")
    except Exception as e:
        print(f"❌ OCR/NER processing failed: {e}")
        state["ocr_result"] = ""
        state["ner_result"] = []
    
    return state


# ==========================================================
# 📹 Pathology Report Processing Node
# ==========================================================

def process_pathology(state: MessageState) -> MessageState:
    """Step 3: Extract and analyze pathology reports from PDFs."""
    from models.patho import PDFPathologyPipeline
    
    pdf_path = state.get("pdf_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping OCR/NER")
        return state
    
    # Check MongoDB cache first
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("pathology_ocr"):
        print("✅ Using cached pathology results")
        state["pathology_report"] = cached["pathology_ocr"]
        return state
    
    if not pdf_path :
        print("⚠️ No pdf path provided, skipping OCR/NER")
        return state
    
    try:
        print("\n================ Pathology Report Stage ================")
        pipeline = PDFPathologyPipeline(
            pdf_path=pdf_path,
            gcp_key_path=os.getenv("GCP_FILE_PATH"),
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        pipeline.configure_gcp()
        pipeline.configure_gemini()
        image_paths = pipeline.convert_pdf_to_images()
        pipeline.run_ocr_on_images(image_paths)
        pipeline.run_gemini_ner()
        
        
        state["pathology_report"] = [pipeline.ocr_text]
        # Merge pathology entities with existing NER results
        existing_ner = state.get("ner_result", [])
        state["ner_result"] = existing_ner + pipeline.entities
        save_analysis_results(state, cached)
        print("✅ Pathology processing complete.")
    except Exception as e:
        print(f"❌ Pathology processing failed: {e}")
        state["pathology_report"] = []
    
    return state


# ==========================================================
# 📹 MedGemma Multimodal Analysis Node
# ==========================================================

def process_medgemma(state: MessageState) -> MessageState:
    """Step 4: Run multimodal medical analysis using MedGemma."""
    from models.medgemma import MedGemmaMultiInputClient
    
    image_path = state.get("image_path", "")
    pseudonym_id = state.get("pseudonym_id")
    
    if not pseudonym_id:
        print("⚠️ No pseudonym_id provided, skipping OCR/NER")
        return state
    
    # Check MongoDB cache first
    cached = get_cached_report(pseudonym_id)
    if cached and cached.get("medgemma_analysis"):
        print("✅ Using cached MedGemma results")
        state["medgemma_report"] = cached["medgemma_analysis"]
        # Also restore image regions if available
        if cached.get("images"):
            for img in cached["images"]:
                if img.get("url") == image_path and img.get("regions"):
                    state["image_regions"] = img["regions"]
                    break
        return state
    
    if not image_path :
        print("⚠️ No image path provided, skipping OCR/NER")
        return state

    try:
        print("\n================ MedGemma Analysis Stage ================")
        endpoint_name = os.getenv("MEDGEMMA_ENDPOINT", "jumpstart-dft-hf-vlm-gemma-3-27b-in-20251026-050912")
        client = MedGemmaMultiInputClient(endpoint_name=endpoint_name)
        
        # Prepare inputs
        prescription_text = state.get("ocr_result", "No prescription text available")
        pathology_text = "\n".join(state.get("pathology_report", ["No pathology report available"]))
        doctor_prompt = state.get("rewritten_query", state.get("original_query", "Analyze the medical images"))
        
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
1. **Analyze** the image(s) for medically relevant findings.  
2. **Correlate** visual observations with the prescription and pathology text.  
3. **Reason** through potential diagnoses, conditions, or abnormalities.  
4. **Summarize** the key insights clearly for a clinician.  
5. **Output** the following structured report:

---

### 🩺 MedGemma Report

**1. Observations (Image Analysis):**
- [Findings from medical image(s)]

**2. Correlation with Prescription:**
- [Relevant matches or contradictions]

**3. Correlation with Pathology Report:**
- [Key overlaps or discrepancies]

**4. Differential Diagnoses (Ranked):**
1. [Condition A] – [Rationale]
2. [Condition B] – [Rationale]
3. [Condition C] – [Rationale]

**5. Recommendations:**
- [Next diagnostic or clinical steps]

---

⚠️ If any input (image, text, or report) is missing, state it explicitly and proceed with available data.""",
            doctor_prompt=doctor_prompt,
            prescription_text=prescription_text,
            pathology_text=pathology_text,
            image_paths=[image_path],
            max_tokens=1024
        )
        
        response = client.invoke(payload)
        state["medgemma_report"] = response
        print("✅ MedGemma analysis complete.")
        
        # After successful processing, save results
        save_analysis_results(state, cached)
    except Exception as e:
        print(f"❌ MedGemma processing failed: {e}")
        state["medgemma_report"] = ""
    
    return state


# ==========================================================
# 📹 Report Fusion Node
# ==========================================================

def fuse_reports(state: MessageState) -> MessageState:
    """Step 5: Combine multiple model reports into one unified clinical summary."""
    print("\n================ Report Fusion Stage ================")

    ocr = state.get("ocr_result", "")
    ner = json.dumps(state.get("ner_result", []), indent=2)
    patho = "\n".join(state.get("pathology_report", []))
    medgemma = state.get("medgemma_report", "")

    prompt = PromptTemplate.from_template(
        """
        You are a clinical report synthesizer.
        Combine the following separate analyses into one coherent medical summary:

        --- OCR Extracted Text ---
        {ocr}

        --- NER Entities ---
        {ner}

        --- Pathology Report ---
        {patho}

        --- MedGemma / Multimodal Summary ---
        {medgemma}

        Produce a structured JSON summary including:
        - Chief Findings
        - Possible Diagnoses
        - Medications
        - Recommended Follow-ups
        - Key Observations
        """
    )

    try:
        fused = (prompt | llm).invoke({
            "ocr": ocr,
            "ner": ner,
            "patho": patho,
            "medgemma": medgemma
        })
        state["fused_report"] = fused.content if hasattr(fused, "content") else str(fused)
        print("✅ Report fusion complete.")
    except Exception as e:
        print(f"❌ Report fusion failed: {e}")
        state["fused_report"] = ""

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
    from .logic import context_retrieve
    
    workflow = StateGraph(MessageState)
    # Add validation node to ensure required fields
    def validate_state(state: MessageState) -> MessageState:
        if not state.get("pseudonym_id"):
            raise ValueError("pseudonym_id is required")
        state["step"] = state.get("step", 0)
        return state
    
    # Add all processing nodes in sequence
    workflow.add_node("validate", validate_state)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("ocr_ner", process_ocr_ner)
    workflow.add_node("pathology", process_pathology)
    workflow.add_node("medgemma", process_medgemma)
    workflow.add_node("fuse_reports", fuse_reports)
    workflow.add_node("rag_retrieval", context_retrieve)
    
    # Define the workflow sequence
    workflow.add_edge(START, "validate")
    workflow.add_edge("validate", "rewrite_query")
    workflow.add_edge("rewrite_query", "ocr_ner")
    workflow.add_edge("ocr_ner", "pathology")
    workflow.add_edge("pathology", "medgemma")
    workflow.add_edge("medgemma", "fuse_reports")
    workflow.add_edge("fuse_reports", "rag_retrieval")
    workflow.add_edge("rag_retrieval", END)
    
    # Compile with checkpointer for conversation memory
    return workflow.compile(checkpointer=checkpointer)

# 📹 Initialize graphs with and without memory
# ==========================================================

# For FastAPI: Use memory checkpointer
memory_checkpointer = MemorySaver()
health_rag_graph_with_memory = build_health_rag_graph(checkpointer=memory_checkpointer)

# For simple usage without memory
health_rag_graph = build_health_rag_graph()
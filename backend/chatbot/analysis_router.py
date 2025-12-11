from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# local imports (avoid circulars)
from .recommendations import ClinicalSafetyAssistant
from .types import MessageState

load_dotenv()

router = APIRouter(prefix="/analyze", tags=["Suggestions"])

MONGO_URI = os.getenv("MONGODB_KEY", "mongodb://localhost:27017")
MONGO_DB = "medicotourism"
MONGO_COLLECTION = "ocr_medsam_reports"

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]


class AnalyzeRequest(BaseModel):
    patient_id: str  # primary key in MongoDB document
    concise: Optional[bool] = False


# try to import existing disease identifier; fallback to a simple stub
try:
    from .disease_identifier import parse_medgemma_output  # expected -> (symptoms, suspected_conditions)
except Exception:  # pragma: no cover
    def identify_diseases(medgemma_report: Any):
        # Fallback stub: return empty lists so pipeline still works
        return [], []


@router.post("/clinical-analyze")
def clinical_analyze(payload: AnalyzeRequest = Body(...)):
    """
    Fetch medicines and medgemma_report for patient_id from MongoDB.
    If cached clinical_analysis exists, return it.
    Otherwise:
      - call disease identifier to get symptoms and suspected_conditions
      - call suggest_tests and analyze_medications
      - store symptoms, suspected_conditions and outputs back to MongoDB
      - return tests and recommendations
    """
    api_key = os.getenv("GEMINI_API_KEY")
    doc = collection.find_one({"pseudonym_id": payload.patient_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Patient document not found")

    # Return cached result if present
    cached = doc.get("clinical_analysis")
    if cached:
        return {"cached": True, "result": cached}

    # Extract inputs - handle both old and new field names
    medicines = doc.get("extracted_medicines") or doc.get("medicines") or doc.get("medications") or []
    medgemma = doc.get("medgemma_analysis") or doc.get("medgemma") or ""
    
    print(f"📊 Fetched from MongoDB:")
    print(f"   Medicines: {medicines}")
    print(f"   MedGemma report length: {len(medgemma)} chars")
    # Identify symptoms & suspected conditions
    try:
        symptoms, suspected_conditions = parse_medgemma_output(medgemma, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disease identifier failed: {e}")

    # Initialize state object
    state: MessageState = {}
    state["medicines"] = medicines
    state["medgemma_report"] = medgemma
    state["symptoms"] = symptoms
    state["suspected"] = suspected_conditions  # FIX: Use 'suspected' to match MessageState type

    # Run clinical assistant
    assistant = ClinicalSafetyAssistant()

    try:
        print(f"🧪 Calling suggest_tests with symptoms={symptoms}, suspected={suspected_conditions}")
        test_state = assistant.suggest_tests(
            symptoms=symptoms,
            suspected_conditions=suspected_conditions,
            current_results=doc.get("current_results"),
            concise=True,  # FIX: Changed from "true" string to True boolean
            state=state,
        )
        print(f"✅ suggest_tests completed")
    except Exception as e:
        print(f"❌ suggest_tests failed: {e}")
        raise HTTPException(status_code=500, detail=f"suggest_tests failed: {e}")

    try:
        print(f"💊 Calling analyze_medications with medicines={medicines}")
        med_state = assistant.analyze_medications(
            medications=medicines,
            patient_conditions=suspected_conditions,  # FIX: Use suspected_conditions instead of doc conditions
            additional_context=doc.get("clinical_history") or "",
            concise=True,  # FIX: Changed from "true" string to True boolean
            state=test_state,
        )
        print(f"✅ analyze_medications completed")
    except Exception as e:
        print(f"❌ analyze_medications failed: {e}")
        raise HTTPException(status_code=500, detail=f"analyze_medications failed: {e}")

    # Prepare result payload
    clinical_analysis: Dict[str, Any] = {
        "symptoms": symptoms,
        "suspected_conditions": suspected_conditions,
        "suggest_tests": test_state.get("suggest_tests"),
        "analyze_medications": med_state.get("analyze_medications"),
    }

    # Persist into MongoDB (atomic update) - FIX: Use pseudonym_id, not patient_id
    print(f"💾 Updating MongoDB for patient: {payload.patient_id}")
    print(f"   Symptoms: {symptoms}")
    print(f"   Suspected: {suspected_conditions}")
    print(f"   Tests: {test_state.get('suggest_tests', 'N/A')[:100]}...")
    print(f"   Medications: {med_state.get('analyze_medications', 'N/A')[:100]}...")
    
    result = collection.update_one(
        {"pseudonym_id": payload.patient_id},  # FIX: Changed from patient_id to pseudonym_id
        {
            "$set": {
                "symptoms": symptoms,
                "suspected": suspected_conditions,  # FIX: Changed from suspected_conditions to suspected
                "clinical_analysis": clinical_analysis,
            }
        },
        upsert=False,
    )
    
    if result.matched_count > 0:
        print(f"✅ MongoDB updated successfully ({result.modified_count} fields modified)")
    else:
        print(f"⚠️ No document found with pseudonym_id: {payload.patient_id}")

    return {"cached": False, "result": clinical_analysis}
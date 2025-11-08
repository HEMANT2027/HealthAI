import os
import json
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
import google.generativeai as genai
from pymongo import MongoClient
from typing import Tuple, Dict, Any
from .auth import authMiddleware
import re
from datetime import datetime  # <-- added

router = APIRouter(prefix="/tourism", tags=["Tourism"])

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_KEY") or os.getenv("MONGO_URI")
MONGO_DB_NAME = "medicotourism"  # <-- added

if not API_KEY:
    raise ValueError("🔴 GEMINI_API_KEY not found. Please check your .env file.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")

# --- Shared mongo client + collection for storing recommendations ---
_mongo_client = None
_db = None
_tourism_collection = None
try:
    if MONGODB_URI:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _mongo_client.get_database(MONGO_DB_NAME)
        _tourism_collection = _db["tourism_recommendations"]
except Exception as e:
    print(f"❌ Warning: could not initialize MongoDB client in recommend.py: {e}")

def fetch_patient_and_medical(pseudonym_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Try to fetch patient profile and medical profile documents from MongoDB.
    Adjust collection names if your schema uses different collections.
    """
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Test the connection
    client.server_info()    
    db = client.get_database("medicotourism")

    # try common collection names; update if your DB uses different names
    patient = None
    medical = None

    try:
        if "intake_forms" in db.list_collection_names():
            patient = db["intake_forms"].find_one({"patient": pseudonym_id}) or db["intake_forms"].find_one({"pseudonym_id": pseudonym_id})
        # fallback common alternatives
        if not patient:
            if "patients" in db.list_collection_names():
                patient = db["patients"].find_one({"patient": pseudonym_id}) or db["patients"].find_one({"pseudonym_id": pseudonym_id})
            if not patient and "intake" in db.list_collection_names():
                patient = db["intake"].find_one({"patient": pseudonym_id}) or db["intake"].find_one({"pseudonym_id": pseudonym_id})
    except Exception:
        patient = None

    try:
        if "ocr_medsam_reports" in db.list_collection_names():
            medical = db["ocr_medsam_reports"].find_one({"pseudonym_id": pseudonym_id}) or db["ocr_medsam_reports"].find_one({"patient": pseudonym_id})
        # fallback alternative collection names
        if not medical and "medical_reports" in db.list_collection_names():
            medical = db["medical_reports"].find_one({"pseudonym_id": pseudonym_id}) or db["medical_reports"].find_one({"patient": pseudonym_id})
    except Exception:
        medical = None

    # Final fallback: try intake_forms again to pull embedded medical data
    if not patient and "intake_forms" in db.list_collection_names():
        patient = db["intake_forms"].find_one({"patient": pseudonym_id}) or db["intake_forms"].find_one({"pseudonym_id": pseudonym_id})

    return (patient or {}, medical or {})

# --- NEW: use Gemini to extract a concise "Impression" / treatmentType ---
def _extract_impression_with_gemini(med_text: str) -> str:
    """
    Ask the Gemini model to extract a single concise 'Impression' or 'Conclusion'
    sentence/line from med_text. Returns empty string on failure.
    """
    if not med_text or not isinstance(med_text, str):
        return ""

    # Keep the instruction extremely strict to avoid JSON / extra text
    instruction = (
"You are a clinical assistant. From the following medical analysis text, "
        "RETURN ONLY the single primary DIAGNOSIS TERM (one short phrase). "
        "Do NOT include question marks, modifiers like 'suspected', 'possible', "
        "'likely', '–' comments, ICD codes, parentheses, or any extra text. "
        "Return plain text only, a single phrase (e.g. 'Appendicitis', "
        "'Community-Acquired Pneumonia').\n\n"
        "Medical analysis text:\n"
        "'''\n"
        f"{med_text[:6000]}\n"
        "'''\n\n"
        "Return only the primary diagnosis term on one line."
    )

    try:
        resp = model.generate_content(instruction)
        text = (resp.text or "").strip()
        # remove fenced blocks or accidental markdown
        text = text.replace("```", "").strip()
        # collapse whitespace and return first non-empty line
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines[0] if lines else ""
    except Exception as e:
            return ""

def build_prompt(patient: Dict[str, Any], medical: Dict[str, Any]) -> str:
    """Create the prompt for Gemini from the patient + medical dicts."""
    # extract a concise treatmentType from medgemma_analysis (impression/conclusion)
    med_text = medical.get('medgemma_analysis')
    treatment_type = _extract_impression_with_gemini(med_text)
    
    print("treatment_type:",treatment_type)

    user_profile_details = f"""
--- Patient Profile ---
Name: {patient.get('fullName') or patient.get('name') or 'N/A'}
Age: {patient.get('age', 'N/A')}
Country: {patient.get('country', 'N/A')}
Budget: ${patient.get('budget', 'N/A')}
Sightseeing: {patient.get('hasSightseeing', 'N/A')} ({patient.get('sightseeingDays', 0)} days)
Preferences: {', '.join(patient.get('sightseeingPrefs', [])) if patient.get('sightseeingPrefs') else 'None'}
Notes:{patient.get('notes') or None}

--- Medical Profile ---
Treatment Type: {treatment_type}
"""

    prompt = f"""
You are a medical travel itinerary assistant. 
Your task is to recommend hospitals in India and generate a detailed itinerary for a patient traveling for treatment, based on nationality, dietary restrictions, and recovery needs.

### USER PROFILE
{user_profile_details}

 ### TASK DETAILS
    1.Recommend 2–3 top hospitals in India that specialize in treating the patient's condition and accept international patients.
    2. For each hospital, include:
    - Name, location, and accreditation (NABH/JCI if applicable)
    - Specialty relevant to the condition
    - Average cost of treatment (approximate)
    - Contact or website (if available)
    3. Create a full itinerary for the patient including:
    - Day of arrival
    - Pre-operation checkup
    - Operation day
    - Recovery period (mention whether the patient can step outside or needs rest)
    - Post-recovery sightseeing plan (based on mobility and health)
    4. Recommend **local places to visit** near the hospital during the recovery phase, filtered by:
    - Accessibility (light walking or drive)
    - Dietary compatibility (e.g., halal food nearby)
    - Cultural/religious comfort (based on nationality and diet) if religion or dietary restrictions is present in the user profile in notes pay special attention.

    5. Mention whether **hospital staff or nearby accommodations** can provide meals matching the dietary restrictions.

    6. Format your output in clear, structured text or JSON:
    ```json

{{ 
  "HospitalRecommendations": [ {{ "Name": "", "City": "", "Accreditation": "", "Specialization": "", "ApproxTreatmentCost": "", "Website": "" }} ],
  "Itinerary": [ {{ "Day": "", "Activity": "", "Notes": "" }} ],
  "RecoveryAndSightseeing": [ {{ "Place": "", "WhyRecommended": "", "NearbyDietaryOptions": "" }} ]
}}

Return valid JSON only. If you cannot return strict JSON, return a plain-text summary with clear headings.
"""
    return prompt

def generate_itinerary_for_pseudonym(pseudonym_id: str) -> Dict[str, Any]:
    """
    Fetch patient & medical data from MongoDB, call Gemini and return parsed JSON (if possible)
    or raw text under 'raw' key. Also persist the result to mongodb (tourism_recommendations).
    """
    patient, medical = fetch_patient_and_medical(pseudonym_id)
    if not patient and not medical:
        raise ValueError(f"No patient or medical profile found for pseudonym_id={pseudonym_id}")

    prompt = build_prompt(patient, medical)

    try:
        response = model.generate_content(prompt)
        text = (response.text or "").strip()

        # Try to clean fenced code blocks then parse JSON
        cleaned = text.replace("```json", "").replace("```", "").strip()
        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = None

        # Persist to MongoDB (upsert)
        try:
            if _tourism_collection is not None:
                doc = {
                    "pseudonym_id": pseudonym_id,
                    "json": parsed,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                _tourism_collection.update_one(
                    {"pseudonym_id": pseudonym_id},
                    {"$set": doc},
                    upsert=True
                )
        except Exception as e:
            # non-fatal; log and continue
            print(f"❌ Failed to persist tourism recommendation: {e}")

        if parsed is not None:
            return {"success": True, "json": parsed}
        else:
            # If not JSON, still return raw text
            return {"success": True, "json": None, "raw": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/recommend/{pseudonym_id}")
async def recommend_for_patient(pseudonym_id: str, current_user: dict = Depends(authMiddleware)):
    """
    Fetch patient data from MongoDB and return itinerary / recommendations generated by Gemini.
    Response format:
      { success: True, json: <parsed JSON or null>, raw: <raw model text> }
    """
    try:
        result = generate_itinerary_for_pseudonym(pseudonym_id)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW endpoint: fetch stored recommendation (if any) ---
@router.get("/stored/{pseudonym_id}")
async def get_stored_recommendation(pseudonym_id: str, current_user: dict = Depends(authMiddleware)):
    """
    Return the stored recommendation document for the given pseudonym_id (if available).
    """
    try:
        if _tourism_collection is None:
            raise HTTPException(status_code=500, detail="Storage not configured on server")
        doc = _tourism_collection.find_one({"pseudonym_id": pseudonym_id})
        if not doc:
            raise HTTPException(status_code=404, detail="No stored recommendation found")
        # Remove Mongo _id for client
        doc.pop("_id", None)
        # Convert datetimes to ISO
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        if isinstance(doc.get("updated_at"), datetime):
            doc["updated_at"] = doc["updated_at"].isoformat()
        return {"success": True, "recommendation": doc}
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # CLI usage: pass pseudonym id as env or argument for testing
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else input("Enter pseudonym_id: ").strip()
    out = generate_itinerary_for_pseudonym(pid)
    print(json.dumps(out, indent=2))
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv
from .Mongo_connect import get_mongo_connection
from urllib.parse import urlsplit, urlunsplit
from .auth import authMiddleware

load_dotenv()

router = APIRouter(prefix="/intake", tags=["Intake Form"])

# ---------- Configuration ----------
try:
    mongo_conn = get_mongo_connection()
    db = mongo_conn.get_database()
    intake_collection = db.get_collection("intake_forms")
    patients_collection = db.get_collection("patients")
    print("✅ MongoDB connected in intake.py")
except Exception as e:
    print(f"❌ MongoDB connection failed in intake.py: {e}")
    raise

# ---------- Pydantic Models ----------

class DocumentInfo(BaseModel):
    url: str
    presigned_url: Optional[str] = None
    fileName: str
    uploadedAt: str
    type: Optional[str] = None  # File type: prescription, pathology, scan

class IntakeFormCreate(BaseModel):
    pseudonym_id: str = Field(...)
    fullName: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=1, le=120)
    phone: str = Field(..., min_length=10, max_length=20)
    country: str = Field(..., min_length=2, max_length=100)
    budget: float = Field(..., ge=0)
    hasSightseeing: str = Field(..., pattern="^(yes|no)$")
    sightseeingDays: Optional[int] = Field(None, ge=1, le=30)
    sightseeingPrefs: List[str] = []
    notes: Optional[str] = None
    documents: List[DocumentInfo] = []
    
    @validator('sightseeingDays')
    def validate_sightseeing_days(cls, v, values):
        if values.get('hasSightseeing') == 'yes' and v is None:
            raise ValueError('Sightseeing days required when sightseeing is enabled')
        return v

# ---------- Helper Functions ----------

def format_intake_form(form: dict) -> dict:
    """Format intake form for response - matches sample.json structure"""
    form["_id"] = str(form["_id"])
    
    # Format timestamps
    if "createdAt" in form and isinstance(form["createdAt"], datetime):
        form["createdAt"] = form["createdAt"].isoformat() + "Z"
    if "updatedAt" in form and isinstance(form["updatedAt"], datetime):
        form["updatedAt"] = form["updatedAt"].isoformat() + "Z"
    
    # Format documents to include url, fileName, uploadedAt, and type
    if "documents" in form:
        form["documents"] = [
            {
                "url": doc.get("url", ""),
                "fileName": doc.get("fileName", ""),
                "uploadedAt": doc.get("uploadedAt", ""),
                "type": doc.get("type", "clinical_notes")
            }
            for doc in form["documents"]
        ]
    
    return form

# ---------- URL Sanitization Helper ----------
def sanitize_s3_url(url: str) -> str:
    """Strip query/fragment so URL ends cleanly at the file path/filename."""
    try:
        parts = urlsplit(url)
        # Drop query and fragment
        clean = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
        return clean
    except Exception:
        return url

# ---------- INTAKE FORM ENDPOINTS ----------

@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_intake_form(
    form_data: IntakeFormCreate,
    current_user: dict = Depends(authMiddleware)
):
    """
    Submit patient intake form
    - Stores data in MongoDB in sample.json format
    - Associates with logged-in patient
    - Creates patient record in patients collection matching Mongo_connect.py structure
    - Documents already uploaded to S3 via /upload endpoint
    """
    try:
        # Verify pseudonym_id matches authenticated user
        if form_data.pseudonym_id != current_user.get("pseudonym_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pseudonym ID mismatch"
            )
        
        # Check if patient already exists
        existing_patient = patients_collection.find_one({"pseudonym_id": form_data.pseudonym_id})
        
        if not existing_patient:
            # Create patient record matching Mongo_connect.py structure with all fields initialized
            patient_doc = {
                "pseudonym_id": form_data.pseudonym_id,
                "visits": [],
                "patient_summary": "",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "source_system": "",
                "assigned_doctor": ""
            }
            patients_collection.insert_one(patient_doc)
            print(f"✅ Created patient record for {form_data.pseudonym_id}")
        else:
            print(f"ℹ️ Patient record already exists for {form_data.pseudonym_id}")
        
        # Create intake form document
        intake_doc = {
            "patient": form_data.pseudonym_id,
            "fullName": form_data.fullName,
            "age": form_data.age,
            "phone": form_data.phone,
            "country": form_data.country,
            "budget": form_data.budget,
            "hasSightseeing": form_data.hasSightseeing,
            "sightseeingDays": form_data.sightseeingDays if form_data.hasSightseeing == "yes" else None,
            "sightseeingPrefs": form_data.sightseeingPrefs if form_data.hasSightseeing == "yes" else [],
            "notes": form_data.notes,
            "documents": [
                {
                    "url": sanitize_s3_url(doc.url or ""),
                    "fileName": doc.fileName,
                    "uploadedAt": doc.uploadedAt,
                    "type": doc.type or "clinical_notes"
                }
                for doc in form_data.documents
            ],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = intake_collection.insert_one(intake_doc)
        
        # Get the inserted document
        inserted_doc = intake_collection.find_one({"_id": result.inserted_id})
        
        print(f"✅ Intake form submitted successfully for patient {form_data.pseudonym_id}: {result.inserted_id}")
        
        return {
            "success": True,
            "message": "Intake form submitted successfully",
            "formId": str(result.inserted_id),
            "data": format_intake_form(inserted_doc)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error submitting intake form: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit intake form: {str(e)}"
        )

@router.get("/forms")
async def get_intake_forms(
    status: Optional[str] = None,
    country: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(authMiddleware)
):
    """
    Get intake forms with filtering
    - Patients see only their forms
    - Doctors/Admins see all forms
    """
    query = {}
    
    # Role-based filtering
    if current_user.get("role") == "patient":
        query["patient"] = current_user.get("pseudonym_id")
    
    # Additional filters
    if status:
        query["status"] = status
    if country:
        query["country"] = country
    
    try:
        forms = list(
            intake_collection
            .find(query)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )
        
        formatted_forms = [format_intake_form(form) for form in forms]
        
        return {
            "success": True,
            "count": len(formatted_forms),
            "forms": formatted_forms
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch intake forms: {str(e)}"
        )

@router.get("/form/{pseudonym_id}")
async def get_intake_form_by_id(
    pseudonym_id: str,
):
    
    try:
        form = intake_collection.find_one({"patient": pseudonym_id})
        
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intake form not found"
            )
                
        return {
            "success": True,
            "form": format_intake_form(form)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid form ID: {str(e)}"
        )
    
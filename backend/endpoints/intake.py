from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional
import os
import secrets
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
    pseudonym_id: Optional[str] = None  # Optional - will be auto-generated for doctor-created patients
    fullName: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=1, le=120)
    documents: List[DocumentInfo] = []
    
# ---------- Helper Functions ----------

def format_intake_form(form: dict) -> dict:
    """Format intake form for response - matches sample.json structure"""
    form["_id"] = str(form["_id"])
    
    # Format timestamps
    if "createdAt" in form and isinstance(form["createdAt"], datetime):
        form["createdAt"] = form["createdAt"].isoformat() + "Z"
    if "updatedAt" in form and isinstance(form["updatedAt"], datetime):
        form["updatedAt"] = form["updatedAt"].isoformat() + "Z"
    
    # Format documents to include url, fileName, uploadedAt, type, and s3 metadata
    if "documents" in form:
        form["documents"] = [
            {
                "url": doc.get("url", ""),
                "fileName": doc.get("fileName", ""),
                "uploadedAt": doc.get("uploadedAt", ""),
                "type": doc.get("type", "clinical_notes"),
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

# ---------- Pseudonym ID Generator ----------
def generate_patient_pseudonym_id() -> str:
    """Generate a unique patient pseudonym ID in format P-XXXX-XXXX"""
    part1 = secrets.token_hex(2).upper()  # 4 hex characters
    part2 = secrets.token_hex(2).upper()  # 4 hex characters
    return f"P-{part1}-{part2}"

# ---------- INTAKE FORM ENDPOINTS ----------

@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_intake_form(
    form_data: IntakeFormCreate,
    current_user: dict = Depends(authMiddleware)
):
    """
    Submit patient intake form
    - If submitted by a doctor/admin: Creates new patient with auto-generated pseudonym ID
    - If submitted by a patient: Uses their existing pseudonym ID
    - Stores data in MongoDB and creates patient record in patients collection
    - Documents already uploaded to S3 via /upload endpoint
    """
    try:
        user_role = current_user.get("role")
        patient_pseudonym_id = None
        assigned_doctor = None
        
        # Determine patient pseudonym ID based on who is submitting
        if user_role in ["doctor", "admin"]:
            patient_pseudonym_id = generate_patient_pseudonym_id()
            print(f"✅ Generated new patient pseudonym ID: {patient_pseudonym_id}")
            
            # Assign the doctor to this patient using their email
            assigned_doctor = current_user.get("email")
            
        elif user_role == "patient":
            # Patient submitting their own form
            if form_data.pseudonym_id and form_data.pseudonym_id != current_user.get("pseudonym_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Pseudonym ID mismatch - patients can only submit their own forms"
                )
            patient_pseudonym_id = current_user.get("pseudonym_id")
            assigned_doctor = ""  # No doctor assigned yet
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        # Check if patient already exists
        existing_patient = patients_collection.find_one({"pseudonym_id": patient_pseudonym_id})
        
        if not existing_patient:
            # Create patient record matching Mongo_connect.py structure
            patient_doc = {
                "pseudonym_id": patient_pseudonym_id,
                "visits": [],
                "patient_summary": "",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "source_system": "intake_form",
                "assigned_doctor": assigned_doctor
            }
            patients_collection.insert_one(patient_doc)
            print(f"✅ Created patient record for {patient_pseudonym_id} (assigned to: {assigned_doctor or 'none'})")
        else:
            # Update assigned doctor if doctor is creating the form
            if assigned_doctor and not existing_patient.get("assigned_doctor"):
                patients_collection.update_one(
                    {"pseudonym_id": patient_pseudonym_id},
                    {"$set": {"assigned_doctor": assigned_doctor, "updated_at": datetime.utcnow()}}
                )
                print(f"✅ Updated patient {patient_pseudonym_id} - assigned doctor: {assigned_doctor}")
            else:
                print(f"ℹ️ Patient record already exists for {patient_pseudonym_id}")
        
        # Create intake form document
        intake_doc = {
            "patient": patient_pseudonym_id,
            "fullName": form_data.fullName,
            "age": form_data.age,
            "documents": [
                {
                    "url": sanitize_s3_url(doc.url or ""),
                    "fileName": doc.fileName,
                    "uploadedAt": doc.uploadedAt,
                    "type": doc.type or "clinical_notes",
                }
                for doc in form_data.documents
            ],
            "assignedDoctor": assigned_doctor,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = intake_collection.insert_one(intake_doc)
        
        # Get the inserted document
        inserted_doc = intake_collection.find_one({"_id": result.inserted_id})
        
        print(f"✅ Intake form submitted successfully for patient {patient_pseudonym_id}: {result.inserted_id}")
        
        return {
            "success": True,
            "message": "Intake form submitted successfully",
            "formId": str(result.inserted_id),
            "pseudonym_id": patient_pseudonym_id,  # Return the patient pseudonym ID
            "assigned_doctor": assigned_doctor,
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
    
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from datetime import datetime
from typing import List, Optional
import os
import dotenv
import boto3
from botocore.exceptions import ClientError
import secrets

dotenv.load_dotenv()

router = APIRouter(prefix="/intake", tags=["Intake Form"])

# ---------- Configuration ----------
client = MongoClient(os.getenv("MONGODB_KEY"))
db = client.get_database("medicotourism")
patients_collection = db.get_collection("patients")

# AWS S3 Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1")
)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# ---------- Models ----------
class DocumentSchema(BaseModel):
    label: str
    url: str
    fileName: str
    uploadedAt: datetime

class IntakeFormRequest(BaseModel):
    patient: Optional[str] = None  # User ID if authenticated
    fullName: str
    age: int
    phone: str
    country: str
    budget: float
    treatmentType: str
    hasSightseeing: str  # "yes" or "no"
    sightseeingDays: Optional[int] = None
    sightseeingPrefs: List[str] = []
    notes: Optional[str] = None
    documents: List[dict] = []  # Will be populated after file upload

# ---------- Utility Functions ----------
def upload_file_to_s3(file: UploadFile, folder: str = "intake-documents") -> str:
    """
    Upload file to S3 and return the public URL
    """
    try:
        # Generate unique filename
        file_extension = file.filename.split('.')[-1]
        unique_filename = f"{folder}/{secrets.token_hex(16)}.{file_extension}"
        
        # Upload file
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={
                'ContentType': file.content_type,
                'ACL': 'public-read'  # Make file publicly accessible
            }
        )
        
        # Generate URL
        file_url = f"https://{S3_BUCKET_NAME}.s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/{unique_filename}"
        return file_url
    
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to S3: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

# ---------- Routes ----------
@router.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload multiple files to S3 and return their URLs
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_documents = []
    
    for file in files:
        # Validate file size (max 10MB)
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail=f"File {file.filename} is too large (max 10MB)")
        
        # Upload to S3
        file_url = upload_file_to_s3(file)
        
        uploaded_documents.append({
            "label": file.filename.split('.')[0],  # Use filename without extension as label
            "url": file_url,
            "fileName": file.filename,
            "uploadedAt": datetime.utcnow().isoformat()
        })
    
    return {
        "success": True,
        "message": "Files uploaded successfully",
        "documents": uploaded_documents
    }

@router.post("/submit")
async def submit_intake_form(data: IntakeFormRequest):
    """
    Submit intake form data to MongoDB
    """
    # Validate required fields
    if not data.fullName or not data.age or not data.phone or not data.country:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Validate age
    if data.age < 1 or data.age > 120:
        raise HTTPException(status_code=400, detail="Invalid age")
    
    # Validate budget
    if data.budget < 0:
        raise HTTPException(status_code=400, detail="Budget cannot be negative")
    
    # Validate sightseeing preferences
    if data.hasSightseeing == "yes" and not data.sightseeingDays:
        raise HTTPException(status_code=400, detail="Sightseeing days required when sightseeing is enabled")
    
    # Create intake form document
    intake_form = {
        "patient": data.patient,
        "fullName": data.fullName,
        "age": data.age,
        "phone": data.phone,
        "country": data.country,
        "budget": data.budget,
        "treatmentType": data.treatmentType,
        "hasSightseeing": data.hasSightseeing,
        "sightseeingDays": data.sightseeingDays if data.hasSightseeing == "yes" else None,
        "sightseeingPrefs": data.sightseeingPrefs if data.hasSightseeing == "yes" else [],
        "notes": data.notes,
        "documents": data.documents,
        "status": "pending",
        "staffNotes": [],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    # Insert into MongoDB
    result = patients_collection.insert_one(intake_form)
    intake_form["id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "message": "Intake form submitted successfully",
        "intakeFormId": str(result.inserted_id),
        "data": {
            "id": intake_form["id"],
            "fullName": intake_form["fullName"],
            "email": intake_form.get("email"),
            "treatmentType": intake_form["treatmentType"],
            "status": intake_form["status"],
            "createdAt": intake_form["createdAt"].isoformat()
        }
    }

@router.get("/forms")
async def get_all_intake_forms(status: Optional[str] = None, limit: int = 50, skip: int = 0):
    """
    Get all intake forms with optional filtering
    """
    query = {}
    if status:
        query["status"] = status
    
    forms = list(patients_collection.find(query).sort("createdAt", -1).skip(skip).limit(limit))
    
    # Convert ObjectId to string
    for form in forms:
        form["id"] = str(form["_id"])
        del form["_id"]
        if "createdAt" in form:
            form["createdAt"] = form["createdAt"].isoformat()
        if "updatedAt" in form:
            form["updatedAt"] = form["updatedAt"].isoformat()
    
    return {
        "success": True,
        "count": len(forms),
        "forms": forms
    }

@router.get("/forms/{form_id}")
async def get_intake_form_by_id(form_id: str):
    """
    Get a specific intake form by ID
    """
    from bson import ObjectId
    
    try:
        form = patients_collection.find_one({"_id": ObjectId(form_id)})
        
        if not form:
            raise HTTPException(status_code=404, detail="Intake form not found")
        
        form["id"] = str(form["_id"])
        del form["_id"]
        if "createdAt" in form:
            form["createdAt"] = form["createdAt"].isoformat()
        if "updatedAt" in form:
            form["updatedAt"] = form["updatedAt"].isoformat()
        
        return {
            "success": True,
            "form": form
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid form ID: {str(e)}")

@router.patch("/forms/{form_id}/status")
async def update_intake_form_status(form_id: str, status: str):
    """
    Update intake form status (pending, in_review, contacted, completed, cancelled)
    """
    from bson import ObjectId
    
    valid_statuses = ["pending", "in_review", "contacted", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    try:
        result = patients_collection.update_one(
            {"_id": ObjectId(form_id)},
            {
                "$set": {
                    "status": status,
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Intake form not found")
        
        return {
            "success": True,
            "message": f"Status updated to {status}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating status: {str(e)}")

@router.delete("/forms/{form_id}")
async def delete_intake_form(form_id: str):
    """
    Delete an intake form
    """
    from bson import ObjectId
    
    try:
        result = patients_collection.delete_one({"_id": ObjectId(form_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Intake form not found")
        
        return {
            "success": True,
            "message": "Intake form deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting form: {str(e)}")
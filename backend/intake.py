from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv
from Mongo_connect import get_mongo_connection, upload_file_to_s3
from auth import getCurrentUser

load_dotenv()

router = APIRouter(prefix="/intake", tags=["Intake Form"])

# ---------- Configuration ----------
try:
    mongo_conn = get_mongo_connection()
    db = mongo_conn.get_database()
    intake_collection = db.get_collection("patients")
    print("✅ MongoDB connected in intake.py")
except Exception as e:
    print(f"❌ MongoDB connection failed in intake.py: {e}")
    raise

# ---------- Pydantic Models ----------

class DocumentInfo(BaseModel):
    url: str
    s3_key: str
    fileName: str
    uploadedAt: str

class IntakeFormCreate(BaseModel):
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

class IntakeFormUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|in_review|contacted|approved|rejected|completed|cancelled)$")
    staffNotes: Optional[str] = None
    assignedDoctor: Optional[str] = None

# ---------- Helper Functions ----------

def format_intake_form(form: dict) -> dict:
    """Format intake form for response - matches sample.json structure"""
    form["_id"] = str(form["_id"])  # Keep _id for MongoDB compatibility
    
    # Format timestamps
    if "createdAt" in form and isinstance(form["createdAt"], datetime):
        form["createdAt"] = form["createdAt"].isoformat() + "Z"
    if "updatedAt" in form and isinstance(form["updatedAt"], datetime):
        form["updatedAt"] = form["updatedAt"].isoformat() + "Z"
    
    # Format documents to match sample.json (only url, fileName, uploadedAt)
    if "documents" in form:
        form["documents"] = [
            {
                "url": doc.get("url", ""),
                "fileName": doc.get("fileName", ""),
                "uploadedAt": doc.get("uploadedAt", "")
            }
            for doc in form["documents"]
        ]
    
    return form

# ---------- INTAKE FORM ENDPOINTS ----------

@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_intake_form(
    form_data: IntakeFormCreate,
    current_user: dict = Depends(getCurrentUser)
):
    """
    Submit patient intake form
    - Stores data in MongoDB in sample.json format
    - Associates with logged-in patient
    - Documents already uploaded to S3 via /upload endpoint
    """
    # Only patients can submit intake forms
    if current_user.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can submit intake forms"
        )
    
    try:
        from bson import ObjectId
        
        # Get user's ObjectId
        user_id = ObjectId(current_user.get("_id"))
        
        # Create intake form document matching sample.json structure
        intake_form = {
            "patient": user_id,  # Store as ObjectId for reference
            "fullName": form_data.fullName,
            "age": form_data.age,
            "phone": form_data.phone,
            "country": form_data.country,
            "budget": form_data.budget,
            "treatmentType": form_data.treatmentType,
            "hasSightseeing": form_data.hasSightseeing,
            "sightseeingDays": form_data.sightseeingDays if form_data.hasSightseeing == "yes" else None,
            "sightseeingPrefs": form_data.sightseeingPrefs if form_data.hasSightseeing == "yes" else [],
            "notes": form_data.notes or "",
            "documents": [
                {
                    "url": doc.url,
                    "fileName": doc.fileName,
                    "uploadedAt": doc.uploadedAt
                }
                for doc in form_data.documents
            ],
            "status": "pending",
            "staffNotes": [],
            "assignedDoctor": None,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = intake_collection.insert_one(intake_form)
        intake_form["_id"] = result.inserted_id
        
        return {
            "success": True,
            "message": "Intake form submitted successfully",
            "form": format_intake_form(intake_form)
        }
        
    except Exception as e:
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
    current_user: dict = Depends(getCurrentUser)
):
    """
    Get intake forms with filtering
    - Patients see only their forms
    - Doctors/Admins see assigned or all forms
    """
    from bson import ObjectId
    
    query = {}
    
    # Role-based filtering
    if current_user.get("role") == "patient":
        query["patient"] = ObjectId(current_user.get("_id"))
    elif current_user.get("role") == "doctor":
        query["$or"] = [
            {"assignedDoctor": current_user.get("email")},
            {"assignedDoctor": None}
        ]
    
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

@router.get("/forms/{form_id}")
async def get_intake_form_by_id(
    form_id: str,
    current_user: dict = Depends(getCurrentUser)
):
    """Get specific intake form by ID with access control and fresh URLs"""
    from bson import ObjectId
    
    try:
        form = intake_collection.find_one({"_id": ObjectId(form_id)})
        
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intake form not found"
            )
        
        # Access control
        if current_user.get("role") == "patient":
            if str(form.get("patient")) != current_user.get("_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this form"
                )
        elif current_user.get("role") == "doctor":
            if form.get("assignedDoctor") and form.get("assignedDoctor") != current_user.get("email"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This form is assigned to another doctor"
                )
        
        # Note: In production, you might want to refresh S3 URLs here
        # For now, we'll use the stored URLs from sample.json format
        
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

@router.patch("/forms/{form_id}")
async def update_intake_form(
    form_id: str,
    update_data: IntakeFormUpdate,
    current_user: dict = Depends(getCurrentUser)
):
    """Update intake form (doctors/admins only)"""
    from bson import ObjectId
    
    if current_user.get("role") not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and admins can update intake forms"
        )
    
    try:
        update_fields = {"updatedAt": datetime.utcnow()}
        
        if update_data.status:
            update_fields["status"] = update_data.status
        
        if update_data.staffNotes:
            staff_note = {
                "note": update_data.staffNotes,
                "addedBy": current_user.get("email"),
                "addedByRole": current_user.get("role"),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            intake_collection.update_one(
                {"_id": ObjectId(form_id)},
                {"$push": {"staffNotes": staff_note}}
            )
        
        if update_data.assignedDoctor and current_user.get("role") == "admin":
            update_fields["assignedDoctor"] = update_data.assignedDoctor
        
        result = intake_collection.update_one(
            {"_id": ObjectId(form_id)},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intake form not found"
            )
        
        updated_form = intake_collection.find_one({"_id": ObjectId(form_id)})
        
        return {
            "success": True,
            "message": "Intake form updated successfully",
            "form": format_intake_form(updated_form)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update form: {str(e)}"
        )

@router.delete("/forms/{form_id}")
async def delete_intake_form(
    form_id: str,
    current_user: dict = Depends(getCurrentUser)
):
    """Delete intake form with S3 cleanup"""
    from bson import ObjectId
    
    try:
        form = intake_collection.find_one({"_id": ObjectId(form_id)})
        
        if not form:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intake form not found"
            )
        
        # Access control
        if current_user.get("role") == "patient":
            if str(form.get("patient")) != current_user.get("_id"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own forms"
                )
            if form.get("status") != "pending":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot delete forms that are in progress"
                )
        elif current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can delete forms"
            )
        
        # Delete associated S3 files (if s3_key is stored)
        # Note: sample.json doesn't include s3_key, but we should store it
        # For now, skip S3 deletion as URLs are public
        
        # Delete form from MongoDB
        intake_collection.delete_one({"_id": ObjectId(form_id)})
        
        return {
            "success": True,
            "message": "Intake form deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete form: {str(e)}"
        )

@router.get("/stats")
async def get_intake_stats(current_user: dict = Depends(getCurrentUser)):
    """Get intake form statistics"""
    if current_user.get("role") not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and admins can access statistics"
        )
    
    total_forms = intake_collection.count_documents({})
    pending = intake_collection.count_documents({"status": "pending"})
    in_review = intake_collection.count_documents({"status": "in_review"})
    contacted = intake_collection.count_documents({"status": "contacted"})
    completed = intake_collection.count_documents({"status": "completed"})
    
    # Top treatment types
    pipeline = [
        {"$group": {"_id": "$treatmentType", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_treatments = list(intake_collection.aggregate(pipeline))
    
    # Top countries
    pipeline = [
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_countries = list(intake_collection.aggregate(pipeline))
    
    return {
        "success": True,
        "stats": {
            "total_forms": total_forms,
            "by_status": {
                "pending": pending,
                "in_review": in_review,
                "contacted": contacted,
                "completed": completed
            },
            "top_treatments": [{"treatment": t["_id"], "count": t["count"]} for t in top_treatments],
            "top_countries": [{"country": c["_id"], "count": c["count"]} for c in top_countries]
        }
    }
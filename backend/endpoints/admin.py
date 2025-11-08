from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .Mongo_connect import get_mongo_connection
from .auth import authMiddleware

router = APIRouter(prefix="/admin", tags=["Admin"])

# ---------- Configuration ----------
try:
    mongo_conn = get_mongo_connection()
    db = mongo_conn.get_database()
    users_collection = db.get_collection("users")
    patients_collection = db.get_collection("patients")
    print("✅ MongoDB connected in admin.py")
except Exception as e:
    print(f"❌ MongoDB connection failed in admin.py: {e}")
    raise

# ---------- Pydantic Models ----------

class AssignDoctorRequest(BaseModel):
    patient_pseudonym_id: str
    doctor_email: str

# ---------- ADMIN ENDPOINTS ----------
 
@router.get("/pending-doctors")
async def get_pending_doctors(current_user: dict = Depends(authMiddleware)):
    """Get all doctors with pending verification"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    try:
        pending_doctors = list(
            users_collection.find({
                "role": "doctor",
                "verified": False
            })
        )
        
        formatted_doctors = []
        for doc in pending_doctors:
            formatted_doctors.append({
                "id": str(doc["_id"]),
                "username": doc["username"],
                "email": doc["email"],
                "verified": doc["verified"],
                "created_at": doc.get("created_at")
            })
        
        return {
            "success": True,
            "count": len(formatted_doctors),
            "doctors": formatted_doctors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending doctors: {str(e)}"
        )

@router.get("/unassigned-patients")
async def get_unassigned_patients(current_user: dict = Depends(authMiddleware)):
    """Get all patients without assigned doctor"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    try:
        # Debug: Check total documents first
        total_count = patients_collection.count_documents({})
        print(f"🔍 Total documents in patients: {total_count}")
        
        # Debug: Check all assigned_doctor values
        all_patients = list(patients_collection.find({}, {"pseudonym_id": 1, "assigned_doctor": 1}))
        print(f"🔍 All patients with assigned_doctor field:")
        for p in all_patients:
            print(f"   - {p.get('pseudonym_id')}: assigned_doctor = {repr(p.get('assigned_doctor'))}")
        
        # Query for unassigned patients
        query = {
            "$or": [
                {"assigned_doctor": None},
                {"assigned_doctor": {"$exists": False}},
                {"assigned_doctor": ""}
            ]
        }
        print(f"🔍 Query: {query}")
        
        unassigned_patients = list(patients_collection.find(query))
        print(f"🔍 Found {len(unassigned_patients)} unassigned patients")
        
        formatted_patients = []
        for patient in unassigned_patients:
            print(f"🔍 Processing patient: {patient.get('pseudonym_id')}")
            formatted_patients.append({
                "id": str(patient["_id"]),
                "pseudonym_id": patient["pseudonym_id"],
                "patient_summary": patient.get("patient_summary", "No summary available"),
                "created_at": patient.get("created_at"),
                "assigned_doctor": patient.get("assigned_doctor")
            })
        
        return {
            "success": True,
            "count": len(formatted_patients),
            "patients": formatted_patients
        }
    except Exception as e:
        print(f"❌ Error in get_unassigned_patients: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unassigned patients: {str(e)}"
        )

@router.get("/verified-doctors")
async def get_verified_doctors(current_user: dict = Depends(authMiddleware)):
    """Get all verified doctors"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    
    try:
        verified_doctors = list(
            users_collection.find({
                "role": "doctor",
                "verified": True
            })
        )
        
        formatted_doctors = []
        for doc in verified_doctors:
            formatted_doctors.append({
                "id": str(doc["_id"]),
                "username": doc["username"],
                "email": doc["email"]
            })
        
        return {
            "success": True,
            "count": len(formatted_doctors),
            "doctors": formatted_doctors
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch verified doctors: {str(e)}"
        )

@router.post("/assign-doctor")
async def assign_doctor(
    request: AssignDoctorRequest,
    current_user: dict = Depends(authMiddleware)
):
    """Assign doctor to patient"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign doctors"
        )
    
    try:
        # Verify doctor exists and is verified
        doctor = users_collection.find_one({
            "email": request.doctor_email,
            "role": "doctor",
            "verified": True
        })
        
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verified doctor not found"
            )
        
        # Update patient's assigned doctor
        result = patients_collection.update_one(
            {"pseudonym_id": request.patient_pseudonym_id},
            {
                "$set": {
                    "assigned_doctor": request.doctor_email,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )
        
        print(f"✅ Assigned doctor {request.doctor_email} to patient {request.patient_pseudonym_id}")
        
        return {
            "success": True,
            "message": f"Doctor {request.doctor_email} assigned to patient {request.patient_pseudonym_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign doctor: {str(e)}"
        )

@router.post("/verify-doctor/{doctor_id}")
async def verify_doctor(
    doctor_id: str,
    current_user: dict = Depends(authMiddleware)
):
    """Verify a doctor"""
    from bson import ObjectId
    
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can verify doctors"
        )
    
    try:
        result = users_collection.update_one(
            {"_id": ObjectId(doctor_id), "role": "doctor"},
            {"$set": {"verified": True}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        print(f"✅ Verified doctor with ID: {doctor_id}")
        
        return {
            "success": True,
            "message": "Doctor verified successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify doctor: {str(e)}"
        )

# ---------- DOCTOR ENDPOINTS ----------

@router.get("/doctor/my-patients")
async def get_doctor_patients(current_user: dict = Depends(authMiddleware)):
    """Get all patients assigned to the logged-in doctor"""
    if current_user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this endpoint"
        )
    
    try:
        doctor_email = current_user.get("email")
        
        # Query for patients assigned to this doctor
        assigned_patients = list(
            patients_collection.find({
                "assigned_doctor": doctor_email
            })
        )
        
        print(f"🔍 Doctor {doctor_email} has {len(assigned_patients)} assigned patients")
        
        formatted_patients = []
        for patient in assigned_patients:
            formatted_patients.append({
                "id": str(patient["_id"]),
                "pseudonym_id": patient["pseudonym_id"],
                "patient_summary": patient.get("patient_summary", "No summary available"),
                "created_at": patient.get("created_at"),
                "updated_at": patient.get("updated_at"),
                "assigned_doctor": patient.get("assigned_doctor"),
                "visits": patient.get("visits", [])
            })
        
        return {
            "success": True,
            "count": len(formatted_patients),
            "patients": formatted_patients
        }
    except Exception as e:
        print(f"❌ Error in get_doctor_patients: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch assigned patients: {str(e)}"
        )

@router.get("/doctor/patient/{pseudonym_id}")
async def get_patient_details(
    pseudonym_id: str,
    current_user: dict = Depends(authMiddleware)
):
    """Get detailed information about a specific patient assigned to the doctor"""
    if current_user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this endpoint"
        )
    
    try:
        doctor_email = current_user.get("email")
        
        # Find patient and verify it's assigned to this doctor
        patient = patients_collection.find_one({
            "pseudonym_id": pseudonym_id,
            "assigned_doctor": doctor_email
        })
        
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found or not assigned to you"
            )
        
        return {
            "success": True,
            "patient": {
                "id": str(patient["_id"]),
                "pseudonym_id": patient["pseudonym_id"],
                "patient_summary": patient.get("patient_summary", ""),
                "created_at": patient.get("created_at"),
                "updated_at": patient.get("updated_at"),
                "assigned_doctor": patient.get("assigned_doctor"),
                "visits": patient.get("visits", []),
                "source_system": patient.get("source_system", "")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_patient_details: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch patient details: {str(e)}"
        )
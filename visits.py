# main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, validator
import re

from Connections.Mongo_connect import get_mongo_connection
from Connections.patient_workflow import PatientWorkflow
from Connections.llm_service import LLMService

app = FastAPI(
    title="Healthcare AI POC API",
    description="Medical assistance system for healthcare providers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
mongo = get_mongo_connection()
workflow = PatientWorkflow()
llm_service = LLMService()


# ==================== PYDANTIC MODELS FOR VALIDATION ====================

class PatientIDValidator:
    """Validator for patient pseudonym ID format"""
    @staticmethod
    def validate(v: str) -> str:
        if not re.match(r'^P-[A-Z0-9]{4}-[A-Z0-9]{4}$', v):
            raise ValueError('Patient ID must be in format P-XXXX-XXXX')
        return v


class VisitTypeValidator:
    """Validator for visit type"""
    @staticmethod
    def validate(v: str) -> str:
        allowed = ['initial', 'follow_up', 'emergency', 'routine_checkup']
        if v not in allowed:
            raise ValueError(f'Visit type must be one of: {allowed}')
        return v


# ==================== PATIENT ENDPOINTS ====================

@app.post("/api/patients/create")
async def create_patient(
    patient_id: str = Form(...),
    doctor_id: str = Form(...),
    chief_complaint: str = Form("Initial consultation"),
    visit_type: str = Form("initial")
):
    """Create new patient with initial visit"""
    try:
        # Validate patient ID format
        PatientIDValidator.validate(patient_id)
        
        # Validate visit type
        VisitTypeValidator.validate(visit_type)
        
        visit_timestamp = mongo.create_patient_record(
            pseudonym_id=patient_id,
            clinician_id=doctor_id,
            chief_complaint=chief_complaint,
            visit_type=visit_type
        )
        
        if not visit_timestamp:
            raise HTTPException(status_code=500, detail="Failed to create patient")
        
        return {
            "success": True,
            "patient_id": patient_id,
            "visit_timestamp": visit_timestamp.isoformat(),
            "message": "Patient created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get complete patient record"""
    try:
        PatientIDValidator.validate(patient_id)
        
        patient = mongo.get_patient_by_pseudonym(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        patient["_id"] = str(patient["_id"])
        return {"success": True, "data": patient}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients/{patient_id}/history")
async def get_history(patient_id: str):
    """Get patient history for LLM context"""
    try:
        PatientIDValidator.validate(patient_id)
        
        history = mongo.get_patient_history_for_llm(patient_id)
        if not history:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {"success": True, "data": history}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== VISIT ENDPOINTS ====================

@app.post("/api/patients/{patient_id}/visits/new")
async def create_visit(
    patient_id: str,
    doctor_id: str = Form(...),
    chief_complaint: str = Form(""),
    visit_type: str = Form("follow_up")
):
    """Create new visit"""
    try:
        PatientIDValidator.validate(patient_id)
        VisitTypeValidator.validate(visit_type)
        
        visit_timestamp = mongo.add_new_visit(
            pseudonym_id=patient_id,
            clinician_id=doctor_id,
            chief_complaint=chief_complaint,
            visit_type=visit_type
        )
        
        if not visit_timestamp:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return {
            "success": True,
            "visit_timestamp": visit_timestamp.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients/{patient_id}/visits/latest")
async def get_latest_visit(patient_id: str):
    """Get most recent visit"""
    try:
        PatientIDValidator.validate(patient_id)
        visit = mongo.get_latest_visit(patient_id)
        if not visit:
            raise HTTPException(status_code=404, detail="No visits found")
        return {"success": True, "data": visit}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== FILE UPLOAD ====================

@app.post("/api/upload-patient-file")
async def upload_file(
    patient_id: str = Form(...),
    file_type: str = Form(...),
    doctor_id: str = Form(...),
    chief_complaint: str = Form(""),
    file: UploadFile = File(...)
):
    """Smart file upload - auto-manages visits"""
    try:
        # Validate inputs
        PatientIDValidator.validate(patient_id)
        
        valid_types = ["prescription", "lab_report", "imaging", "clinical_notes"]
        if file_type not in valid_types:
            raise HTTPException(400, f"Invalid file_type. Must be one of: {valid_types}")
        
        # Process upload
        result = await workflow.doctor_uploads_file(
            doctor_id=doctor_id,
            patient_pseudonym=patient_id,
            uploaded_file=file,
            file_type=file_type,
            chief_complaint=chief_complaint
        )
        
        if not result['success']:
            error_type = result.get('error_type', 'unknown_error')
            if error_type == 'validation_error':
                raise HTTPException(400, result['error'])
            else:
                raise HTTPException(500, result['error'])
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ==================== FILE ACCESS (SECURE) ====================

@app.get("/api/files/download/{patient_id}/{ingest_id}")
async def download_file(
    patient_id: str,
    ingest_id: str,
    doctor_id: Optional[str] = None  # For access control
):
    """
    Generate temporary download URL for a file.
    This endpoint creates a fresh presigned URL every time it's called.
    
    Args:
        patient_id: Patient pseudonym ID (P-XXXX-XXXX format)
        ingest_id: Unique file identifier
        doctor_id: Optional doctor ID for access control
    
    Returns:
        Download URL valid for 1 hour, file metadata
    """
    try:
        # Validate patient ID
        PatientIDValidator.validate(patient_id)
        
        # Get patient record
        patient = mongo.get_patient_by_pseudonym(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Find the ingest across all visits
        ingest_data = None
        visit_with_file = None
        
        for visit in patient.get('visits', []):
            for ingest in visit.get('ingests', []):
                if ingest['ingest_id'] == ingest_id:
                    ingest_data = ingest
                    visit_with_file = visit
                    break
            if ingest_data:
                break
        
        if not ingest_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Optional: Add access control check
        if doctor_id and visit_with_file.get('clinician_id') != doctor_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only access files from your own visits")
        
        # Generate fresh presigned URL (valid for 1 hour)
        presigned_url = mongo.generate_presigned_url(
            ingest_data['s3_key'],
            expiration=3600  # 1 hour
        )
        
        if not presigned_url:
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
        
        return {
            "success": True,
            "download_url": presigned_url,
            "expires_in_seconds": 3600,
            "file_info": {
                "ingest_id": ingest_data['ingest_id'],
                "filename": ingest_data['original_filename'],
                "size": ingest_data['file_size'],
                "type": ingest_data['type'],
                "content_type": ingest_data['content_type'],
                "upload_timestamp": ingest_data['upload_timestamp'].isoformat(),
                "processing_status": ingest_data['processing_status']
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/visits/{patient_id}/{visit_timestamp}/files")
async def get_visit_files(
    patient_id: str, 
    visit_timestamp: str,
    doctor_id: Optional[str] = None  # For access control
):
    """
    Get all files for a specific visit with download URLs.
    
    Args:
        patient_id: Patient pseudonym ID (P-XXXX-XXXX format)
        visit_timestamp: Visit timestamp in ISO format
        doctor_id: Optional doctor ID for access control
    
    Returns:
        List of files with download URLs (each valid for 1 hour)
    """
    try:
        PatientIDValidator.validate(patient_id)
        
        # Parse timestamp
        try:
            visit_ts = datetime.fromisoformat(visit_timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")
        
        patient = mongo.get_patient_by_pseudonym(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Find the specific visit
        visit = next(
            (v for v in patient['visits'] if v['visit_timestamp'] == visit_ts),
            None
        )
        
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        # Optional: Add access control check
        if doctor_id and visit.get('clinician_id') != doctor_id:
            raise HTTPException(status_code=403, detail="Access denied: You can only access your own visits")
        
        # Generate presigned URLs for all files in this visit
        files = []
        for ingest in visit.get('ingests', []):
            download_url = mongo.generate_presigned_url(
                ingest['s3_key'],
                expiration=3600
            )
            
            if not download_url:
                # Log error but continue with other files
                download_url = None
            
            files.append({
                "ingest_id": ingest['ingest_id'],
                "type": ingest['type'],
                "filename": ingest['original_filename'],
                "size": ingest['file_size'],
                "content_type": ingest['content_type'],
                "upload_timestamp": ingest['upload_timestamp'].isoformat(),
                "processing_status": ingest['processing_status'],
                "download_url": download_url,  # Fresh URL, expires in 1 hour
                "expires_in_seconds": 3600 if download_url else None
            })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "visit_timestamp": visit_timestamp,
            "visit_type": visit.get('visit_type'),
            "chief_complaint": visit.get('chief_complaint'),
            "clinician_id": visit.get('clinician_id'),
            "files": files,
            "total_files": len(files)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ==================== AI SUMMARIES ====================

@app.post("/api/visits/generate-summary")
async def generate_summary(
    patient_id: str = Form(...),
    visit_timestamp: str = Form(...)
):
    """Generate AI summary for visit"""
    try:
        PatientIDValidator.validate(patient_id)
        
        visit_ts = datetime.fromisoformat(visit_timestamp.replace('Z', '+00:00'))
        
        summary = await llm_service.generate_visit_summary(patient_id, visit_ts)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Visit not found or generation failed")
        
        return {"success": True, "summary": summary}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/patients/{patient_id}/generate-overall-summary")
async def generate_patient_summary(patient_id: str):
    """Generate overall patient summary from all visits"""
    try:
        PatientIDValidator.validate(patient_id)
        
        summary = await llm_service.generate_patient_summary(patient_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Patient not found or generation failed")
        
        return {"success": True, "summary": summary}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== DOCTOR REVIEW ====================

@app.get("/api/doctor/pending-reviews")
async def get_pending(doctor_id: Optional[str] = None):
    """Get visits pending review"""
    pending = mongo.get_visits_pending_review(doctor_id)
    return {"success": True, "count": len(pending), "visits": pending}


@app.put("/api/visits/doctor-notes")
async def add_notes(
    patient_id: str = Form(...),
    visit_timestamp: str = Form(...),
    doctor_notes: str = Form(...),
    approve: bool = Form(True)
):
    """Doctor adds notes"""
    try:
        PatientIDValidator.validate(patient_id)
        
        visit_ts = datetime.fromisoformat(visit_timestamp.replace('Z', '+00:00'))
        
        success = mongo.update_doctor_notes(
            pseudonym_id=patient_id,
            visit_timestamp=visit_ts,
            doctor_notes=doctor_notes,
            mark_reviewed=approve
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return {"success": True, "visit_completed": approve}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== UTILITY ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Healthcare AI POC",
        "mongodb_connected": mongo.is_connected,
        "s3_configured": mongo.s3_client is not None
    }


@app.get("/api/stats")
async def get_stats():
    """System statistics"""
    try:
        patients_collection = mongo.get_collection('patients')
        total_patients = patients_collection.count_documents({})
        
        pipeline = [
            {"$project": {"visit_count": {"$size": "$visits"}}},
            {"$group": {"_id": None, "total_visits": {"$sum": "$visit_count"}}}
        ]
        
        visit_stats = list(patients_collection.aggregate(pipeline))
        total_visits = visit_stats[0]['total_visits'] if visit_stats else 0
        pending = mongo.get_visits_pending_review()
        
        return {
            "success": True,
            "stats": {
                "total_patients": total_patients,
                "total_visits": total_visits,
                "pending_reviews": len(pending),
                "avg_visits_per_patient": round(total_visits / total_patients, 2) if total_patients > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

#  run:        uvicorn main:app --host 0.0.0.0 --port 8000 --reload

"""✅ http://localhost:8000/docs
   (Interactive API documentation - Swagger UI)

✅ http://localhost:8000/redoc
   (Alternative API docs - ReDoc)

✅ http://localhost:8000/api/health
   (Health check endpoint)

✅ http://localhost:8000/api/stats
   (System statistics)"""
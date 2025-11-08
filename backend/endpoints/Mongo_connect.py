import os
from pymongo import MongoClient, ASCENDING, DESCENDING
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
import tempfile

load_dotenv()

router = APIRouter(prefix="/files", tags=["File Management"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBConnection:
    """MongoDB Atlas connection manager with healthcare schema enforcement"""
    
    def __init__(self):
        # Load all config from environment variables
        self.connection_string = os.getenv('MONGODB_KEY')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'medicotourism')
        
        # S3 Configuration
        self.s3_bucket = os.getenv('S3_BUCKET')
        self.s3_region = os.getenv('S3_REGION', 'ap-south-1')
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        # Validate required environment variables
        self._validate_config()
        
        self.client = None
        self.database = None
        self.s3_client = None
        self.is_connected = False

    def _validate_config(self):
        """Validate all required configuration is present"""
        required_vars = {
            'MONGODB_KEY': self.connection_string,
            'S3_BUCKET': self.s3_bucket,
            'AWS_ACCESS_KEY_ID': self.aws_access_key,
            'AWS_SECRET_ACCESS_KEY': self.aws_secret_key
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            error_msg = f"❌ Missing required environment variables: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def connect(self):
        """Establish connection to MongoDB Atlas and S3"""
        try:
            logger.info("🔄 Connecting to MongoDB Atlas...")
            
            # Create MongoDB client
            self.client = MongoClient(self.connection_string)
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB Atlas!")
            
            # Get database
            self.database = self.client[self.db_name]
            self.is_connected = True
            
            # Initialize S3 client with explicit credentials
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.s3_region
                )
                
                # Test S3 connection
                self.s3_client.head_bucket(Bucket=self.s3_bucket)
                logger.info(f"✅ S3 client initialized and bucket '{self.s3_bucket}' accessible")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.error(f"❌ S3 bucket '{self.s3_bucket}' does not exist")
                elif error_code == '403':
                    logger.error(f"❌ Access denied to S3 bucket '{self.s3_bucket}'")
                else:
                    logger.error(f"❌ S3 error: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ S3 client initialization failed: {e}")
                raise
            
            # Enforce schema on connection
            self.enforce_healthcare_schema()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            self.is_connected = False
            raise
    
    def enforce_healthcare_schema(self):
        """Enforce the healthcare schema structure with visit-based tracking"""
        try:
            logger.info("🔧 Enforcing healthcare schema with visit-based structure...")
            
            # Visit-based schema with S3 integration
            schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["pseudonym_id", "visits", "created_at"],
                    "properties": {
                        "pseudonym_id": {
                            "bsonType": "string",
                            "pattern": "^P-[A-Z0-9]{4}-[A-Z0-9]{4}$",
                            "description": "Must be pseudonym format P-XXXX-XXXX"
                        },
                        "visits": {
                            "bsonType": "array",
                            "description": "Array of patient visits ordered by visit_timestamp",
                            "items": {
                                "bsonType": "object",
                                "required": ["visit_timestamp", "ingests"],
                                "properties": {
                                    "visit_timestamp": {
                                        "bsonType": "date",
                                        "description": "Unique timestamp identifying this visit"
                                    },
                                    "visit_type": {
                                        "enum": ["initial", "follow_up", "emergency", "routine_checkup"],
                                        "description": "Type of visit"
                                    },
                                    "chief_complaint": {
                                        "bsonType": "string",
                                        "description": "Primary reason for visit"
                                    },
                                    "ingests": {
                                        "bsonType": "array",
                                        "description": "Files uploaded during this visit",
                                        "items": {
                                            "bsonType": "object",
                                            "required": ["ingest_id", "type", "s3_key"],
                                            "properties": {
                                                "ingest_id": {
                                                    "bsonType": "string",
                                                    "description": "Unique identifier for this file upload"
                                                },
                                                "type": {
                                                    "enum": ["prescription", "lab_report", "imaging", "clinical_notes"],
                                                    "description": "Type of medical document"
                                                },
                                                "s3_key": {
                                                    "bsonType": "string",
                                                    "description": "PERMANENT S3 object key (e.g., patients/P-XXXX-XXXX/visits/20250101_120000/imaging/file.png)"
                                                },
                                                "s3_bucket": {
                                                    "bsonType": "string",
                                                    "description": "S3 bucket name where file is stored"
                                                },
                                                "s3_region": {
                                                    "bsonType": "string",
                                                    "description": "AWS region of the S3 bucket"
                                                },
                                                "upload_timestamp": {
                                                    "bsonType": "date",
                                                    "description": "When the file was uploaded"
                                                },
                                                "original_filename": {
                                                    "bsonType": "string",
                                                    "description": "Original filename from upload"
                                                },
                                                "file_size": {
                                                    "bsonType": "number",
                                                    "description": "File size in bytes"
                                                },
                                                "content_type": {
                                                    "bsonType": "string",
                                                    "description": "MIME type (e.g., image/png, application/pdf)"
                                                },
                                                "processing_status": {
                                                    "enum": ["pending", "processing", "completed", "failed"],
                                                    "description": "AI processing status"
                                                },
                                                "parsed_text": {
                                                    "bsonType": "string",
                                                    "description": "Text extracted from document by AI"
                                                },
                                                "structured_data": {
                                                    "bsonType": "object",
                                                    "description": "Structured information extracted by AI (e.g., lab values, medication names)"
                                                }
                                            }
                                        }
                                    },
                                    "outputs": {
                                        "bsonType": "object",
                                        "description": "AI model outputs for this visit",
                                        "properties": {
                                            "ner_entities": {
                                                "bsonType": "array",
                                                "description": "Named entities extracted from documents"
                                            },
                                            "imaging_findings": {
                                                "bsonType": "array",
                                                "description": "AI findings from medical images"
                                            },
                                            "referral_suggestions": {
                                                "bsonType": "array",
                                                "description": "AI-suggested referrals"
                                            }
                                        }
                                    },
                                    "visit_summary": {
                                        "bsonType": "string",
                                        "description": "LLM-generated summary of this visit"
                                    },
                                    "doctor_notes": {
                                        "bsonType": "string",
                                        "description": "Doctor's manual notes - human-in-the-loop review"
                                    },
                                    "clinician_id": {
                                        "bsonType": "string",
                                        "description": "Doctor/clinician who handled this visit"
                                    },
                                    "status": {
                                        "enum": ["in_progress", "completed", "cancelled"],
                                        "description": "Visit status"
                                    },
                                    "human_review_completed": {
                                        "bsonType": "bool",
                                        "description": "Flag indicating if doctor has reviewed AI outputs"
                                    }
                                }
                            }
                        },
                        "patient_summary": {
                            "bsonType": "string",
                            "description": "Overall patient health summary (LLM-generated from all visits)"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "First visit/record creation date"
                        },
                        "updated_at": {
                            "bsonType": "date",
                            "description": "Last update timestamp"
                        },
                        "source_system": {
                            "bsonType": "string",
                            "description": "System that created this record (e.g., healthcare_ai)"
                        }
                    }
                }
            }
            
            # Try to update existing collection
            try:
                self.database.command({
                    "collMod": "patients",
                    "validator": schema,
                    "validationLevel": "moderate",  # Use "strict" for production
                    "validationAction": "error"
                })
                logger.info("✅ Schema validation updated with S3-integrated visit-based structure")
                
            except Exception as e:
                # If update fails, try to create new collection
                try:
                    self.database.create_collection(
                        "patients",
                        validator=schema,
                        validationLevel="moderate",
                        validationAction="error"
                    )
                    logger.info("✅ New patients collection created with S3-integrated schema")
                except Exception as e2:
                    logger.error(f"❌ Schema enforcement failed: {e2}")
            
            # Create performance indexes
            try:
                patients = self.database.patients
                
                # Core indexes
                patients.create_index([("pseudonym_id", 1)], unique=True)
                patients.create_index([("visits.visit_timestamp", DESCENDING)])
                patients.create_index([("updated_at", DESCENDING)])
                patients.create_index([("created_at", DESCENDING)])
                
                # Visit-specific indexes
                patients.create_index([("visits.clinician_id", 1)])
                patients.create_index([("visits.status", 1)])
                patients.create_index([("visits.human_review_completed", 1)])
                patients.create_index([("visits.visit_type", 1)])
                
                # File/ingest indexes
                patients.create_index([("visits.ingests.ingest_id", 1)])
                patients.create_index([("visits.ingests.s3_key", 1)])
                patients.create_index([("visits.ingests.processing_status", 1)])
                
                # Compound indexes for common queries
                patients.create_index([
                    ("visits.clinician_id", 1),
                    ("visits.human_review_completed", 1)
                ], name="doctor_pending_reviews")
                
                patients.create_index([
                    ("pseudonym_id", 1),
                    ("visits.visit_timestamp", DESCENDING)
                ], name="patient_visits_timeline")
                
                logger.info("✅ Performance indexes created for S3-integrated schema")
                
            except Exception as e:
                logger.error(f"⚠️ Index creation failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Schema enforcement failed: {e}")
    
    def get_database(self):
        """Get database instance"""
        if not self.is_connected or self.database is None:
            self.connect()
        return self.database
    
    def get_collection(self, collection_name):
        """Get specific collection"""
        db = self.get_database()
        return db[collection_name]
    
    # ==================== S3 FILE OPERATIONS ====================
    
    def generate_presigned_url(self, s3_key, expiration=3600):
        """Generate presigned URL for temporary file access"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.s3_bucket,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None
    
    def download_file_from_s3(self, s3_key, local_path):
        """Download file from S3"""
        try:
            self.s3_client.download_file(self.s3_bucket, s3_key, local_path)
            logger.info(f"✅ Downloaded from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"❌ S3 download failed: {e}")
            return False
    
    def delete_file_from_s3(self, s3_key):
        """Delete file from S3 (use with caution)"""
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            logger.info(f"✅ Deleted from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"❌ S3 deletion failed: {e}")
            return False
    
    def get_s3_http_url(self, s3_key):
        """
        Return stable HTTP URL for an S3 object (virtual-hosted style).
        Example: https://{bucket}.s3.{region}.amazonaws.com/{key}
        For us-east-1 use the regional-less endpoint.
        """
        bucket = self.s3_bucket
        region = (self.s3_region or "").strip()
        # handle older us-east-1 endpoint variant
        if region in ("", "us-east-1"):
            return f"https://{bucket}.s3.amazonaws.com/{s3_key}"
        return f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"

    # ==================== PATIENT & VISIT OPERATIONS ====================
    
    def create_patient_record(self, pseudonym_id, clinician_id, 
                            chief_complaint="", visit_type="initial", 
                            source_system="healthcare_ai"):
        """Create a new patient record with initial visit"""
        try:
            patients = self.get_collection('patients')
            
            visit_timestamp = datetime.utcnow()
            
            patient_record = {
                "pseudonym_id": pseudonym_id,
                "visits": [
                    {
                        "visit_timestamp": visit_timestamp,
                        "visit_type": visit_type,
                        "chief_complaint": chief_complaint,
                        "ingests": [],
                        "outputs": {},
                        "visit_summary": "",
                        "doctor_notes": "",
                        "clinician_id": clinician_id,
                        "status": "in_progress",
                        "human_review_completed": False
                    }
                ],
                "patient_summary": "",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "source_system": source_system
            }
            
            result = patients.insert_one(patient_record)
            logger.info(f"✅ Patient record created: {pseudonym_id} with initial visit")
            return visit_timestamp
            
        except Exception as e:
            logger.error(f"❌ Failed to create patient record: {e}")
            return None
    
    def add_new_visit(self, pseudonym_id, clinician_id, 
                     chief_complaint="", visit_type="follow_up"):
        """Add a new visit to an existing patient"""
        try:
            patients = self.get_collection('patients')
            
            visit_timestamp = datetime.utcnow()
            
            new_visit = {
                "visit_timestamp": visit_timestamp,
                "visit_type": visit_type,
                "chief_complaint": chief_complaint,
                "ingests": [],
                "outputs": {},
                "visit_summary": "",
                "doctor_notes": "",
                "clinician_id": clinician_id,
                "status": "in_progress",
                "human_review_completed": False
            }
            
            result = patients.update_one(
                {"pseudonym_id": pseudonym_id},
                {
                    "$push": {"visits": new_visit},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ New visit added for patient {pseudonym_id}")
                return visit_timestamp
            else:
                logger.warning(f"⚠️ Patient {pseudonym_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to add new visit: {e}")
            return None
    
    def add_ingest_to_visit(self, pseudonym_id, visit_timestamp, ingest_data):
        """Add an ingest record to a specific visit"""
        try:
            patients = self.get_collection('patients')
            
            # Add timestamp if not provided
            if 'upload_timestamp' not in ingest_data:
                ingest_data['upload_timestamp'] = datetime.utcnow()
            
            result = patients.update_one(
                {
                    "pseudonym_id": pseudonym_id,
                    "visits.visit_timestamp": visit_timestamp
                },
                {
                    "$push": {"visits.$.ingests": ingest_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Ingest added to visit for patient {pseudonym_id}")
                return True
            else:
                logger.warning(f"⚠️ Visit not found for patient {pseudonym_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add ingest to visit: {e}")
            return False
    
    def upload_and_add_file_to_visit(self, pseudonym_id, visit_timestamp, 
                                    file_path, file_type):
            
        """Upload file to S3 and store permanent references in MongoDB"""
        try:
            # Generate unique ingest ID
            ingest_id = f"ING-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"
            
            # Upload to S3
            s3_result = self.upload_file_to_s3(
                file_path, pseudonym_id, visit_timestamp, file_type
            )
            
            if not s3_result:
                return None
            
            s3_key = s3_result.get('s3_key')
            # Construct http URL (permanent, non-presigned)
            http_url = self.get_s3_http_url(s3_key) if s3_key else None

            # Create ingest object with ONLY permanent data
            ingest_obj = {
                "ingest_id": ingest_id,
                "type": file_type,
                "s3_key": s3_result['s3_key'],           # ✅ Permanent reference
                "s3_bucket": s3_result['s3_bucket'],     # ✅ Permanent reference
                "s3_region": s3_result['s3_region'],     # ✅ Permanent reference
                "http_url": http_url,                    # ✅ Permanent HTTP URL (non-presigned)
                "upload_timestamp": datetime.utcnow(),
                "original_filename": os.path.basename(file_path),
                "file_size": s3_result['file_size'],
                "content_type": s3_result['content_type'],
                "processing_status": "pending",
                "parsed_text": "",
                "structured_data": {}
            }
            
            # Add to visit
            success = self.add_ingest_to_visit(pseudonym_id, visit_timestamp, ingest_obj)
            
            if success:
                logger.info(f"✅ File uploaded and metadata saved: {ingest_id}")
                return ingest_id
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file: {e}")
            return None
    
    def refresh_presigned_url(self, pseudonym_id, visit_timestamp, ingest_id):
        """Refresh expired presigned URL for a file"""
        try:
            patients = self.get_collection('patients')
            
            # Get the ingest record
            patient = patients.find_one(
                {"pseudonym_id": pseudonym_id},
                {"visits": {"$elemMatch": {"visit_timestamp": visit_timestamp}}}
            )
            
            if not patient or 'visits' not in patient or not patient['visits']:
                return None
            
            visit = patient['visits'][0]
            ingest = next((i for i in visit.get('ingests', []) if i['ingest_id'] == ingest_id), None)
            
            if not ingest:
                return None
            
            # Generate new presigned URL
            new_url = self.generate_presigned_url(ingest['s3_key'], expiration=3600)
            
            if not new_url:
                return None
            
            # Update in database
            result = patients.update_one(
                {
                    "pseudonym_id": pseudonym_id,
                    "visits.visit_timestamp": visit_timestamp,
                    "visits.ingests.ingest_id": ingest_id
                },
                {
                    "$set": {
                        "visits.$[visit].ingests.$[ingest].presigned_url": new_url,
                        "visits.$[visit].ingests.$[ingest].presigned_url_expiry": datetime.utcnow() + datetime.timedelta(seconds=3600),
                        "updated_at": datetime.utcnow()
                    }
                },
                array_filters=[
                    {"visit.visit_timestamp": visit_timestamp},
                    {"ingest.ingest_id": ingest_id}
                ]
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Presigned URL refreshed for {ingest_id}")
                return new_url
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh presigned URL: {e}")
            return None
    
    def update_visit_outputs(self, pseudonym_id, visit_timestamp, outputs_data):
        """Update AI model outputs for a specific visit"""
        try:
            patients = self.get_collection('patients')
            
            result = patients.update_one(
                {
                    "pseudonym_id": pseudonym_id,
                    "visits.visit_timestamp": visit_timestamp
                },
                {
                    "$set": {
                        "visits.$.outputs": outputs_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Outputs updated for visit")
                return True
            else:
                logger.warning(f"⚠️ Visit not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update visit outputs: {e}")
            return False
    
    def update_visit_summary(self, pseudonym_id, visit_timestamp, llm_summary):
        """Update LLM-generated summary for a visit"""
        try:
            patients = self.get_collection('patients')
            
            result = patients.update_one(
                {
                    "pseudonym_id": pseudonym_id,
                    "visits.visit_timestamp": visit_timestamp
                },
                {
                    "$set": {
                        "visits.$.visit_summary": llm_summary,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Visit summary updated")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update visit summary: {e}")
            return False
    
    def update_doctor_notes(self, pseudonym_id, visit_timestamp, 
                          doctor_notes, mark_reviewed=True):
        """Update doctor's manual notes (human-in-the-loop)"""
        try:
            patients = self.get_collection('patients')
            
            update_data = {
                "visits.$.doctor_notes": doctor_notes,
                "updated_at": datetime.utcnow()
            }
            
            if mark_reviewed:
                update_data["visits.$.human_review_completed"] = True
                update_data["visits.$.status"] = "completed"
            
            result = patients.update_one(
                {
                    "pseudonym_id": pseudonym_id,
                    "visits.visit_timestamp": visit_timestamp
                },
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Doctor notes saved")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update doctor notes: {e}")
            return False
    
    def update_patient_summary(self, pseudonym_id, patient_summary):
        """Update overall patient summary (LLM-generated from all visits)"""
        try:
            patients = self.get_collection('patients')
            
            result = patients.update_one(
                {"pseudonym_id": pseudonym_id},
                {
                    "$set": {
                        "patient_summary": patient_summary,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Patient summary updated")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to update patient summary: {e}")
            return False
    
    def get_patient_by_pseudonym(self, pseudonym_id):
        """Retrieve complete patient record by pseudonym ID"""
        try:
            patients = self.get_collection('patients')
            patient = patients.find_one({"pseudonym_id": pseudonym_id})
            return patient
        except Exception as e:
            logger.error(f"❌ Failed to retrieve patient: {e}")
            return None
    
    def get_patient_history_for_llm(self, pseudonym_id):
        """Get structured patient history for LLM context"""
        try:
            patient = self.get_patient_by_pseudonym(pseudonym_id)
            
            if not patient:
                return None
            
            # Sort visits by timestamp (oldest first)
            visits = sorted(
                patient.get("visits", []), 
                key=lambda x: x.get("visit_timestamp")
            )
            
            history = {
                "pseudonym_id": pseudonym_id,
                "total_visits": len(visits),
                "first_visit_date": visits[0].get("visit_timestamp") if visits else None,
                "last_visit_date": visits[-1].get("visit_timestamp") if visits else None,
                "patient_summary": patient.get("patient_summary", ""),
                "visit_history": []
            }
            
            for idx, visit in enumerate(visits, 1):
                history["visit_history"].append({
                    "visit_number": idx,
                    "visit_date": visit.get("visit_timestamp"),
                    "visit_type": visit.get("visit_type"),
                    "chief_complaint": visit.get("chief_complaint"),
                    "visit_summary": visit.get("visit_summary", ""),
                    "doctor_notes": visit.get("doctor_notes", ""),
                    "has_prescription": any(
                        i.get("type") == "prescription" 
                        for i in visit.get("ingests", [])
                    ),
                    "has_labs": any(
                        i.get("type") == "lab_report" 
                        for i in visit.get("ingests", [])
                    ),
                    "has_imaging": any(
                        i.get("type") == "imaging" 
                        for i in visit.get("ingests", [])
                    )
                })
            
            return history
            
        except Exception as e:
            logger.error(f"❌ Failed to get patient history: {e}")
            return None
    
    def get_latest_visit(self, pseudonym_id):
        """Get the most recent visit for a patient"""
        try:
            patient = self.get_patient_by_pseudonym(pseudonym_id)
            
            if not patient or not patient.get("visits"):
                return None
            
            # Get latest visit (sort by timestamp descending)
            visits = sorted(
                patient.get("visits", []),
                key=lambda x: x.get("visit_timestamp"),
                reverse=True
            )
            
            return visits[0] if visits else None
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest visit: {e}")
            return None
    
    def get_visits_pending_review(self, clinician_id=None):
        """Get all visits pending human review"""
        try:
            patients = self.get_collection('patients')
            
            query = {"visits.human_review_completed": False}
            if clinician_id:
                query["visits.clinician_id"] = clinician_id
            
            pending_visits = []
            
            for patient in patients.find(query):
                for visit in patient.get("visits", []):
                    if not visit.get("human_review_completed", True):
                        pending_visits.append({
                            "pseudonym_id": patient.get("pseudonym_id"),
                            "visit_timestamp": visit.get("visit_timestamp"),
                            "visit_type": visit.get("visit_type"),
                            "chief_complaint": visit.get("chief_complaint"),
                            "clinician_id": visit.get("clinician_id"),
                            "status": visit.get("status")
                        })
            
            return pending_visits
            
        except Exception as e:
            logger.error(f"❌ Failed to get pending visits: {e}")
            return []
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("🔒 MongoDB connection closed")


# Singleton instance for FastAPI integration
_mongo_instance = None

def get_mongo_connection():
    """Get singleton MongoDB connection instance"""
    global _mongo_instance
    if _mongo_instance is None:
        _mongo_instance = MongoDBConnection()
        _mongo_instance.connect()
    return _mongo_instance


@router.post("/upload-intake-documents")
async def upload_intake_documents(
    files: List[UploadFile] = File(...),
    pseudonym_id: str = Form(...),
    file_types: str = Form(...)  # Comma-separated string of file types
):
    """
    Upload multiple files to S3 and return S3 references for each file.
    Supports different file types: prescription, pathology, scan.
    Files are stored in organized folders in S3 based on type.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Parse file_types string (comma-separated) into list
        file_types_list = [ft.strip() for ft in file_types.split(',')]
        
        if len(files) != len(file_types_list):
            raise HTTPException(
                status_code=400, 
                detail=f"Number of files ({len(files)}) must match number of file types ({len(file_types_list)})"
            )
        
        # Get MongoDB connection for S3 client access
        mongo_conn = get_mongo_connection()
        
        if not mongo_conn.s3_client:
            raise HTTPException(status_code=500, detail="S3 client not initialized")
        
        uploaded_files = []
        failed_files = []
        
        for idx, (file, file_type) in enumerate(zip(files, file_types_list)):
            try:
                # Validate file type - accept new types for intake forms
                valid_types = ["prescription", "pathology", "scan", "lab_report", "imaging", "clinical_notes"]
                if file_type not in valid_types:
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"Invalid file type '{file_type}'. Must be one of: {', '.join(valid_types)}"
                    })
                    continue
                
                # Create temporary file
                file_ext = os.path.splitext(file.filename)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    # Write uploaded file to temp location
                    content = await file.read()
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                try:
                    # Get file info
                    file_size = os.path.getsize(temp_file_path)
                    max_size = int(os.getenv('MAX_FILE_SIZE_MB', '50')) * 1024 * 1024
                    
                    if file_size > max_size:
                        failed_files.append({
                            "filename": file.filename,
                            "error": f"File too large ({file_size / (1024*1024):.2f}MB). Max size: {max_size / (1024*1024)}MB"
                        })
                        os.unlink(temp_file_path)
                        continue
                    
                    # Determine content type
                    ext = os.path.splitext(file.filename)[1].lower()
                    content_type_map = {
                        '.pdf': 'application/pdf',
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.dcm': 'application/dicom',
                        '.tiff': 'image/tiff',
                        '.tif': 'image/tiff'
                    }
                    content_type = content_type_map.get(ext, file.content_type or 'application/octet-stream')
                    
                    # Create S3 key with timestamp
                    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    safe_filename = file.filename.replace(' ', '_').replace('(', '').replace(')', '')
                    s3_key = f"patients/{pseudonym_id}/intake/{file_type}/{timestamp_str}_{safe_filename}"
                    
                    # Upload to S3
                    mongo_conn.s3_client.upload_file(
                        temp_file_path,
                        mongo_conn.s3_bucket,
                        s3_key,
                        ExtraArgs={
                            'ServerSideEncryption': 'AES256',
                            'ContentType': content_type,
                            'Metadata': {
                                'pseudonym_id': pseudonym_id,
                                'file_type': file_type,
                                'original_filename': file.filename,
                                'uploaded_by': 'intake_form',
                                'upload_date': datetime.utcnow().isoformat()
                            }
                        }
                    )
                    
                    # Generate presigned URL for immediate access
                    presigned_url = mongo_conn.generate_presigned_url(s3_key, expiration=3600)
                    
                    # Generate S3 URI
                    uri = f"s3://{mongo_conn.s3_bucket}/{s3_key}"
                    
                    # Permanent HTTP URL (non-presigned) stored in DB in requested format
                    http_url = mongo_conn.get_s3_http_url(s3_key)
                    
                    # Add to successful uploads
                    uploaded_files.append({
                        "original_filename": file.filename,
                        "file_type": file_type,
                        "s3_key": s3_key,
                        "s3_bucket": mongo_conn.s3_bucket,
                        "s3_region": mongo_conn.s3_region,
                        "uri": uri,
                        # Store the permanent HTTP URL (no query params) as the canonical url
                        "url": http_url,
                        # Provide the presigned URL separately for immediate frontend access
                        "presigned_url": presigned_url,
                        "file_size": file_size,
                        "content_type": content_type,
                        "upload_timestamp": datetime.utcnow().isoformat()
                    })
                    
                    logger.info(f"✅ Uploaded to S3: {s3_key}")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        
            except Exception as e:
                logger.error(f"❌ Failed to upload {file.filename}: {e}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        # Return response
        response = {
            "success": len(uploaded_files) > 0,
            "total_files": len(files),
            "uploaded_count": len(uploaded_files),
            "failed_count": len(failed_files),
            "uploaded_files": uploaded_files
        }
        
        if failed_files:
            response["failed_files"] = failed_files
        
        if len(uploaded_files) == 0:
            raise HTTPException(
                status_code=500,
                detail="All file uploads failed. See failed_files for details.",
                headers={"X-Failed-Files": str(failed_files)}
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )
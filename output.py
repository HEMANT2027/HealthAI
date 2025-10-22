def enforce_healthcare_schema(self):
    """Enforce the healthcare schema structure with visit-based tracking"""
    try:
        print("🔧 Enforcing healthcare schema with visit-based structure...")
        
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
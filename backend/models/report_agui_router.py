"""
AGUI Protocol Implementation for Medical Report Processing
Provides streaming responses for OCR and analysis tasks
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import uuid
from datetime import datetime
import asyncio
import os

from endpoints.auth import authMiddleware
from pymongo import MongoClient

# Import pipelines
try:
    from .ocr_ner import MedicalOCRPipeline
    from .patho import PDFPathologyPipeline
    from .medgemma import MedGemmaMultiInputClient
except ImportError:
    MedicalOCRPipeline = None
    PDFPathologyPipeline = None
    MedGemmaMultiInputClient = None

router = APIRouter(prefix="/report-agent", tags=["Report AGUI Agent"])

# MongoDB Setup
client = MongoClient(os.getenv("MONGODB_KEY"))
db = client["medicotourism"]
form_collection = db["intake_forms"]
collection = db["ocr_medsam_reports"]

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
GCP_KEY_FILE = "heroic-dynamo-473510-q9-936d0b6e305a.json"
GCP_KEY_PATH = os.path.join(MODULE_DIR, GCP_KEY_FILE)


# ============================================================
# AGUI Event Types
# ============================================================
class EventType:
    RUN_STARTED = "run_started"
    PRESCRIPTION_STARTED = "prescription_started"
    PRESCRIPTION_CHUNK = "prescription_chunk"
    PRESCRIPTION_FINISHED = "prescription_finished"
    PATHOLOGY_STARTED = "pathology_started"
    PATHOLOGY_CHUNK = "pathology_chunk"
    PATHOLOGY_FINISHED = "pathology_finished"
    SCANS_LOADED = "scans_loaded"
    RUN_FINISHED = "run_finished"
    ERROR = "error"


# ============================================================
# Request Models
# ============================================================
class ProcessIntakeRequest(BaseModel):
    """Input schema for processing intake form"""
    pseudonym_id: str


# ============================================================
# Event Encoder
# ============================================================
class EventEncoder:
    """Encodes events for streaming based on Accept header"""
    
    def __init__(self, accept: Optional[str] = None):
        self.use_sse = accept and "text/event-stream" in accept
        self.content_type = "text/event-stream" if self.use_sse else "application/x-ndjson"
    
    def encode(self, event: Dict[str, Any]) -> str:
        """Encode event as SSE or JSON-lines"""
        json_str = json.dumps(event, ensure_ascii=False)
        
        if self.use_sse:
            return f"data: {json_str}\n\n"
        else:
            return f"{json_str}\n"
    
    def get_content_type(self) -> str:
        return self.content_type


# ============================================================
# Helper Functions
# ============================================================
def _run_medical_ocr(image_url: str) -> str:
    """Run prescription OCR pipeline"""
    if not MedicalOCRPipeline:
        raise Exception("OCR pipeline not available")
    
    pipeline = MedicalOCRPipeline(
        image_path=image_url,
        gcp_key_path=GCP_KEY_PATH,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    pipeline.run()
    return pipeline.full_text


def _run_pathology_ocr(pdf_url: str) -> str:
    """Run pathology OCR pipeline"""
    if not PDFPathologyPipeline:
        raise Exception("Pathology pipeline not available")
    
    pipeline = PDFPathologyPipeline(
        pdf_path=pdf_url,
        gcp_key_path=GCP_KEY_PATH,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    pipeline.run()
    return pipeline.ocr_text


# ============================================================
# AGUI Streaming Endpoint
# ============================================================
@router.post("")
async def process_intake_streaming(
    input_data: ProcessIntakeRequest,
    request: Request,
    current_user: dict = Depends(authMiddleware)
):
    """
    AGUI-compatible streaming endpoint for processing intake forms.
    
    Streams events:
    - run_started: Processing begins
    - prescription_started: Prescription OCR begins
    - prescription_chunk: Streaming prescription text
    - prescription_finished: Prescription OCR complete
    - pathology_started: Pathology OCR begins
    - pathology_chunk: Streaming pathology text
    - pathology_finished: Pathology OCR complete
    - scans_loaded: Scan images loaded
    - run_finished: Processing complete
    """
    
    encoder = EventEncoder(accept=request.headers.get("accept"))
    run_id = str(uuid.uuid4())
    
    async def event_generator():
        try:
            # ✅ Event 1: Run Started
            yield encoder.encode({
                "type": EventType.RUN_STARTED,
                "runId": run_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Fetch intake form
            intake_form = await asyncio.to_thread(
                form_collection.find_one,
                {"patient": input_data.pseudonym_id}
            )
            
            if not intake_form:
                yield encoder.encode({
                    "type": EventType.ERROR,
                    "error": "Intake form not found",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            documents = intake_form.get("documents", [])
            prescription_file = next((doc for doc in documents if doc.get("type") == "prescription"), None)
            pathology_file = next((doc for doc in documents if doc.get("type") == "pathology"), None)
            scan_files = [doc for doc in documents if doc.get("type") == "scan"]
            
            prescription_text = ""
            pathology_text = ""
            
            # ✅ Process Prescription OCR (First, with streaming)
            if prescription_file:
                yield encoder.encode({
                    "type": EventType.PRESCRIPTION_STARTED,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                try:
                    # Run OCR in thread
                    prescription_text = await asyncio.to_thread(
                        _run_medical_ocr,
                        prescription_file.get("url")
                    )
                    
                    # Stream the result in chunks
                    chunk_size = 100
                    for i in range(0, len(prescription_text), chunk_size):
                        chunk = prescription_text[i:i + chunk_size]
                        yield encoder.encode({
                            "type": EventType.PRESCRIPTION_CHUNK,
                            "delta": chunk
                        })
                        await asyncio.sleep(0.03)
                    
                    yield encoder.encode({
                        "type": EventType.PRESCRIPTION_FINISHED,
                        "content": prescription_text,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing prescription: {str(e)}"
                    prescription_text = error_msg
                    yield encoder.encode({
                        "type": EventType.PRESCRIPTION_FINISHED,
                        "content": error_msg,
                        "error": True,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # ✅ Process Pathology OCR (Second, with streaming)
            if pathology_file:
                yield encoder.encode({
                    "type": EventType.PATHOLOGY_STARTED,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                try:
                    # Run OCR in thread
                    pathology_text = await asyncio.to_thread(
                        _run_pathology_ocr,
                        pathology_file.get("url")
                    )
                    
                    # Stream the result in chunks
                    chunk_size = 100
                    for i in range(0, len(pathology_text), chunk_size):
                        chunk = pathology_text[i:i + chunk_size]
                        yield encoder.encode({
                            "type": EventType.PATHOLOGY_CHUNK,
                            "delta": chunk
                        })
                        await asyncio.sleep(0.03)
                    
                    yield encoder.encode({
                        "type": EventType.PATHOLOGY_FINISHED,
                        "content": pathology_text,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing pathology: {str(e)}"
                    pathology_text = error_msg
                    yield encoder.encode({
                        "type": EventType.PATHOLOGY_FINISHED,
                        "content": error_msg,
                        "error": True,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # ✅ Load Scan Images
            scan_images = [
                {"url": doc.get("url"), "name": doc.get("fileName")}
                for doc in scan_files
            ]
            
            yield encoder.encode({
                "type": EventType.SCANS_LOADED,
                "scans": scan_images,
                "count": len(scan_images),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # ✅ Event: Run Finished
            yield encoder.encode({
                "type": EventType.RUN_FINISHED,
                "runId": run_id,
                "prescription_text": prescription_text,
                "pathology_text": pathology_text,
                "scan_images": scan_images,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            yield encoder.encode({
                "type": EventType.ERROR,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================
# MedGemma Analysis Endpoint (AGUI Streaming)
# ============================================================
class AnalyzeMedGemmaRequest(BaseModel):
    """Input schema for MedGemma analysis"""
    images: List[Dict[str, Any]]
    prescription_text: str = ""
    pathology_text: str = ""
    doctor_prompt: Optional[str] = None


@router.post("/analyze-medgemma")
async def analyze_with_medgemma_streaming(
    payload: AnalyzeMedGemmaRequest,
    request: Request,
    current_user: dict = Depends(authMiddleware)
):
    """
    AGUI-compatible streaming endpoint for MedGemma analysis.
    
    Streams events:
    - analysis_started: Analysis begins
    - analysis_progress: Progress updates
    - analysis_chunk: Streaming analysis text
    - analysis_finished: Analysis complete
    """
    import tempfile
    import requests
    from PIL import Image
    
    encoder = EventEncoder(accept=request.headers.get("accept"))
    analysis_id = str(uuid.uuid4())
    
    async def event_generator():
        temp_files = []
        try:
            # ✅ Event 1: Analysis Started
            yield encoder.encode({
                "type": "analysis_started",
                "analysisId": analysis_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            images = payload.images
            prescription_text = payload.prescription_text
            pathology_text = payload.pathology_text
            doctor_prompt = payload.doctor_prompt

            if not images:
                yield encoder.encode({
                    "type": "error",
                    "error": "No images provided",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return

            if not MedGemmaMultiInputClient:
                yield encoder.encode({
                    "type": "error",
                    "error": "MedGemma client not available",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return

            # ✅ Event 2: Progress - Downloading images
            yield encoder.encode({
                "type": "analysis_progress",
                "message": "Downloading and processing images...",
                "progress": 20,
                "timestamp": datetime.utcnow().isoformat()
            })

            endpoint_name = os.getenv("MEDGEMMA_ENDPOINT") or "jumpstart-dft-hf-vlm-gemma-3-4b-ins-20251031-123610"
            client = MedGemmaMultiInputClient(endpoint_name=endpoint_name)

            image_paths_for_model = []

            for img_obj in images:
                url = img_obj.get("url")
                regions = img_obj.get("regions", []) or []

                if not url:
                    continue

                # Download remote image
                try:
                    r = await asyncio.to_thread(requests.get, url, timeout=30)
                    r.raise_for_status()
                except Exception as e:
                    yield encoder.encode({
                        "type": "error",
                        "error": f"Failed to download image {url}: {e}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return

                # Save original to temp
                tmp_orig = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                tmp_orig.write(r.content)
                tmp_orig.flush()
                tmp_orig.close()
                temp_files.append(tmp_orig.name)

                # Open image for cropping
                try:
                    pil_img = Image.open(tmp_orig.name).convert("RGB")
                except Exception as e:
                    image_paths_for_model.append(tmp_orig.name)
                    continue

                if regions:
                    for i, reg in enumerate(regions):
                        try:
                            x = int(reg.get("x", 0))
                            y = int(reg.get("y", 0))
                            w = int(reg.get("w", 0))
                            h = int(reg.get("h", 0))
                            left = max(0, x)
                            top = max(0, y)
                            right = min(pil_img.width, x + w)
                            bottom = min(pil_img.height, y + h)
                            if right <= left or bottom <= top:
                                continue
                            cropped = pil_img.crop((left, top, right, bottom))
                            out_path = tmp_orig.name + f"_crop_{i}.jpg"
                            cropped.save(out_path, format="JPEG", quality=90)
                            temp_files.append(out_path)
                            image_paths_for_model.append(out_path)
                        except Exception:
                            continue
                else:
                    image_paths_for_model.append(tmp_orig.name)

            if not image_paths_for_model:
                yield encoder.encode({
                    "type": "error",
                    "error": "No valid image pages/regions available to analyze",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return

            # ✅ Event 3: Progress - Building payload
            yield encoder.encode({
                "type": "analysis_progress",
                "message": "Preparing analysis request...",
                "progress": 40,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Build payload and invoke MedGemma
            payload_for_model = client.build_payload(
                system_prompt="You are a helpful medical assistant",
                doctor_prompt=doctor_prompt,
                prescription_text=prescription_text,
                pathology_text=pathology_text,
                image_paths=image_paths_for_model,
                max_tokens=1024
            )

            # ✅ Event 4: Progress - Analyzing
            yield encoder.encode({
                "type": "analysis_progress",
                "message": "Running MedGemma analysis...",
                "progress": 60,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Run analysis in thread
            model_result = await asyncio.to_thread(client.invoke, payload_for_model)

            # ✅ Event 5: Stream result in chunks
            yield encoder.encode({
                "type": "analysis_progress",
                "message": "Generating report...",
                "progress": 80,
                "timestamp": datetime.utcnow().isoformat()
            })

            chunk_size = 50
            for i in range(0, len(model_result), chunk_size):
                chunk = model_result[i:i + chunk_size]
                yield encoder.encode({
                    "type": "analysis_chunk",
                    "delta": chunk
                })
                await asyncio.sleep(0.05)

            # ✅ Event 6: Analysis Finished
            yield encoder.encode({
                "type": "analysis_finished",
                "analysisId": analysis_id,
                "content": model_result,
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            yield encoder.encode({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        finally:
            # Cleanup temp files
            for p in temp_files:
                try:
                    os.remove(p)
                except Exception:
                    pass
    
    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================
# Save Analysis Endpoint
# ============================================================
@router.post("/save-analysis")
async def save_analysis(
    payload: Dict[str, Any],
    current_user: dict = Depends(authMiddleware)
):
    """
    Save combined OCR / pathology / MedGemma results to MongoDB.
    Same functionality as /report/save-analysis
    """
    try:
        pseudonym_id = payload.get("pseudonym_id")
        if not pseudonym_id:
            raise HTTPException(status_code=400, detail="pseudonym_id is required")

        record = {
            "pseudonym_id": pseudonym_id,
            "prescription_ocr": payload.get("prescription_ocr", ""),
            "pathology_ocr": payload.get("pathology_ocr", ""),
            "medgemma_analysis": payload.get("medgemma_analysis") or payload.get("analysis") or "",
            "images": payload.get("images", []),
            "meta": payload.get("meta", {}),
            "created_by": current_user.get("email") if current_user else None,
            "created_at": datetime.utcnow()
        }

        # Insert record
        res = collection.insert_one(record)
        inserted_id = str(res.inserted_id)

        # Link to intake form
        try:
            form_collection.update_one(
                {"patient": pseudonym_id},
                {"$push": {"reports": {"report_id": inserted_id, "created_at": record["created_at"]}}},
                upsert=False
            )
        except Exception:
            pass

        return {"success": True, "report_id": inserted_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Health Check
# ============================================================
@router.get("/health")
async def report_agent_health():
    """Check if report agent is operational"""
    return {
        "status": "healthy",
        "agent": "ReportProcessor",
        "protocol": "AGUI",
        "version": "1.0.0",
        "pipelines": {
            "ocr": MedicalOCRPipeline is not None,
            "pathology": PDFPathologyPipeline is not None,
            "medgemma": MedGemmaMultiInputClient is not None
        }
    }

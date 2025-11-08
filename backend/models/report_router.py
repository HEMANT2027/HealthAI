from fastapi import FastAPI, APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from pymongo import MongoClient
import datetime
import asyncio
import os
import tempfile
import requests
from PIL import Image
from endpoints.auth import authMiddleware
from bson import ObjectId

# === Import your pipelines ===
try:
    from .ocr_ner import MedicalOCRPipeline
    from .patho import PDFPathologyPipeline
    from .medgemma import MedGemmaMultiInputClient
except ImportError:
    # Fallback for when modules are not available
    MedicalOCRPipeline = None
    PDFPathologyPipeline = None

router = APIRouter(prefix="/report", tags=["Medical Report Pipeline"])
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
GCP_KEY_FILE = "heroic-dynamo-473510-q9-936d0b6e305a.json"
GCP_KEY_PATH = os.path.join(MODULE_DIR, GCP_KEY_FILE)

# ==============================
# MongoDB Setup
# ==============================
client = MongoClient(os.getenv("MONGODB_KEY"))
db = client["medicotourism"]
collection = db["ocr_medsam_reports"]
form_collection = db["intake_forms"]

# ==============================
# Data Models
# ==============================
class OCRExtractRequest(BaseModel):
    image_path: str

class PDFPathologyExtractRequest(BaseModel) :
    pdf_path : str

class MedGemmaRequest(BaseModel):
    pathology_text: str
    prescription_text: str
    medsam_text: str
    image_data: List[str] = []
    doctor_prompt: str = "Summarize findings and suggest possible diagnosis in a well descriptive manner and after that summarize all cases in bullet points, be considerate about every possible case"


# ==============================
# 0️⃣ Fetch Intake Form Data
# ==============================
@router.get("/intake-form/{pseudonym_id}")
async def get_intake_form_data(
    pseudonym_id: str,
    current_user: dict = Depends(authMiddleware)
):
    """
    Fetch intake form data for a patient and process documents concurrently
    (prescription + pathology OCR in parallel)
    """
    try:
        # Fetch the intake form
        intake_form = form_collection.find_one({"patient": pseudonym_id})
        if not intake_form:
            raise HTTPException(status_code=404, detail="Intake form not found")

        documents = intake_form.get("documents", [])
        prescription_file = next((doc for doc in documents if doc.get("type") == "prescription"), None)
        pathology_file = next((doc for doc in documents if doc.get("type") == "pathology"), None)
        scan_files = [doc for doc in documents if doc.get("type") == "scan"]

        async def process_prescription():
            if not prescription_file or not MedicalOCRPipeline:
                return None
            try:
                return await asyncio.to_thread(
                    lambda: _run_medical_ocr(prescription_file.get("url"))
                )
            except Exception as e:
                print(f"Error processing prescription OCR: {e}")
                return "Error processing prescription file"

        async def process_pathology():
            if not pathology_file or not PDFPathologyPipeline:
                return None
            try:
                return await asyncio.to_thread(
                    lambda: _run_pathology_ocr(pathology_file.get("url"))
                )
            except Exception as e:
                print(f"Error processing pathology OCR: {e}")
                return "Error processing pathology file"

        # Run both OCRs in parallel
        prescription_ocr, pathology_ocr = await asyncio.gather(
            process_prescription(),
            process_pathology()
        )

        return {
            "success": True,
            "prescription_ocr": prescription_ocr,
            "pathology_ocr": pathology_ocr,
            "scan_images": [
                {"url": doc.get("url"), "name": doc.get("fileName")}
                for doc in scan_files
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions for threaded execution
def _run_medical_ocr(image_url: str):
    pipeline = MedicalOCRPipeline(
        image_path=image_url,
        gcp_key_path=GCP_KEY_PATH,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    pipeline.run()
    return pipeline.full_text


def _run_pathology_ocr(pdf_url: str):
    pipeline = PDFPathologyPipeline(
        pdf_path=pdf_url,
        gcp_key_path=GCP_KEY_PATH,
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )
    pipeline.run()
    return pipeline.ocr_text

# ==============================
# 1️⃣ Run OCR + Gemini Pipeline
# ==============================
@router.post("/ocr/extract")
async def extract_ocr_data(request: OCRExtractRequest):
    """
    Extract structured text data using Vision API + Gemini.
    """
    try:
        if not MedicalOCRPipeline:
            raise HTTPException(status_code=503, detail="OCR pipeline not available")
            
        pipeline = MedicalOCRPipeline(
            image_path=request.image_path,
            gcp_key_path = "heroic-dynamo-473510-q9-936d0b6e305a.json",  # Replace with your actual key file
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        pipeline.run()

        return {
            "status": "success",
            "ocr_full_text": pipeline.full_text,
            "medical_entities": pipeline.extract_medical_entities()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf_pathology/extract")
async def extract_pdf_pathology_data(request: PDFPathologyExtractRequest):
    """
    Extract pathology report from PDF using PDF Pathology pipeline model.
    """
    try:
        if not PDFPathologyPipeline:
            raise HTTPException(status_code=503, detail="Pathology pipeline not available")
            
        pipeline = PDFPathologyPipeline(
            pdf_path=request.pdf_path,
            gcp_key_path = "heroic-dynamo-473510-q9-936d0b6e305a.json" , # Replace with your actual key file
            gemini_api_key=os.getenv("GEMINI_API_KEY")
        )
        pipeline.run()

        return {
            "status": "success",
            "ocr_full_text": pipeline.ocr_text,
            "medical_entities": pipeline.entities
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/analyze_medgemma")
async def analyze_with_medgemma(payload: dict = Body(...)):
    """
    Payload format:
    {
      "images": [
        { "url": "https://...", "regions": [{ "x": 10, "y": 20, "w": 100, "h": 80 }, ...] },
        ...
      ],
      "prescription_text": "...",
      "pathology_text": "...",
      "doctor_prompt": "optional prompt"
    }
    """
    images = payload.get("images", [])
    prescription_text = payload.get("prescription_text", "")
    pathology_text = payload.get("pathology_text", "")
    doctor_prompt = payload.get("doctor_prompt")

    if not images:
        raise HTTPException(status_code=400, detail="No images provided")

    endpoint_name = os.getenv("MEDGEMMA_ENDPOINT") or "jumpstart-dft-hf-vlm-gemma-3-4b-ins-20251031-123610"
    client = MedGemmaMultiInputClient(endpoint_name=endpoint_name)

    temp_files = []
    try:
        # For each image, download and crop selected regions (if any).
        # Cropped images are passed to MedGemma.
        image_paths_for_model = []

        for img_obj in images:
            url = img_obj.get("url")
            regions = img_obj.get("regions", []) or []

            if not url:
                continue

            # download remote image
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to download image {url}: {e}")

            # save original to temp
            tmp_orig = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_orig.write(r.content)
            tmp_orig.flush()
            tmp_orig.close()
            temp_files.append(tmp_orig.name)

            # open image for cropping
            try:
                pil_img = Image.open(tmp_orig.name).convert("RGB")
            except Exception as e:
                # fallback: pass original file if PIL cannot open
                image_paths_for_model.append(tmp_orig.name)
                continue

            if regions:
                for i, reg in enumerate(regions):
                    try:
                        x = int(reg.get("x", 0))
                        y = int(reg.get("y", 0))
                        w = int(reg.get("w", 0))
                        h = int(reg.get("h", 0))
                        # ensure bounds
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
                        # on failure of a region, skip it
                        continue
            else:
                # no regions — send full image
                image_paths_for_model.append(tmp_orig.name)

        if not image_paths_for_model:
            raise HTTPException(status_code=400, detail="No valid image pages/regions available to analyze")

        # build payload and invoke MedGemma
        payload_for_model = client.build_payload(
            system_prompt="You are a helpful medical assistant",
            doctor_prompt=doctor_prompt,
            prescription_text=prescription_text,
            pathology_text=pathology_text,
            image_paths=image_paths_for_model,
            max_tokens=1024
        )

        model_result = client.invoke(payload_for_model)
        return {"success": True, "analysis": model_result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # cleanup temp files
        for p in temp_files:
            try:
                os.remove(p)
            except Exception:
                pass

@router.post("/save-analysis")
async def save_analysis(
    payload: Dict[str, Any] = Body(...),
    current_user: dict = Depends(authMiddleware)
):
    """
    Save combined OCR / pathology / MedGemma results to MongoDB.

    Expected payload keys (flexible):
      - pseudonym_id (required)
      - prescription_ocr
      - pathology_ocr
      - medgemma_analysis  (can be string or structured JSON)
      - images (list of {url, name, regions[...]})
      - meta (optional dict)
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
            "created_at": datetime.datetime.utcnow()
        }

        # Insert record
        res = collection.insert_one(record)
        inserted_id = str(res.inserted_id)

        # Optionally link this report to the intake form document if it exists
        try:
            form_collection.update_one(
                {"patient": pseudonym_id},
                {"$push": {"reports": {"report_id": inserted_id, "created_at": record["created_at"]}}},
                upsert=False
            )
        except Exception:
            # non-fatal; continue even if linking fails
            pass

        return {"success": True, "report_id": inserted_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
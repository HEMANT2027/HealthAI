import os
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
from google.cloud import vision
import google.generativeai as genai
from fastapi import APIRouter, HTTPException, Body

router = APIRouter(prefix="/ocr", tags=["OCR_NER"])

class MedicalOCRPipeline:
    ocr_text = None
    def __init__(self, image_path, gcp_key_path, gemini_api_key):
        self.image_path = image_path
        self.gcp_key_path = gcp_key_path
        self.gemini_api_key = gemini_api_key
        self.processed_image_path = 'processed_prescription.png'
        self.full_text = None
        self.model = None

    def verify_image(self):
        print("🔍 Verifying image...")
        img = cv2.imread(self.image_path)
        if img is None:
            raise FileNotFoundError(f"❌ Could not read the image at {self.image_path}")
        print(f"✅ Successfully loaded image from: {self.image_path}")
        return img

    def preprocess_image(self):
        print("⚙ Starting preprocessing...")
        image = cv2.imread(self.image_path)
        if image is None:
            raise ValueError("❌ Failed to load image for preprocessing.")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 5
        )

        success = cv2.imwrite(self.processed_image_path, binary)
        if success:
            print(f"✅ Processed image saved at: {self.processed_image_path}")
        else:
            raise IOError("❌ Failed to save processed image. Check write permissions or path.")

    def configure_gcp_credentials(self):
        print("🔐 Configuring GCP credentials...")
        if not os.path.exists(self.gcp_key_path):
            raise FileNotFoundError("❌ GCP key file not found.")
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.gcp_key_path
        print("✅ GCP credentials configured.")

    def extract_text_with_vision(self):
        print("📄 Extracting text with Vision API...")
        client = vision.ImageAnnotatorClient()
        with open(self.processed_image_path, 'rb') as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        if response.error.message:
            raise Exception(f"Vision API error: {response.error.message}")
        self.full_text = response.full_text_annotation.text
        ocr_text = response.full_text_annotation.text
        print("\n✅ Text Extraction Complete!")
        print("\n================ OCR OUTPUT ================")
        print(self.full_text)
        print("==========================================")

    def configure_gemini(self):
        print("🤖 Configuring Gemini API...")
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        if not self.model:
            raise Exception("Gemini model not initialized.")

        print("✅ Gemini API configured.")

    def extract_medical_entities(self):
        print("🧠 Extracting medical entities...")
        if not self.full_text:
            print("❌ No OCR text available for NER.")
            return []
        prompt = f"""
You are a biomedical text mining expert.

Analyze the following text and extract all medically relevant terms, including but not limited to:
- Diseases and conditions
- Symptoms and signs
- Drugs and chemicals
- Lab tests and procedures
- Anatomical parts
- Medical devices
- Clinical findings
- Any other term commonly found in medical literature

Return the output as a valid JSON list of objects. Each object should have:
- "entity": the extracted term
- "type": a broad category such as DISEASE, SYMPTOM, DRUG, TEST, ANATOMY, PROCEDURE, DEVICE, etc.

If no entities are found, return an empty list [].

Text to analyze:
---
{self.full_text}
---
"""     
        raw_text=""
        try:
            response = self.model.generate_content(prompt)
            raw_text = getattr(response, "text", "").strip()
            if not raw_text:
                raise ValueError("Empty response from Gemini API")

            # Try to find JSON substring if response has extra text
            start = raw_text.find('[')
            end = raw_text.rfind(']') + 1
            if start != -1 and end != 0:
                json_text = raw_text[start:end]
            else:
                raise ValueError(f"No JSON array found in response: {raw_text}")

            entities = json.loads(json_text)
            print("\n================ MEDICAL ENTITIES FOUND ================")
            for e in entities:
                print(f"- Entity: \"{e.get('entity','N/A')}\", Type: {e.get('type','N/A')}")
            print("========================================================")
            return entities

        except Exception as e:
            print(f"❌ Error during NER: {e}")
            print(f"🧾 Raw model output:\n{raw_text if 'raw_text' in locals() else 'No text returned'}")
            return []


    def run(self):
        try:
            self.verify_image()
            self.preprocess_image()
            self.configure_gcp_credentials()
            self.extract_text_with_vision()
            self.configure_gemini()
            self.extract_medical_entities()
            # response = self.model.generate_content("Return JSON: [{\"entity\":\"Hypertension\",\"type\":\"DISEASE\"}]")
            # print(response.text)

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")

@router.post("/extract")
def extract_text_and_entities(payload: dict = Body(...)):
    """
    Run the full OCR + NER pipeline and store the extracted text in memory.
    """
    global current_text

    image_path = payload.get("image_path")
    gcp_key_path = payload.get("gcp_key_path")
    gemini_api_key = payload.get("gemini_api_key")

    if not all([image_path, gcp_key_path, gemini_api_key]):
        raise HTTPException(status_code=400, detail="Missing one or more required parameters.")

    pipeline = MedicalOCRPipeline(image_path, gcp_key_path, gemini_api_key)

    try:
        result = pipeline.run()
        current_text = result["full_text"]  # Store extracted text in memory
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/text")
def get_full_text():
    """
    Fetch the currently stored OCR text (from memory).
    """
    if not current_text:
        raise HTTPException(status_code=404, detail="No OCR text found. Run the pipeline first.")
    return {"full_text": current_text}


@router.post("/text")
def update_full_text(payload: dict = Body(...)):
    """
    Update the in-memory OCR text manually from the frontend.
    """
    global current_text
    new_text = payload.get("full_text")
    if not new_text:
        raise HTTPException(status_code=400, detail="Missing 'full_text' in request body.")
    current_text = new_text
    return {"message": "✅ full_text updated successfully", "full_text": current_text}


# --- Example Usage ---
if __name__ == "__main__":
    image_path = "3.jpg"  # Make sure this file exists in your working directory
    gcp_key_path = r"C:\Users\Aditya Pratap Singh\Desktop\HEALTH-AI AQ\heroic-dynamo-473510-q9-936d0b6e305a.json"  # Replace with your actual key file
    gemini_api_key = "AIzaSyAh0g0SF0NFvbhLDiOXPLGp-JhBBvmDS4c"  # Replace with your actual Gemini API key

    pipeline = MedicalOCRPipeline(image_path, gcp_key_path, gemini_api_key)
    pipeline.run()
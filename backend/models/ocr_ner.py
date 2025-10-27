import os
import io
import tempfile
import requests
import cv2
import json
import numpy as np
import matplotlib.pyplot as plt
from google.cloud import vision
import google.generativeai as genai
from fastapi import APIRouter, HTTPException, Body
import fitz  
import shutil  # <-- added

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

        # Minimal additions to support PDF input
        self.pdf_path = None
        self.image_dir = None
        if isinstance(image_path, str):
            lower = image_path.lower()
            if lower.endswith(".pdf") or (lower.startswith("http") and ".pdf" in lower):
                self.pdf_path = image_path
                # create temporary directory to hold converted page images
                self.image_dir = tempfile.mkdtemp(prefix="ocr_pdf_")

    def convert_pdf_to_images(self):
        print("📄 Converting PDF to images...")
        os.makedirs(self.image_dir, exist_ok=True)

        pdf_path = self.pdf_path
        temp_downloaded = None

        # If pdf_path is a URL, download it first
        if isinstance(pdf_path, str) and pdf_path.lower().startswith("http"):
            try:
                print(f"🔽 Downloading remote PDF: {pdf_path}")
                r = requests.get(pdf_path, stream=True, timeout=30)
                r.raise_for_status()
                suffix = ".pdf"
                tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                with tf as f:
                    for chunk in r.iter_content(1024 * 64):
                        if chunk:
                            f.write(chunk)
                temp_downloaded = tf.name
                pdf_path = temp_downloaded
            except Exception as e:
                raise RuntimeError(f"❌ Could not download PDF from URL: {e}")

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise RuntimeError(f"❌ Could not open PDF '{pdf_path}': {e}")

        image_paths = []
        try:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=300)
                image_path = os.path.join(self.image_dir, f"page_{i+1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
            print(f"✅ Converted {len(image_paths)} pages to images.")
            return image_paths
        finally:
            doc.close()
            if temp_downloaded:
                os.remove(temp_downloaded)  # Clean up temp file


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
        Extract all medically relevant entities (diseases, symptoms, drugs, tests, anatomy, etc.)
        Return output strictly as a JSON list like:
        [{{"entity": "Hypertension", "type": "DISEASE"}}, ...]
        
        Text:
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
            # If input is a PDF (local path or remote URL), convert pages and process each page
            if self.pdf_path:
                print("📄 Detected PDF input — running page-wise OCR pipeline.")
                try:
                    image_pages = self.convert_pdf_to_images()
                except Exception as e:
                    raise RuntimeError(f"❌ Pipeline failed during PDF -> image conversion: {e}")

                all_texts = []
                # configure GCP once
                self.configure_gcp_credentials()
                for idx, page_img in enumerate(image_pages):
                    try:
                        print(f"🔍 Processing page {idx+1}/{len(image_pages)}: {page_img}")
                        # update image path and processed image path per page
                        self.image_path = page_img
                        self.processed_image_path = os.path.join(self.image_dir, f"processed_page_{idx+1}.png")

                        # preprocess and OCR
                        self.preprocess_image()
                        self.extract_text_with_vision()
                        all_texts.append(self.full_text or "")

                    except Exception as e:
                        # continue with other pages but log
                        print(f"❌ Failed processing page {idx+1}: {e}")

                # aggregate OCR text from pages
                self.full_text = "\n\n".join([t for t in all_texts if t.strip()])
                if not self.full_text:
                    raise RuntimeError("❌ No OCR text extracted from PDF pages.")

                # NER
                self.configure_gemini()
                self.extract_medical_entities()

                # cleanup temp images directory
                try:
                    if self.image_dir and os.path.exists(self.image_dir):
                        shutil.rmtree(self.image_dir, ignore_errors=True)
                except Exception:
                    pass

            else:
                # existing single-image flow
                self.verify_image()
                self.preprocess_image()
                self.configure_gcp_credentials()
                self.extract_text_with_vision()
                self.configure_gemini()
                self.extract_medical_entities()

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")

# --- Example Usage ---
if __name__ == "__main__":
    image_path = "Screenshot from 2025-03-18 19-51-33.png"  # Make sure this file exists in your working directory
    gcp_key_path = "heroic-dynamo-473510-q9-936d0b6e305a.json"  # Replace with your actual key file
    gemini_api_key = "AIzaSyAh0g0SF0NFvbhLDiOXPLGp-JhBBvmDS4c"  # Replace with your actual Gemini API key

    pipeline = MedicalOCRPipeline(image_path, gcp_key_path, gemini_api_key)
    pipeline.run()
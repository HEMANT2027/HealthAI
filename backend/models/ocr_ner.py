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
from PIL import Image  # <-- added

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
        # track any temp file downloaded (image/pdf)
        self._temp_downloaded = None

        if isinstance(image_path, str):
            lower = image_path.lower()
            if lower.endswith(".pdf") or (lower.startswith("http") and ".pdf" in lower):
                self.pdf_path = image_path
                # create temporary directory to hold converted page images
                self.image_dir = tempfile.mkdtemp(prefix="ocr_pdf_")

    def _download_remote_file(self, url: str) -> str:
        """Download remote URL (image or PDF) to a temp file and return local path."""
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Could not download file from URL: {e}")

        # infer suffix from content-type or url
        ct = resp.headers.get("content-type", "")
        suffix = None
        if "pdf" in ct:
            suffix = ".pdf"
        elif "jpeg" in ct or "jpg" in ct:
            suffix = ".jpg"
        elif "png" in ct:
            suffix = ".png"
        elif "tiff" in ct or "tif" in ct:
            suffix = ".tiff"
        else:
            parsed = os.path.splitext(url.split("?")[0])
            suffix = parsed[1] if len(parsed) > 1 and parsed[1] else ".jpg"

        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            for chunk in resp.iter_content(1024 * 64):
                if chunk:
                    tf.write(chunk)
            tf.flush()
            tf.close()
            self._temp_downloaded = tf.name
            return tf.name
        except Exception as e:
            try:
                tf.close()
                os.remove(tf.name)
            except Exception:
                pass
            raise RuntimeError(f"Failed saving remote file: {e}")

    def convert_pdf_to_images(self):
        print("📄 Converting PDF to images...")
        os.makedirs(self.image_dir, exist_ok=True)

        pdf_path = self.pdf_path
        temp_downloaded = None

        # If pdf_path is a URL, download it first
        if isinstance(pdf_path, str) and pdf_path.lower().startswith("http"):
            try:
                print(f"🔽 Downloading remote PDF: {pdf_path}")
                rpath = self._download_remote_file(pdf_path)
                temp_downloaded = rpath
                pdf_path = rpath
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
                try:
                    os.remove(temp_downloaded)
                except Exception:
                    pass


    def verify_image(self):
        """
        Verify and load image into an OpenCV (BGR) numpy array.
        Supports:
         - local file paths
         - http/https image URLs (downloads to temp file)
         - PIL fallback if cv2.imread fails
        Sets self.image_path to local path when a download occurred.
        """
        print("🔍 Verifying image...")
        # If image_path is a remote URL, download it first
        if isinstance(self.image_path, str) and self.image_path.lower().startswith(("http://", "https://")):
            try:
                print(f"🔽 Detected remote image URL, downloading: {self.image_path}")
                downloaded = self._download_remote_file(self.image_path)
                self.image_path = downloaded
            except Exception as e:
                raise FileNotFoundError(f"❌ Could not download remote image: {e}")

        # Expand user and normalize path
        if isinstance(self.image_path, str):
            self.image_path = os.path.expanduser(self.image_path)

        # Basic existence check
        if isinstance(self.image_path, str) and not os.path.exists(self.image_path):
            raise FileNotFoundError(f"❌ Image file not found at path: {self.image_path}")

        # Try cv2.imread first
        img = cv2.imread(self.image_path, cv2.IMREAD_COLOR)
        # If cv2 failed to load, try PIL
        if img is None:
            try:
                print("⚠️ cv2.imread failed — attempting to open with PIL as fallback.")
                pil_img = Image.open(self.image_path).convert("RGB")
                img = np.array(pil_img)[:, :, ::-1]  # RGB -> BGR
            except Exception as e:
                raise FileNotFoundError(f"❌ Could not read the image (cv2 and PIL failed): {e}")

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
            medicines = []
            entities = json.loads(json_text)
            print("\n================ MEDICAL ENTITIES FOUND ================")
            for e in entities:
                entity_obj = {
                    "entity": e.get("entity", "N/A"),
                    "type": e.get("type", "N/A")
                }
                if entity_obj["type"].upper() in ["DRUG", "MEDICINE", "MEDICATION"]:
                    medicines.append(entity_obj["entity"])

                print(f"- Entity: \"{e.get('entity','N/A')}\", Type: {e.get('type','N/A')}")
            print("Medicines: ",medicines)
            print("========================================================")
            return medicines

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
        finally:
            # cleanup any single-file download created during processing
            try:
                if getattr(self, "_temp_downloaded", None) and os.path.exists(self._temp_downloaded):
                    os.remove(self._temp_downloaded)
            except Exception:
                pass

# --- Example Usage ---
if __name__ == "__main__":
    image_path = "Doctors_Prescription_Note.pdf"  # Make sure this file exists in your working directory
    gcp_key_path = "heroic-dynamo-473510-q9-936d0b6e305a.json"  # Replace with your actual key file
    gemini_api_key = "AIzaSyAh0g0SF0NFvbhLDiOXPLGp-JhBBvmDS4c"  # Replace with your actual Gemini API key

    pipeline = MedicalOCRPipeline(image_path, gcp_key_path, gemini_api_key)
    pipeline.run()
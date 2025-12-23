import os
import io
import tempfile
import requests
import pymupdf as fitz
import json
from google.cloud import vision
import google.generativeai as genai

class PDFPathologyPipeline:
    def __init__(self, pdf_path, gcp_key_path, gemini_api_key):
        self.pdf_path = pdf_path
        self.gcp_key_path = gcp_key_path
        self.gemini_api_key = gemini_api_key
        self.image_dir = "pdf_pages"
        self.ocr_text = ""
        self.entities = []
        # track any remote download (image/pdf) to clean up later
        self._temp_downloaded = None

    def configure_gcp(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.gcp_key_path
        print("✅ GCP credentials configured.")

    def configure_gemini(self):
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        print("✅ Gemini API configured.")

    def _download_remote_file(self, url: str) -> str:
        """
        Download remote URL (PDF or image) to a temp file and return local path.
        Sets self._temp_downloaded to the path so caller can clean up later.
        """
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Could not download file from URL: {e}")

        ct = resp.headers.get("content-type", "").lower()
        suffix = ".jpg"
        if "pdf" in ct or url.lower().endswith(".pdf"):
            suffix = ".pdf"
        elif "jpeg" in ct or url.lower().endswith((".jpg", ".jpeg")):
            suffix = ".jpg"
        elif "png" in ct or url.lower().endswith(".png"):
            suffix = ".png"
        elif "tiff" in ct or url.lower().endswith((".tif", ".tiff")):
            suffix = ".tiff"

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

        # If pdf_path is a URL, download it first (will detect pdf vs image)
        if isinstance(pdf_path, str) and pdf_path.lower().startswith(("http://", "https://")):
            try:
                print(f"🔽 Downloading remote file: {pdf_path}")
                rpath = self._download_remote_file(pdf_path)
                temp_downloaded = rpath
                pdf_path = rpath
            except Exception as e:
                raise RuntimeError(f"❌ Could not download remote file from URL: {e}")

        # If the provided path is an image (local or downloaded), return it directly
        lower = str(pdf_path).lower()
        if lower.endswith((".png", ".jpg", ".jpeg", ".tiff", ".tif")):
            print("🖼 Detected image input — returning single image path for OCR.")
            return [pdf_path]

        try:
            doc = fitz.Document(pdf_path)
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
            # if we downloaded a PDF earlier, remove it now; if we downloaded an image, keep it
            if temp_downloaded and temp_downloaded.lower().endswith(".pdf"):
                try:
                    os.remove(temp_downloaded)
                except Exception:
                    pass

    def run_ocr_on_images(self, image_paths):
        print("🔍 Running OCR on images...")
        client = vision.ImageAnnotatorClient()

        for path in image_paths:
            with open(path, "rb") as img_file:
                content = img_file.read()
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)

            if response.error.message:
                print(f"❌ Error on {path}: {response.error.message}")
                continue

            text = response.full_text_annotation.text
            self.ocr_text += f"\n\n--- Page: {path} ---\n{text}"

        print("✅ OCR complete.")

    def run_gemini_ner(self):
        print("🧠 Running Gemini NER...")
        if not self.ocr_text.strip():
            print("❌ No OCR text available for NER.")
            return []

        prompt = f"""
You are a biomedical text mining expert.

Analyze the following pathology report and extract medically relevant terms such as:
- Diagnoses
- Tumor types and grades
- Biomarkers
- Specimen types
- Clinical findings

Return a JSON list of objects with:
- "entity": the term
- "type": category like DIAGNOSIS, GRADE, BIOMARKER, SPECIMEN, etc.

Text:
---
{self.ocr_text}
---
"""
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip().replace("```json", "").replace("```", "")
            self.entities = json.loads(json_text)
            print("\n🧠 Extracted Medical Entities:")
            for e in self.entities:
                print(f"- {e.get('entity')} ({e.get('type')})")
        except Exception as e:
            print(f"❌ Gemini NER error: {e}")
            self.entities = []

    def run(self):
        try:
            self.configure_gcp()
            self.configure_gemini()
            image_paths = self.convert_pdf_to_images()
            self.run_ocr_on_images(image_paths)
            self.run_gemini_ner()
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
        finally:
            # Cleanup any temp download (image or pdf) if present
            try:
                if getattr(self, "_temp_downloaded", None) and os.path.exists(self._temp_downloaded):
                    os.remove(self._temp_downloaded)
            except Exception:
                pass
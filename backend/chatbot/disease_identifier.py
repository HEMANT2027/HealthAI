import json
import re
import google.generativeai as genai
from typing import Tuple, List,Any
from dotenv import load_dotenv
import os
load_dotenv()

class GeminiDiseaseExtractor:
    def __init__(self, api_key: str):
        """
        Initialize the Gemini API client with the provided API key.
        
        Args:
            api_key: Your Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def extract_diseases(self, medgemma_output: str) -> Tuple[str, List[str]]:
        """
        Extract symptoms and suspected diseases from MedGemma output using Gemini API.
        
        Args:
            medgemma_output: The text output from MedGemma model
            
        Returns:
            Tuple containing (symptoms_string, suspected_diseases_list)
        """
        prompt = f"""You are a medical text parser. Extract symptoms and suspected diseases from the following clinical report.

Clinical Report:
{medgemma_output}

Instructions:
1. Extract ALL symptoms from the "Subjective" and "Objective" sections
2. Extract ALL suspected diseases from the "Working Impression" section
3. Format symptoms as a comma-separated string
4. Format suspected diseases as a Python list

Output format (copy exactly, no other text):
symptoms = "symptom1, symptom2, symptom3"
suspected = ["Disease1", "Disease2"]

Example output:
symptoms = "High-grade fever, Productive cough, Shortness of breath, Chest pain, Fatigue"
suspected = ["Community-Acquired Pneumonia"]

Now extract from the clinical report above and provide ONLY the two output lines in the exact format shown.
"""
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse the response to extract symptoms and suspected diseases
            symptoms = self._extract_symptoms(response_text)
            suspected = self._extract_suspected(response_text)
            
            return symptoms, suspected
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # Fallback: try to parse directly from medgemma output
            return self._fallback_parse(medgemma_output)
    
    def _extract_symptoms(self, text: str) -> str:
        """Extract symptoms string from Gemini response."""
        # Try to find symptoms = "..." pattern (most common)
        match = re.search(r'symptoms\s*=\s*"([^"]+)"', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Alternative pattern with colon
        match = re.search(r'symptoms\s*:\s*"([^"]+)"', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try without quotes (fallback)
        match = re.search(r'symptoms\s*=\s*(.+?)(?:\n|suspected|$)', text, re.IGNORECASE | re.DOTALL)
        if match:
            symptoms_text = match.group(1).strip().strip('"').strip("'")
            return symptoms_text
        
        return ""
    
    def _extract_suspected(self, text: str) -> List[str]:
        """Extract suspected diseases list from Gemini response."""
        # Try to find suspected = [...] pattern (most common)
        match = re.search(r'suspected\s*=\s*\[(.*?)\]', text, re.IGNORECASE | re.DOTALL)
        if match:
            diseases_str = match.group(1)
            # Parse the list items (handle both quoted and unquoted)
            diseases = re.findall(r'"([^"]+)"', diseases_str)
            if not diseases:
                # Try unquoted items
                diseases = [d.strip() for d in diseases_str.split(',') if d.strip()]
            return [d.strip() for d in diseases if d.strip()]
        
        # Alternative pattern with colon
        match = re.search(r'suspected\s*:\s*\[(.*?)\]', text, re.IGNORECASE | re.DOTALL)
        if match:
            diseases_str = match.group(1)
            diseases = re.findall(r'"([^"]+)"', diseases_str)
            if not diseases:
                diseases = [d.strip() for d in diseases_str.split(',') if d.strip()]
            return [d.strip() for d in diseases if d.strip()]
        
        return []
    
    def _fallback_parse(self, medgemma_output: str) -> Tuple[str, List[str]]:
        """Fallback parsing directly from MedGemma output if Gemini fails."""
        symptoms = []
        suspected = []
        
        # Extract symptoms from Subjective section
        subjective_match = re.search(r'Subjective:.*?(?=Objective:|$)', medgemma_output, re.IGNORECASE | re.DOTALL)
        if subjective_match:
            subjective_text = subjective_match.group(0)
            # Extract bullet points (lines starting with * or -)
            bullet_points = re.findall(r'[*•-]\s+([^\n]+)', subjective_text)
            for point in bullet_points:
                # Clean up the symptom text
                symptom = point.strip()
                if symptom and len(symptom) > 5:  # Filter out very short items
                    symptoms.append(symptom)
        
        # Also check Objective section for symptoms
        objective_match = re.search(r'Objective.*?(?=Pathology:|Imaging:|Working|Treatment|$)', medgemma_output, re.IGNORECASE | re.DOTALL)
        if objective_match:
            objective_text = objective_match.group(0)
            # Extract notable findings
            findings = re.findall(r'[*•-]\s+([^\n]+(?:breath|crackles|sounds|pain|fever|temperature)[^\n]*)', objective_text, re.IGNORECASE)
            symptoms.extend([f.strip() for f in findings if f.strip()])
        
        # Extract suspected diseases from Working Impression
        impression_match = re.search(r'Working Impression:.*?(?=Treatment|Follow-up|Important|$)', medgemma_output, re.IGNORECASE | re.DOTALL)
        if impression_match:
            impression_text = impression_match.group(0)
            # Extract disease names after "Suspected"
            disease_matches = re.findall(r'Suspected\s+([A-Z][^–\n*]+?)(?:\s+–|\(|\.|\n|\*)', impression_text, re.IGNORECASE)
            for disease in disease_matches:
                disease_clean = disease.strip().rstrip('.').rstrip(',')
                if disease_clean and len(disease_clean) > 3:
                    suspected.append(disease_clean)
        
        # Clean up symptoms - remove duplicates and format
        symptoms_clean = list(dict.fromkeys(symptoms))  # Remove duplicates while preserving order
        symptoms_str = ", ".join(symptoms_clean[:15]) if symptoms_clean else ""
        
        return symptoms_str, suspected


# Example usage function
def parse_medgemma_output(medgemma_text:Any, api_key: str) -> Tuple[str, List[str]]:
    """
    Simple function to parse MedGemma output and extract symptoms and suspected diseases.
    
    Args:
        medgemma_text: The text output from MedGemma
        api_key: Gemini API key
        
    Returns:
        Tuple of (symptoms_string, suspected_diseases_list)
    """
    print("IN DISEASE IDENTIFIER")
    extractor = GeminiDiseaseExtractor(api_key)
    symptoms, suspected = extractor.extract_diseases(medgemma_text)
    return symptoms, suspected

if __name__ == "__main__":
    # Your Gemini API key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Example MedGemma output
    example_medgemma_output = """Okay, here's a summary of the clinical findings, integrating information from the prescription OCR, pathology report, and provided chest x-ray image.

Patient Summary:

*   Name: Mr. Thomas A. Chen
*   Age: 50
*   Presenting Complaint: 5-day history of worsening respiratory symptoms.

Clinical Findings:

*   Subjective:
    *   High-grade fever (up to 103°F) for 3 days, poorly responsive to OTC medication.
    *   Productive cough with greenish-yellow sputum.
    *   Shortness of breath (dyspnea) with mild exertion.
    *   Right-sided pleuritic chest pain (worsened by deep breaths).
    *   Fatigue, chills, and muscle aches.
*   Objective (Vitals & Exam):
    *   Temperature: 102.8°F
    *   Respiratory Rate: 24 breaths/min
    *   SpO2: 93% on room air
    *   Chest Auscultation: Decreased breath sounds and coarse crackles over the right lower lobe.
*   Pathology:
    *   Respiratory PCR Panel (Sputum): Negative for Influenza A, Influenza B, and Rhinovirus.
*   Imaging (Chest X-ray): Analysis of the provided image suggests significant consolidation in the right lower lobe. The lung field appears opacified, and vascular markings are obscured. This is highly suggestive of pneumonia.

Working Impression:

*   Suspected Community-Acquired Pneumonia (CAP) – ICD-10 Code J18.9
*   The negative viral PCR panel makes a bacterial etiology more likely, supporting the initial suspicion.

Treatment Plan (as prescribed):

*   Azithromycin 500mg daily for 5 days (Macrolide antibiotic)
*   Acetaminophen 650mg PRN for fever (>101°F) or pain.
*   Dextromethorphan/Guaifenesin syrup 10ml TDS.
*   Strict bed rest and increased fluid intake.

Follow-up:

*   Review investigation results in 48 hours.
*   Warning signs: seek emergency care for worsening chest pain, difficulty breathing, or cyanosis.



Important Considerations:

*   The chest x-ray findings are consistent with pneumonia. 
*   The patient has risk factors for CAP (age, clinical presentation).
*   The initial treatment plan targeting bacterial CAP is appropriate, given the clinical presentation and the negative viral PCR results.



Disclaimer: I am an AI assistant and cannot provide medical advice. This analysis is based on the provided information and images and should be reviewed and interpreted by a qualified healthcare professional."""
    
    # Extract symptoms and suspected diseases
    symptoms, suspected = parse_medgemma_output(example_medgemma_output, GEMINI_API_KEY)
    
    # Output in the requested format
    print(f'symptoms = "{symptoms}"')
    print(f'suspected = {suspected}')
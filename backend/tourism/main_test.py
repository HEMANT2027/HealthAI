import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Step 1: Securely load API Key ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
#print(API_KEY) works

if not API_KEY:
    raise ValueError("🔴 GEMINI_API_KEY not found. Please check your .env file.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro')
print("✅ Successfully configured Gemini API")

# --- Step 2: Load and Merge Your Data ---
try:
    with open("data/patient_profile.json", "r") as f:
        patients = json.load(f)

    with open("data/medical_info.json", "r") as f:
        medical_profile = json.load(f)
except FileNotFoundError as e:
    print(f"🔴 Error: {e}. Make sure your JSON files are in a 'data' subfolder.")
    exit()
    
# --- NEW: Create an 'output' directory if it doesn't exist ---
output_dir = "output"
os.makedirs(output_dir, exist_ok=True) # <--- 2. CREATE FOLDER

medical_dict = {m["patient"]: m for m in medical_profile}


# --- Step 3: Loop Through Patients and Call the API ---
print("\nProcessing patient data to generate itineraries...\n" + "="*50)

for patient in patients:
    pid = patient.get("patient")
    medical = medical_dict.get(pid, {})

    # --- CORRECTED: user_profile_details based on your specified fields ---
    user_profile_details = f"""
    --- Patient Profile ---
    Name: {patient.get('fullName', 'N/A')}
    Age: {patient.get('age', 'N/A')}
    Country: {patient.get('country', 'N/A')}
    Budget: ${patient.get('budget', 'N/A')}
    Sightseeing: {patient.get('hasSightseeing', 'N/A')} ({patient.get('sightseeingDays', 0)} days)
    Preferences: {', '.join(patient.get('sightseeingPrefs', [])) or 'None'}

    --- Medical Profile ---
    Treatment Type: {medical.get('treatmentType', 'N/A')}
    Notes: {patient.get('notes', 'None')}
    """

    # --- CORRECTED: Full prompt contained within the script properly ---
    prompt = f"""
    You are a medical travel itinerary assistant. 
    Your task is to recommend hospitals in India and generate a detailed itinerary for a patient traveling for treatment, based on their nationality, dietary restrictions, and recovery needs.

    ### USER PROFILE
    {user_profile_details}

    ### TASK DETAILS
    1.Recommend 2–3 top hospitals in India that specialize in treating the patient's condition and accept international patients.
    2. For each hospital, include:
    - Name, location, and accreditation (NABH/JCI if applicable)
    - Specialty relevant to the condition
    - Average cost of treatment (approximate)
    - Contact or website (if available)
    3. Create a full itinerary for the patient including:
    - Day of arrival
    - Pre-operation checkup
    - Operation day
    - Recovery period (mention whether the patient can step outside or needs rest)
    - Post-recovery sightseeing plan (based on mobility and health)
    4. Recommend **local places to visit** near the hospital during the recovery phase, filtered by:
    - Accessibility (light walking or drive)
    - Dietary compatibility (e.g., halal food nearby)
    - Cultural/religious comfort (based on nationality and diet)

    5. Mention whether **hospital staff or nearby accommodations** can provide meals matching the dietary restrictions.

    6. Format your output in clear, structured text or JSON:
    ```json
    {{
    "HospitalRecommendations": [
        {{
        "Name": "",
        "City": "",
        "Accreditation": "",
        "Specialization": "",
        "ApproxTreatmentCost": "",
        "Website": ""
        }}
    ],
    "Itinerary": [
        {{
        "Day": "",
        "Activity": "",
        "Notes": ""
        }}
    ],
    "RecoveryAndSightseeing": [
        {{
        "Place": "",
        "WhyRecommended": "",
        "NearbyDietaryOptions": ""
        }}
    ]
    }}
    """
    # try:
    #     print(f"\n👤 Generating itinerary for {patient.get('fullName')}...")
    
    #     # Call the API
    #     response = model.generate_content(prompt)
        
    #     # Print the result
    #     print("💡 Gemini's Itinerary:")
    #     print(response.text)
    #     print("-"*50)
    # except Exception as e:
    #     print(f"🔴 An error occurred while calling the Gemini API for {patient.get('fullName')}: {e}")
    

    try:
        print(f"\n👤 Generating itinerary for {patient.get('fullName')}...")
        response = model.generate_content(prompt)
        
        try:
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            itinerary_json = json.loads(clean_text)
            
            # --- 3. CREATE A UNIQUE FILENAME AND SAVE THE JSON ---
            patient_name = patient.get('fullName', 'Unknown_Patient').replace(' ', '_')
            filename = f"{patient_name}_itinerary.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(itinerary_json, f, indent=4)
            
            print(f"✅ Itinerary successfully saved to: {filepath}")
            # --------------------------------------------------------
            
        except json.JSONDecodeError:
            print("🔴 Failed to parse response as JSON. Skipping file save.")
            print(response.text)

    except Exception as e:
        print(f"🔴 An error occurred while calling the Gemini API for {patient.get('fullName')}: {e}")

print("\n✨ All patients processed.")

from Connections.patient_workflow import PatientWorkflow
from Connections.Mongo_connect import get_mongo_connection
from datetime import datetime
import io,os
from dotenv import load_dotenv
load_dotenv() 

file_path = r"C:\Users\HP\Desktop\HEALTH-AI AQ\ChatGPT Image Oct 2, 2025, 02_06_11 PM.png"

workflow = PatientWorkflow()
mongo = get_mongo_connection()
test_id = f"P-TEST-{datetime.now().strftime('%M%S')}"


class MockFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)

    async def read(self):
        with open(self.file_path, "rb") as f:
            return f.read()

async def test_file_upload():
    mock_file = MockFile(file_path)
    
    result = await workflow.doctor_uploads_file(
        doctor_id="DR-TEST",
        patient_pseudonym=test_id,
        uploaded_file=mock_file,
        file_type="imaging",          # ✅ mark it as image-type
        chief_complaint="Chest X-ray upload"
    )
    
    if result['success']:
        print(f"✅ Image uploaded successfully")
        print(f"   Ingest ID: {result['ingest_id']}")
    else:
        print("❌ Image upload failed")
        
        
# Runs async test for storing image in S3
import asyncio
asyncio.run(test_file_upload())

print("\n" + "=" * 70)
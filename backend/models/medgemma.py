import boto3
import base64
import json
from PIL import Image
from io import BytesIO
from typing import Any

class MedGemmaMultiInputClient:
    def __init__(self, endpoint_name, region_name="eu-north-1"):
        self.endpoint_name = endpoint_name
        self.region_name = region_name
        self.runtime = boto3.client("sagemaker-runtime", region_name=self.region_name)

    def encode_image(self, image_path):
        with open(image_path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

    def build_payload(self, system_prompt, doctor_prompt, prescription_text, pathology_text, image_paths, max_tokens=256):
        # Combine all text inputs into one user message
        combined_text = (
            f"Doctor's prompt: {doctor_prompt}\n\n"
            f"Prescription OCR:\n{prescription_text}\n\n"
            f"Pathology OCR:\n{pathology_text}\n\n"
            "Please analyze the image(s) in context of the above information."
        )

        content: list[dict[str, Any]]  = [{"type": "text", "text": combined_text}]
        for path in image_paths:
            content.append({
                "type": "image_url",
                "image_url": {"url": self.encode_image(path)}
            })

        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            "max_tokens": max_tokens
        }

    def invoke(self, payload):
        response = self.runtime.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType="application/json",
            Body=json.dumps(payload)
        )
        result = json.loads(response["Body"].read().decode())
        return result["choices"][0]["message"]["content"]
    


if __name__ == "__main__":
    client = MedGemmaMultiInputClient(endpoint_name="jumpstart-dft-hf-vlm-gemma-3-27b-in-20251028-060633")

    prescription_text = "Tab Paracetamol 500mg twice daily for 5 days"
    pathology_text = "Histology shows dense lymphocytic infiltration with atypical nuclei"
    doctor_prompt = "Summarize findings and suggest possible diagnosis in a well descriptive manner and after that summarize all cases in bullet points, be considerate about every possible case"
    image_paths = ["3.jpg"]

    payload = client.build_payload(
        system_prompt="You are a helpful medical assistant",
        doctor_prompt=doctor_prompt,
        prescription_text=prescription_text,
        pathology_text=pathology_text,
        image_paths=image_paths,
        max_tokens=1024
    )

    response = client.invoke(payload)
    print("🧠 MedGemma Response:\n", response)
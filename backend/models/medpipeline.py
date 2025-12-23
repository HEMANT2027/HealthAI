#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MAIN MEDPIPELINE

Steps:
1. OCR (Vision API)
2. Gemini NER
3. Drug name typo correction + RxNorm canonicalization
4. RxNav DDI + AutoGraph fallback
5. PubMed RAG grounding (single stage)
"""

import os
import json
from typing import Dict, Any, List
from dataclasses import dataclass

from .ocr_ner import MedicalOCRPipeline
from .ddi_engine import DDIPipeline
from chatbot.tool2 import PubMedRetriever

MAX_GEMINI_SUGGESTIONS = 5  # SAFETY CAP

# -------------------------------------------------------------------
@dataclass
class PipelineOutput:
    ocr_text: str
    extracted: List[str]
    suggested: List[str]
    canonicalized: List[Dict]
    interactions: List[Dict]
    pubmed_docs: List[Dict]

# -------------------------------------------------------------------
class MainPipeline:

    def __init__(self, gcp_key: str, gemini_key: str):
        self.gcp_key = gcp_key
        self.gemini_key = gemini_key
        self.ddi = DDIPipeline()

    def run(self, image_path: str) -> Dict[str, Any]:
        print(f"\n{'='*70}")
        print("🚀 MAIN MEDPIPELINE STARTED")
        print(f"{'='*70}")
        print(f"📄 Image path: {image_path}")

        # ---------------- STEP 1: OCR + NER ----------------
        print("\n========== STEP 1: OCR + NER ==========")
        print(f"🔍 Running OCR pipeline...")
        
        ocr = MedicalOCRPipeline(
            image_path=image_path,
            gcp_key_path=self.gcp_key,
            gemini_api_key=self.gemini_key
        )
        ocr.run()

        extracted = ocr.medicines or []
        suggested = getattr(ocr, "suggested_medicines", [])[:MAX_GEMINI_SUGGESTIONS]

        print(f"\n✅ OCR Complete:")
        print(f"   - Text length: {len(ocr.full_text or '')} chars")
        print(f"   - Extracted medicines: {len(extracted)} → {extracted}")
        print(f"   - Suggested medicines: {len(suggested)} → {suggested}")

        # Only check extracted medicines for DDI (not suggested alternatives)
        print(f"\n========== STEP 2: DDI ENGINE ==========")
        print(f"🔧 Checking DDI for {len(extracted)} extracted medicines only")
        all_drugs = list(dict.fromkeys(extracted + suggested))

        # ---------------- STEP 2: DDI ENGINE ----------------
        ddi_out = self.ddi.run(all_drugs)

        print(f"\n✅ DDI Check Complete:")
        print(f"   - Canonicalized drugs: {len(ddi_out['canonicalized'])}")
        print(f"   - Interactions found: {len(ddi_out['interactions'])}")

        # ---------------- STEP 3: PUBMED (FINAL GROUNDING ONLY) ----------------
        print("\n========== STEP 3: PUBMED RAG ==========")
        
        retriever = PubMedRetriever(email="healthai589@gmail.com")
        pubmed_docs = []
        
        if ddi_out["interactions"]:
            # Get unique drug names from interactions
            drug_names = set()
            for interaction in ddi_out["interactions"]:
                drug_names.add(interaction.get("drugA", ""))
                drug_names.add(interaction.get("drugB", ""))
            
            q = ", ".join([d for d in drug_names if d])
            print(f"📚 Searching PubMed for: {q[:100]}...")
            
            pubmed_docs = retriever.to_rag_format(
                retriever.search_pubmed(q, max_results=3)
            )
            print(f"✅ PubMed search complete: {len(pubmed_docs)} documents retrieved")
        else:
            print(f"⚠️ No interactions found, skipping PubMed search")

        print(f"\n{'='*70}")
        print("✅ MAIN MEDPIPELINE COMPLETE")
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   - OCR text: {len(ocr.full_text or '')} chars")
        print(f"   - Extracted medicines (checked for DDI): {len(extracted)}")
        print(f"   - Suggested medicines (alternatives): {len(suggested)}")
        print(f"   - DDI interactions: {len(ddi_out['interactions'])}")
        print(f"   - PubMed docs: {len(pubmed_docs)}")
        print(f"{'='*70}\n")

        return PipelineOutput(
            ocr_text=ocr.full_text or "",
            extracted=extracted,
            suggested=suggested,
            canonicalized=ddi_out["canonicalized"],
            interactions=ddi_out["interactions"],
            pubmed_docs=pubmed_docs
        ).__dict__

# -------------------------------------------------------------------
if __name__ == "__main__":
    pipeline = MainPipeline(
        gcp_key="service-key.json",
        gemini_key=os.getenv("GEMINI_API_KEY")
    )

    out = pipeline.run("prescription.jpg")
    print(json.dumps(out, indent=2))
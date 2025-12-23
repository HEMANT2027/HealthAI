#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DDI ENGINE — RxNorm + RxNav + AutoGraph (no DrugBank)

Pipeline:
1. Normalize & typo-correct drug names (RxNorm)
2. Canonicalize to RxCUI
3. RxNav pairwise interaction check
4. AutoGraph mechanistic inference (enzyme / AE)
5. Evidence + explanation output
"""

import os
import re
import time
import json
import requests
from typing import List, Dict, Optional
from difflib import SequenceMatcher
from dataclasses import dataclass

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

# -------------------------------------------------------------------
# RxNorm API (with typo correction)
# -------------------------------------------------------------------
class RxNormAPI:
    BASE = "https://rxnav.nlm.nih.gov/REST"

    @staticmethod
    def approximate_term(name: str) -> Optional[str]:
        """Fix OCR typos using RxNorm approximate matching"""
        try:
            url = f"{RxNormAPI.BASE}/approximateTerm.json?term={requests.utils.quote(name)}&maxEntries=1"
            r = requests.get(url, timeout=10).json()
            candidates = r.get("approximateGroup", {}).get("candidate", [])
            if candidates:
                return candidates[0]["rxcui"]
        except Exception:
            pass
        return None

    @staticmethod
    def lookup_exact(name: str) -> Optional[str]:
        try:
            url = f"{RxNormAPI.BASE}/rxcui.json?name={requests.utils.quote(name)}"
            r = requests.get(url, timeout=10).json()
            ids = r.get("idGroup", {}).get("rxnormId", [])
            return ids[0] if ids else None
        except Exception:
            return None

    @staticmethod
    def properties(rxcui: str) -> Dict:
        try:
            url = f"{RxNormAPI.BASE}/rxcui/{rxcui}/properties.json"
            return requests.get(url, timeout=10).json().get("properties", {})
        except Exception:
            return {}

# -------------------------------------------------------------------
# Drug Canonicalizer (TYPO FIX + CONFIDENCE)
# -------------------------------------------------------------------
class DrugCanonicalizer:

    def normalize(self, raw_name: str) -> Dict:
        if not raw_name or not raw_name.strip():
            return {
                "raw": raw_name,
                "canonical": raw_name,
                "rxcui": None,
                "confidence": 0.0
            }
        
        cleaned = re.sub(r"[^\w\s]", "", raw_name)
        candidates = [raw_name, cleaned, norm(cleaned)]

        rxcui = None
        for c in candidates:
            if not c.strip():
                continue
            rxcui = RxNormAPI.lookup_exact(c)
            if rxcui:
                break
            time.sleep(0.1)

        # fallback: typo correction
        if not rxcui:
            rxcui = RxNormAPI.approximate_term(raw_name)

        if not rxcui:
            return {
                "raw": raw_name,
                "canonical": raw_name,
                "rxcui": None,
                "confidence": 0.2
            }

        props = RxNormAPI.properties(rxcui)
        canon_name = props.get("name", raw_name)

        conf = max(similarity(canon_name, c) for c in candidates if c.strip())

        return {
            "raw": raw_name,
            "canonical": canon_name,
            "rxcui": f"RXCUI:{rxcui}",
            "confidence": round(max(conf, 0.85), 2)
        }

# -------------------------------------------------------------------
# RxNav DDI (PAIRWISE ONLY — FIXED)
# -------------------------------------------------------------------
class RxNavDDI:

    BASE = "https://rxnav.nlm.nih.gov/REST/interaction/interaction.json"

    def check_pair(self, rxcui_a: str, rxcui_b: str) -> Optional[Dict]:
        try:
            url = f"{self.BASE}?rxcui={rxcui_a.replace('RXCUI:', '')}"
            data = requests.get(url, timeout=10).json()
            groups = data.get("interactionTypeGroup", [])

            for g in groups:
                for t in g.get("interactionType", []):
                    for p in t.get("interactionPair", []):
                        ids = {p["interactionConcept"][0]["minConceptItem"]["rxcui"],
                               p["interactionConcept"][1]["minConceptItem"]["rxcui"]}
                        if rxcui_b.replace("RXCUI:", "") in ids:
                            return {
                                "severity": p.get("severity", "unknown"),
                                "description": p.get("description", "")
                            }
        except Exception:
            pass
        return None

# -------------------------------------------------------------------
# AutoGraph (Lightweight KG)
# -------------------------------------------------------------------
@dataclass
class AutoGraph:
    enzyme_rules = {
        "statin": ("SUBSTRATE_OF", "CYP3A4"),
        "clarithromycin": ("INHIBITS", "CYP3A4"),
        "erythromycin": ("INHIBITS", "CYP3A4"),
        "fluconazole": ("INHIBITS", "CYP2C9"),
        "warfarin": ("SUBSTRATE_OF", "CYP2C9")
    }

    def infer(self, drugA: Dict, drugB: Dict) -> Optional[Dict]:
        a = drugA["canonical"].lower()
        b = drugB["canonical"].lower()

        for k, (relA, enz) in self.enzyme_rules.items():
            if k in a:
                for k2, (relB, enz2) in self.enzyme_rules.items():
                    if k2 in b and enz == enz2:
                        return {
                            "mechanism": f"{drugA['canonical']} ({relA}) & {drugB['canonical']} ({relB}) via {enz}",
                            "severity": "moderate",
                            "confidence": 0.65
                        }
        return None

# -------------------------------------------------------------------
# DDI PIPELINE
# -------------------------------------------------------------------
class DDIPipeline:

    def __init__(self):
        self.canon = DrugCanonicalizer()
        self.rxnav = RxNavDDI()
        self.autograph = AutoGraph()

    def run(self, drugs: List[str]) -> Dict:
        print(f"\n{'='*60}")
        print("🚀 DDI PIPELINE STARTED")
        print(f"{'='*60}")
        
        if not drugs:
            print("⚠️ No drugs provided for DDI check")
            return {
                "canonicalized": [],
                "interactions": []
            }
        
        # Step 1: Canonicalize drug names
        print(f"\n📋 Step 1: Canonicalizing {len(drugs)} drug names...")
        canonicalized = []
        for d in drugs:
            print(f"🔄 Normalizing: {d}")
            result = self.canon.normalize(d)
            canonicalized.append(result)
            if result["rxcui"]:
                print(f"   ✅ {d} → {result['canonical']} ({result['rxcui']}, confidence: {result['confidence']})")
            else:
                print(f"   ⚠️ {d} → No RXCUI found (confidence: {result['confidence']})")
        
        valid = [d for d in canonicalized if d["rxcui"]]
        print(f"\n✅ Canonicalization complete: {len(valid)}/{len(drugs)} drugs have valid RxCUI")

        if len(valid) < 2:
            print("⚠️ Less than 2 valid drugs, skipping DDI check")
            return {
                "canonicalized": canonicalized,
                "interactions": []
            }

        interactions = []

        # Step 2: RxNav pairwise interaction check
        print(f"\n⚠️ Step 2: Checking DDI via RxNav (pairwise)...")
        pairs_checked = 0
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                pairs_checked += 1
                drugA = valid[i]["canonical"]
                drugB = valid[j]["canonical"]
                print(f"🔍 Checking: {drugA} ↔ {drugB}")
                
                hit = self.rxnav.check_pair(valid[i]["rxcui"], valid[j]["rxcui"])
                if hit:
                    print(f"   ⚠️ INTERACTION FOUND: {hit['severity']}")
                    interactions.append({
                        "drugA": drugA,
                        "drugB": drugB,
                        **hit,
                        "source": "RxNav"
                    })
                else:
                    print(f"   ✅ No interaction")
                
                time.sleep(0.2)  # Rate limiting
        
        print(f"\n✅ RxNav check complete: {len(interactions)} interactions found from {pairs_checked} pairs")

        # Step 3: AutoGraph fallback (only if no RxNav hits)
        if not interactions:
            print(f"\n🔍 Step 3: No RxNav hits, trying AutoGraph reasoning...")
            for i in range(len(valid)):
                for j in range(i + 1, len(valid)):
                    kg = self.autograph.infer(valid[i], valid[j])
                    if kg:
                        print(f"   🧠 Inferred: {valid[i]['canonical']} ↔ {valid[j]['canonical']}")
                        interactions.append({
                            "drugA": valid[i]["canonical"],
                            "drugB": valid[j]["canonical"],
                            **kg,
                            "source": "AutoGraph"
                        })
            print(f"✅ AutoGraph reasoning complete: {len(interactions)} interactions inferred")
        else:
            print(f"\n✅ Step 3: Skipping AutoGraph (RxNav found {len(interactions)} interactions)")

        print(f"\n{'='*60}")
        print(f"✅ DDI PIPELINE COMPLETE")
        print(f"   - Total interactions: {len(interactions)}")
        print(f"{'='*60}\n")

        return {
            "canonicalized": canonicalized,
            "interactions": interactions
        }

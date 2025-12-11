import os
import json
import requests
from dotenv import load_dotenv
load_dotenv() 

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "YOUR_TAVILY_API_KEY")

def medical_query_search(query: str, num_results: int = 5) -> dict:
    """
    Generalized web search for ANY medical question using Tavily.
    Returns structured JSON.
    """

    if not TAVILY_API_KEY or "YOUR_TAVILY_API_KEY" in TAVILY_API_KEY:
        raise ValueError("Set TAVILY_API_KEY (env var or in code).")

    url = "https://api.tavily.com/search"

    payload = {
        "query": query,
        "max_results": num_results,
        "include_answer": True,
        "include_domains": [
            # Medical-reliable sources (optional)
            "nih.gov",
            "mayoclinic.org",
            "who.int",
            "cdc.gov",
            "clevelandclinic.org"
        ],
        "search_depth": "advanced"
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TAVILY_API_KEY}"
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Clean JSON format
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title"),
            "snippet": item.get("content"),
            "url": item.get("url")
        })

    return {
        "query": query,
        "result_count": len(results),
        "results": results
    }

if __name__ == "__main__":
    q = input("Enter your medical query: ").strip()
    output = medical_query_search(q)
    print(json.dumps(output, ensure_ascii=False, indent=2))


""""query": "\"what is the treatment for pneumonia?\"",
  "result_count": 1,
  "results": [
    {
      "title": "Implementing Community-Based Strategies for Improved ...",
      "snippet": "by M Selvi · 2024 · Cited by 1 — What Is The Treatment For Pneumonia? Antibiotic Medications, Oxygen Therapy, Pain Killer Medication, Both A And B. D, Observational Checklist",
      "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11015882/"
    }"""

#for advanced queries 
"""Enter your medical query: latest covid variants 2025?
{
  "query": "latest covid variants 2025?",
  "result_count": 5,
  "results": [
    {
      "title": "COVID-19 variants | WHO COVID-19 dashboard - WHO Data",
      "snippet": "Earliest documented samples\n  \n01 July 2024\n\nDate of designation\n  \n24 January 2025\n\nNextstrain clade\n  \n25B\n\nGenetic features\n  \nJN1 + S:T22N, S:F59S, S:G184S,S:A435S, S:F456L, S:T478I, S:Q493E\n\nEarliest documented samples\n  \n22 January 2025\n\nDate of designation\n  \n23 May 2025\n\nNextstrain clade\n  \n25C\n\nGenetic features\n  \nJN1 + S:T22N, S:S31P, S:K182R, S:R190S, S:R346T, S:K444R, S:V445R, S:F456L, S:N487D, S:Q493E, S:T572I\n\nEarliest documented samples\n  \n27 January 2025 [...] | Pango lineage XFG | Nextstrain clade  25C  Genetic features  JN1 + S:T22N, S:S31P, S:K182R, S:R190S, S:R346T, S:K444R, S:V445R, S:F456L, S:N487D, S:Q493E, S:T572I  Earliest documented samples  27 January 2025  Date of designation  25 June 2025   Risk assessment 25 June 2025  XFG Initial Risk Evaluation | [...] Genetic features\n  \nBA.2.86 + S:L455S\n\nEarliest documented samples\n  \n25-08-2023\n\nDate of designation\n  \n18-12-2023\n\n## Currently circulating COVID-19 Variants under Monitoring (VUMs) as of 4 September 2025",
      "url": "https://data.who.int/dashboards/covid19/variants"
    },
    {
      "title": "Rapid Emergence and Evolution of SARS-CoV-2 Intrahost ...",
      "snippet": "|  |  |\n --- |\n| EID | Su Y, Zeller MA, Cronin P, Zhang R, Zhuang Y, Ma J, et al. Rapid Emergence and Evolution of SARS-CoV-2 Intrahost Variants among COVID-19 Patients with Prolonged Infections, Singapore. Emerg Infect Dis. 2025;31(8):1537-1549.  |\n| AMA | Su Y, Zeller MA, Cronin P, et al. Rapid Emergence and Evolution of SARS-CoV-2 Intrahost Variants among COVID-19 Patients with Prolonged Infections, Singapore. Emerging Infectious Diseases. 2025;31(8):1537-1549. doi:10.3201/eid3108.241419. | [...] ##### Volume 31, Number 8—August 2025\n\n#### Volume 31, Number 8—August 2025\n\n##### Research\n\n### Rapid Emergence and Evolution of SARS-CoV-2 Intrahost Variants among COVID-19 Patients with Prolonged Infections, Singapore\n\nHelp Icon\nComments to Author\n\nCite This Article\n\n### Abstract [...] | APA | Su, Y., Zeller, M. A., Cronin, P., Zhang, R., Zhuang, Y., Ma, J....Smith, G. (2025). Rapid Emergence and Evolution of SARS-CoV-2 Intrahost Variants among COVID-19 Patients with Prolonged Infections, Singapore. Emerging Infectious Diseases, 31(8), 1537-1549.  |",
      "url": "https://wwwnc.cdc.gov/eid/article/31/8/24-1419_article"
    },
    {
      "title": "SARS-CoV-2 Variant XEC Increases as KP.3.1.1 Slows",
      "snippet": "Many minor variants of SARS-CoV-2, the virus that causes COVID-19, that are descended from the JN.1 variant are co-circulating heading into winter of 2024–2025. The 2024–2025 COVID-19 vaccine will reduce your risk of severe illness and protect against the variants most common now and those likely to be common in the future.\n\n### What CDC is doing [...] The 2024–2025 COVID-19 vaccine was updated to better protect you against the COVID-19 variants circulating now. The U.S. Food and Drug Administration looked at data on which COVID-19 variants were circulating and how widespread each variant was. The FDA used this information to recommend including JN.1 antigen, and the vaccine is expected to work well against variants that are predominant now (for example, KP.3.1.1). It is also expected to work well against the variants that are increasing and [...] likely to be predominant in the future, such as XEC or MC.1.",
      "url": "https://www.cdc.gov/ncird/whats-new/sars-cov-2-variant-xec-increases-as-kp-3-1-1-slows.html"
    },
    {
      "title": "Staying Up to Date with COVID-19 Vaccines",
      "snippet": "Three vaccines are available for use in the United States. There is no preference for one vaccine over the other when more than one vaccine is recommended for an age group.\n\nVaccine\n\nCan be given to:\n\n2025–2026 Moderna COVID-19 Vaccine: Spikevax\n\nAnyone ages 6 months and older\n\n2025–2026 Moderna COVID-19 Vaccine: mNexspike\n\n2025–2026 Pfizer-BioNTech COVID-19 Vaccine: Comirnaty\n\nAnyone ages 5 years and older\n\n2025–2026 Novavax COVID-19 Vaccine: Nuvaxovid\n\nAnyone ages 12 years and older [...] CDC recommends a 2025-2026 COVID-19 vaccine for people ages 6 months and older based on individual-based decision-making.\n\n### Resource\n\nCDC's Childhood Immunization Schedule\n\nCDC's Adult Immunization Schedule\n\n### People who are moderately or severely immunocompromised\n\nThere are different recommendations if you are moderately or severely immunocompromised; see Vaccines for Moderately to Severely Immunocompromised People.\n\n### People who recently had COVID-19\n\n## Available COVID-19 Vaccines",
      "url": "https://www.cdc.gov/covid/vaccines/stay-up-to-date.html"
    },
    {
      "title": "Current Epidemic Trends (Based on R t ) for States",
      "snippet": "As of November 25, 2025, we estimate that COVID-19 infections are growing or likely growing in 17 states, declining or likely declining in 12 states, and not changing in 16 states. Previous estimates can be found on data.cdc.gov.\n\n## Influenza\n\nAs of November 25, 2025, we estimate that Influenza infections are growing or likely growing in 41 states, declining or likely declining in 0 states, and not changing in 3 states. Previous estimates can be found on data.cdc.gov.\n\n## RSV [...] The second figure below shows the estimated Rt and uncertainty interval from October 1, 2025 through November 25, 2025 for the U.S. and for each reported state. (Click on the map to view the data for a specific state). While Rt tells us if the number of infections is likely growing or declining, it does not reflect the burden of disease.",
      "url": "https://www.cdc.gov/cfa-modeling-and-forecasting/rt-estimates/index.html"
    }
  ]
}"""
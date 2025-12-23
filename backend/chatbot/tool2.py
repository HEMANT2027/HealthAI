"""
Minimal PubMed tester for RAG
- Searches PubMed 
- Returns structured + RAG-ready docs
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from Bio import Entrez  # pip install biopython
from .types import MessageState


@dataclass
class MedicalDocument:
    title: str
    abstract: str
    authors: List[str]
    journal: str
    publication_year: str
    pmid: str
    doi: str
    source_type: str = "pubmed"
    full_text_url: Optional[str] = None


class PubMedRetriever:
    """
    Very small, test-focused PubMed retriever
    """

    def __init__(self, email: str, api_key: Optional[str] = None):
        """
        Args:
            email: Your email for NCBI Entrez (required)
            api_key: NCBI API key (optional but recommended)
        """
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key

    def search_pubmed(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[MedicalDocument]:
        """
        Search PubMed and return a small list of MedicalDocument objects
        """
        docs: List[MedicalDocument] = []

        if not query:
            print("[WARN] Empty query passed to PubMed search.")
            return docs

        try:
            # 1) Search PubMed
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
            )
            record = Entrez.read(handle)
            handle.close()

            id_list = record.get("IdList", [])
            if not id_list:
                print("No results found.")
                return docs

            # 2) Fetch full records
            handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="medline",
                retmode="xml",
            )
            records = Entrez.read(handle)
            handle.close()

            for article in records.get("PubmedArticle", []):
                try:
                    medline = article["MedlineCitation"]
                    article_data = medline["Article"]

                    # Title
                    title = str(article_data.get("ArticleTitle", ""))

                    # Authors
                    authors: List[str] = []
                    if "AuthorList" in article_data:
                        for author in article_data["AuthorList"]:
                            if "LastName" in author and "ForeName" in author:
                                authors.append(
                                    f"{author['ForeName']} {author['LastName']}"
                                )

                    # Abstract
                    abstract = ""
                    if "Abstract" in article_data:
                        abstract_texts = article_data["Abstract"].get(
                            "AbstractText", []
                        )
                        if isinstance(abstract_texts, list):
                            abstract = " ".join(str(t) for t in abstract_texts)
                        else:
                            abstract = str(abstract_texts)

                    # Journal
                    journal = ""
                    journal_info = article_data.get("Journal")
                    if isinstance(journal_info, dict):
                        journal = str(journal_info.get("Title", ""))

                    # Year
                    year = ""
                    if "ArticleDate" in article_data and article_data["ArticleDate"]:
                        year = article_data["ArticleDate"][0].get("Year", "")
                    elif "DateCompleted" in medline:
                        year = medline["DateCompleted"].get("Year", "")
                    elif "DateCreated" in medline:
                        year = medline["DateCreated"].get("Year", "")

                    # PMID
                    pmid = str(medline.get("PMID", ""))

                    # DOI
                    doi = ""
                    pubmed_data = article.get("PubmedData", {})
                    for aid in pubmed_data.get("ArticleIdList", []):
                        if aid.attributes.get("IdType") == "doi":
                            doi = str(aid)
                            break

                    # URL
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                    docs.append(
                        MedicalDocument(
                            title=title,
                            abstract=abstract,
                            authors=authors,
                            journal=journal,
                            publication_year=year,
                            pmid=pmid,
                            doi=doi,
                            full_text_url=url,
                        )
                    )
                except Exception as e:
                    print(f"[WARN] Error parsing one article: {e}")
                    continue

        except Exception as e:
            print(f"[ERROR] PubMed search error: {e}")

        return docs

    def to_rag_format(self, docs: List[MedicalDocument]) -> List[Dict[str, Any]]:
        """
        Convert to simple RAG-compatible dicts: {content, metadata}
        """
        rag_docs: List[Dict[str, Any]] = []

        for d in docs:
            content = f"{d.title}\n\n{d.abstract}"
            metadata = {
                "source": d.source_type,
                "pmid": d.pmid,
                "doi": d.doi,
                "journal": d.journal,
                "authors": ", ".join(d.authors[:3]),
                "year": d.publication_year,
                "url": d.full_text_url,
            }
            rag_docs.append({"content": content, "metadata": metadata})

        return rag_docs


def run_pubmed_demo(state: MessageState) -> MessageState:
    """
    Runs a PubMed search using PubMedRetriever and stores results in dedicated state fields.
    Searches based on suspected conditions from the patient's medical state.
    """
    print("\n" + "="*60)
    print("📚 PUBMED SEARCH")
    print("="*60)
    
    email = "healthai589@gmail.com"
    api_key = None  # set if needed 

    suspected = state.get("suspected", "")
    print(f"📥 Suspected (raw): {suspected} (type: {type(suspected)})")
    
    # Convert suspected to search query string
    if isinstance(suspected, list):
        query = ", ".join(str(s) for s in suspected if s)
    elif isinstance(suspected, dict):
        query = str(suspected)
    else:
        query = str(suspected) if suspected else ""
    
    print(f"🔍 Search query: '{query}'")
    
    if not query or query.strip() == "":
        print("⚠️ Empty query, skipping PubMed search")
        state["pubmed_results"] = []
        state["pubmed_rag_docs"] = []
        state["pubmed_query"] = ""
        print("="*60 + "\n")
        return state

    print(f"🌐 Searching PubMed for: '{query}'...")
    retriever = PubMedRetriever(email=email, api_key=api_key)
    docs = retriever.search_pubmed(query, max_results=3)
    
    print(f"✅ Found {len(docs)} articles")

    if not docs:
        print("⚠️ No articles found")
        state["pubmed_results"] = []
        state["pubmed_rag_docs"] = []
        state["pubmed_query"] = query
        print("="*60 + "\n")
        return state

    # Store responses as list of dictionaries
    results: List[Dict[str, Any]] = []

    for i, d in enumerate(docs, start=1):
        result = {
            "index": i,
            "title": d.title,
            "authors": d.authors[:3],
            "journal": d.journal,
            "year": d.publication_year,
            "pmid": d.pmid,
            "doi": d.doi,
            "url": d.full_text_url,
            "abstract": d.abstract[:200] + "..." if len(d.abstract) > 200 else d.abstract,
        }
        results.append(result)
        print(f"   {i}. {d.title[:80]}... ({d.publication_year})")

    # Store RAG-formatted documents as well
    rag_docs = retriever.to_rag_format(docs)

    # Store in dedicated fields (not messages)
    state["pubmed_results"] = results
    state["pubmed_rag_docs"] = rag_docs
    state["pubmed_query"] = query
    
    print(f"✅ PubMed search complete - {len(results)} articles stored")
    print("="*60 + "\n")

    return state

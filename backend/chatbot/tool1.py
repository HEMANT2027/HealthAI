from typing import Any, Dict, List, Optional
import numpy as np
from langchain.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from .types import MessageState

def _to_readable(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return "\n".join(
                f"{i+1}. " + ", ".join(f"{k}={val}" for k, val in item.items())
                for i, item in enumerate(v)
            )
        return "\n".join(f"- {x}" for x in v)
    if isinstance(v, dict):
        return "\n".join(f"- {k}: {val}" for k, val in v.items())
    return str(v)


class SimpleVectorStore:
    def __init__(self, embedding_fn):
        self.embedding_fn = embedding_fn
        self.docs = []

    def add(self, texts: List[str]):
        if not texts:
            return
        embs = self.embedding_fn.embed_documents(texts)
        for t, e in zip(texts, embs):
            self.docs.append({"text": t, "embedding": np.array(e, float)})

    def search(self, query: str, k: int = 3):
        if not self.docs or not query:
            return []
        q_emb = np.array(self.embedding_fn.embed_query(query), float)
        qn = np.linalg.norm(q_emb)
        if qn == 0:
            return []
        scored = []
        for d in self.docs:
            sim = float(np.dot(q_emb, d["embedding"]) /
                        (qn * np.linalg.norm(d["embedding"]) + 1e-8))
            scored.append((sim, d["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"page_content": t, "score": float(s)} for s, t in scored[:k]]


splitter = RecursiveCharacterTextSplitter(
    chunk_size=900,
    chunk_overlap=120,
    add_start_index=True,
)


@tool
def message_contexter(state: dict) -> Dict[str, Any]:
    """
    Builds clinical context, retrieves relevant chunks, and optionally generates a model response.

    IMPORTANT:
    - Does NOT modify state.
    - Returns final_response ONLY in the returned dict.
    - Graph should assign: state["messages"] = out["final_response"]
    """
    parts = []

    if state.get("ocr_result"):
        parts.append("OCR:\n" + _to_readable(state["ocr_result"]))
    if state.get("ner_result"):
        parts.append("NER:\n" + _to_readable(state["ner_result"]))
    if state.get("pathology_report"):
        parts.append("PATHOLOGY:\n" + _to_readable(state["pathology_report"]))
    if state.get("medgemma_report"):
        parts.append("MED-GEMMA:\n" + _to_readable(state["medgemma_report"]))
    # if state.get("fused_report"):
    #     parts.append("FUSED:\n" + _to_readable(state["fused_report"]))
    if state.get("symptoms"):
        parts.append("SYMPTOMS:\n" + _to_readable(state["symptoms"]))
    if state.get("suspected"):
        parts.append("SUSPECTED:\n" + _to_readable(state["suspected"]))
    if state.get("medicines"):
        parts.append("MEDICINES:\n" + _to_readable(state["medicines"]))
    if state.get("analyze_medications"):
        parts.append("MEDICATION ANALYSIS:\n" + _to_readable(state["analyze_medications"]))
    if state.get("suggest_tests"):
        parts.append("SUGGESTED TESTS:\n" + _to_readable(state["suggest_tests"]))

    blob = "\n\n".join(parts)

    if not blob.strip():
        return {
            "context_blob": "",
            "splits": [],
            "splits_count": 0,
            "retrieved": [],
            "warning": "No clinical content found.",
            "final_response": None
        }

    splits = splitter.split_text(blob)

    # Vector retrieval with ONLY LangChain's OpenAIEmbeddings
    embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small")
    vs = SimpleVectorStore(embedding_fn)
    vs.add(splits)

    query = state.get("rewritten_query") or state.get("original_query") or ""
    retrieved = vs.search(query, k=5)

    result = {
        "context_blob": blob,
        "splits": splits,
        "splits_count": len(splits),
        "retrieved": retrieved,
        "warning": None if retrieved else "No matches found.",
        "final_response": None
    }

    # If start_chat=False → no LLM call
    if not state.get("start_chat"):
        return result

    # Run LLM
    prompt = ChatPromptTemplate.from_template(
        """
You are a clinical RAG assistant.
Query: {query}

Context:
{context}

Answer concisely and clinically.
"""
    )

    llm = ChatAnthropic(
        model="claude-3-haiku-latest",
        temperature=0,
        max_tokens=200
    )

    chain = prompt | llm | StrOutputParser()

    context_text = "\n\n".join(
        x["page_content"] for x in retrieved
    ) if retrieved else blob

    response = chain.invoke({
        "query": query,
        "context": context_text
    })

    result["final_response"] = response
    return result


# ✅ What your graph should now do:
# After calling message_contexter(state):
# out = message_contexter.invoke(state)
#
# # you decide what to do with output
# state["messages"] = out["final_response"]
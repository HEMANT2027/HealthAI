from __future__ import annotations
import json
import os
import operator
from typing import Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from .graph_health import build_health_rag_graph
from .tool1 import message_contexter  
from .tool2 import run_pubmed_demo
from .tool3_advance import medical_query_search
from .types import MessageState

class AgentState(TypedDict, total=False):
    """
    State carried through the LangGraph execution.
    You can extend this as needed.
    """
    user_question: str
    message_state: MessageState

    selected_tool: str  
    reasoning_log: Annotated[List[str], operator.add]
    tool_output: Any
    final_answer: str

LLM_MODEL_NAME = os.getenv("HEALTH_AGENT_MODEL", "gpt-4o-mini")
router_llm = ChatOpenAI(model=LLM_MODEL_NAME, temperature=0)
answer_llm = ChatOpenAI(model=LLM_MODEL_NAME, temperature=0)

import traceback

def _ensure_message_state_dict(obj: Any) -> Dict:
    """
    Ensure the returned object is a dict-like MessageState.
    Try common extraction attempts (result(), output, .data), otherwise raise TypeError.
    """
    if isinstance(obj, dict):
        return obj

    for attr in ("result", "output", "data"):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            try:
                val = val() if callable(val) else val
            except Exception:
                pass
            if isinstance(val, dict):
                return val

    if callable(obj):
        try:
            maybe = obj()
            if isinstance(maybe, dict):
                return maybe
        except Exception:
            pass

    raise TypeError(
        "preprocess_node expected a dict-like MessageState from build_health_rag_graph, "
        f"but got {type(obj)}. Inspect the graph's return type."
    )

def _normalize_message_state(ms: Dict) -> Dict:
    """
    Ensure the MessageState contains the expected keys with safe default types.
    This prevents KeyError/type mismatches downstream.
    """
    defaults = {
        "original_query": "",
        "rewritten_query": "",
        "messages": [],
        "image_path": None,
        "pdf_path": None,
        "ocr_result": "",
        "ner_result": [],
        "pathology_report": [],
        "medgemma_report": "",
        "llm_report": [],
        "analyze_medications": "",
        "suggest_tests": "",
        "suspected": [],
        "symptoms": [],
        "medicines": [],
        "suggested_medicines": [],
        "pubmed_results": [],
        "pubmed_rag_docs": [],
        "pubmed_query": "",
        "web_search_results": [],
        "web_search_query": "",
    }
    for k, dv in defaults.items():
        if k not in ms or ms[k] is None:
            ms[k] = dv
        else:
            if k in ("suspected", "symptoms", "ner_result", "pathology_report", "messages", "medicines", "suggested_medicines"):
                if not isinstance(ms[k], list):
                    if isinstance(ms[k], str):
                        ms[k] = [ms[k]] if ms[k] else []
                    else:
                        try:
                            ms[k] = list(ms[k])
                        except Exception:
                            ms[k] = [ms[k]]
            else:
                pass
    return ms

from typing import Any, Dict

def make_preprocess_node(build_health_rag_graph):
    """
    Returns a node function with the expected signature: node(state) -> state.
    The returned node will call build_health_rag_graph (callable or compiled .invoke)
    and place the normalized message_state and reasoning_log into the returned state.
    """
    def preprocess_node(state: Dict[str, Any]) -> Dict[str, Any]:
        reasoning_log: List[str] = []
        message_state = state.get("message_state", {"original_query": state.get("user_question", "")})
        
        # Check if message_state is already populated from MongoDB
        has_cached_data = (
            message_state.get("medicines") or
            message_state.get("suspected") or
            message_state.get("symptoms") or
            message_state.get("ocr_result")
        )
        
        print(f"\n{'='*60}")
        print("🔄 PREPROCESS NODE")
        print(f"{'='*60}")
        print(f"📦 Input message_state keys: {list(message_state.keys())}")
        print(f"   - medicines: {len(message_state.get('medicines', []))} items - {message_state.get('medicines', [])}")
        print(f"   - suggested_medicines: {len(message_state.get('suggested_medicines', []))} items - {message_state.get('suggested_medicines', [])}")
        print(f"   - suspected: {message_state.get('suspected')}")
        print(f"   - symptoms: {message_state.get('symptoms')}")
        print(f"   - has_cached_data: {has_cached_data}")
        
        # Skip graph processing if data already loaded from MongoDB
        if has_cached_data:
            print("✅ Data already loaded from MongoDB, skipping graph processing")
            processed = _normalize_message_state(message_state)
            state["message_state"] = processed
            state["reasoning_log"] = state.get("reasoning_log", []) + ["Skipped preprocessing - using cached data"]
            print(f"✅ Normalized state keys: {list(processed.keys())}")
            print(f"   - medicines: {len(processed.get('medicines', []))} items - {processed.get('medicines', [])}")
            print(f"   - suggested_medicines: {len(processed.get('suggested_medicines', []))} items - {processed.get('suggested_medicines', [])}")
            print(f"{'='*60}\n")
            return state
        
        # Run graph if no cached data
        print("⚠️ No cached data, running full preprocessing graph...")
        try:
            if hasattr(build_health_rag_graph, "invoke") and callable(build_health_rag_graph.invoke):
                ret = build_health_rag_graph.invoke(message_state)
                reasoning_log.append("Called build_health_rag_graph.invoke(message_state)")
            elif callable(build_health_rag_graph):
                ret = build_health_rag_graph(message_state)
                reasoning_log.append("Called build_health_rag_graph(message_state)")
            else:
                raise TypeError("build_health_rag_graph is not callable and has no .invoke")
            try:
                processed = _ensure_message_state_dict(ret)
            except Exception:
                processed = {}
                if isinstance(ret, dict):
                    processed = ret
                else:
                    processed = getattr(ret, "output", None) or getattr(ret, "result", None) or {}
                    if callable(processed):
                        try:
                            processed = processed()
                        except Exception:
                            processed = {}
                    if not isinstance(processed, dict):
                        processed = {"internal_ret": ret}

            processed = _normalize_message_state(processed)
            processed.setdefault("original_query", message_state.get("original_query", ""))

            state["message_state"] = processed
            prev_log = state.get("reasoning_log", []) or []
            state["reasoning_log"] = prev_log + reasoning_log
            return state

        except Exception as e:
            tb = traceback.format_exc()
            state["message_state"] = _normalize_message_state({"original_query": message_state.get("original_query", "")})
            prev_log = state.get("reasoning_log", []) or []
            state["reasoning_log"] = prev_log + [f"preprocess error: {e}"]
            state["preprocess_error"] = str(e)
            state["_preprocess_traceback"] = tb
            return state

    return preprocess_node

def router_node(state: AgentState) -> AgentState:
    """
    LLM-based router that:
    - Reads user_question and a brief summary of available data in message_state
    - Picks ONE tool
    - Logs its reasoning in `reasoning_log`
    - Sets selected_tool
    """
    question = state.get("user_question", "").strip()
    msg_state: MessageState = state.get("message_state", {})  # type: ignore[assignment]
    suspected = msg_state.get("suspected")
    symptoms = msg_state.get("symptoms")
    combined_text = " ".join(
        [
            str(state.get("user_question", "") or ""),
            str(msg_state.get("ocr_result", "") or ""),
            str(msg_state.get("medgemma_report", "") or ""),
            str(msg_state.get("original_query", "") or ""),
        ]
    ).lower()
    has_clinical_blob = bool(suspected) or bool(symptoms)

    tool_descriptions = """
        You can choose exactly ONE of the following tools:

        1) message_contexter
        - Input: the full MessageState (OCR, NER, fused clinical summary, symptoms, medicines, etc.).
        - Use when: you want to build / refine clinical context, retrieve relevant chunks from the
            patient's data, and optionally generate a concise clinical answer using that RAG context.
        - Good for: questions like "summarize this case", "what is likely diagnosis from this report?",
            "explain the abnormalities in this patient's findings", etc.

        2) pubmed_search
        - Implementation: run_pubmed_demo(MessageState)
        - It looks at MessageState['suspected'] (e.g., 'pneumonia', 'DVT') and performs a PubMed
            literature search, returning a list of structured medical articles and RAG-formatted docs.
        - Use when: the user is asking for supporting literature, latest evidence, or scientific backing
            for a suspected disease or condition.
        - Good for: "find PubMed papers on <disease>", "what recent evidence exists for treatment of X?"

        3) medical_web_search
        - Implementation: medical_query_search(question)
        - Uses Tavily to search the medical web (NIH, Mayo Clinic, WHO, CDC, etc.) for the given query.
        - Use when: the user asks general medical questions (definition, treatment, guidelines, variants,
            etc.) that should be answered from reputable online medical sources.
        - Good for: "what is the treatment for pneumonia?", "latest COVID variants 2025?", etc.
        """

    state_brief = f"""
        Clinical state snapshot:
        - suspected: {suspected!r}
        - symptoms: {symptoms!r}
        - has_clinical_data: {bool(has_clinical_blob)}
        """
    print("STATE BRIEF:", state_brief)
    router_system = (
        "You are a routing expert for a medical AI system. "
        "Your job is ONLY to choose the most appropriate tool and explain WHY."
    )
    router_user = f"""
        User question:
        {question}

        {state_brief}

        {tool_descriptions}

        Return your answer STRICTLY as JSON with the following keys:
        - "tool_name": one of "message_contexter", "pubmed_search", "medical_web_search"
        - "reason": a short explanation of WHY this tool is best for this question.
        """

    try:
        resp = router_llm.invoke(
            [
                {"role": "system", "content": router_system},
                {"role": "user", "content": router_user},
            ]
        )
    except Exception as e:
        prev_log = state.get("reasoning_log", []) or []
        state["reasoning_log"] = prev_log + [f"ROUTER ERROR: {e}"]
        state["selected_tool"] = "medical_web_search"
        return state

    content = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    reason = f"Could not parse router output. Raw: {content}"

    # Enhanced debug logging
    print(f"\n{'='*60}")
    print("🔍 ROUTER NODE DEBUG")
    print(f"{'='*60}")
    print(f"📥 Raw LLM response (first 500 chars):\n{content[:500]}")
    print(f"📊 Clinical state: suspected={suspected}, symptoms={symptoms}, has_data={has_clinical_blob}")

    try:
        parsed = json.loads(content)
        print(f"✅ Successfully parsed JSON: {parsed}")
        t = parsed.get("tool_name", "medical_web_search")
        print(f"📌 Extracted tool_name: '{t}'")
        
        if t not in {"message_contexter", "pubmed_search", "medical_web_search", "none"}:
            print(f"⚠️  Invalid tool name '{t}', defaulting to message_contexter")
            t = "message_contexter"  # Default to message_contexter instead of none
        tool_name = t
        reason = parsed.get("reason", reason)
    except Exception as e:
        # Try regex fallback to extract tool name from text
        import re
        content_lower = content.lower()
        for possible_tool in ["message_contexter", "pubmed_search", "medical_web_search"]:
            if possible_tool in content_lower:
                tool_name = possible_tool
                reason = f"Extracted {tool_name} from text (JSON parse failed)"
                print(f"🔧 Fallback: Found '{tool_name}' in response text")
                break
        
    prev_log = state.get("reasoning_log", []) or []
    state["selected_tool"] = tool_name
    state["reasoning_log"] = prev_log + [f"ROUTER: chose {tool_name!r} because: {reason}"]
    
    print(f"✅ FINAL DECISION: selected_tool = '{tool_name}'")
    print(f"📝 Reason: {reason}")
    print(f"{'='*60}\n")
    
    return state

def message_contexter_node(state: AgentState) -> AgentState:
    """
    Calls your @tool `message_contexter` using the current MessageState.
    """
    msg_state: MessageState = state.get("message_state", {})  # type: ignore[assignment]
    try:
        tool_result = message_contexter.invoke({"state": msg_state})
    except Exception as e:
        prev_log = state.get("reasoning_log", []) or []
        state["tool_output"] = {"tool": "message_contexter", "error": str(e)}
        state["reasoning_log"] = prev_log + [f"TOOL ERROR: message_contexter failed: {e}"]
        return state

    prev_log = state.get("reasoning_log", []) or []
    state["tool_output"] = {
        "tool": "message_contexter",
        "raw": tool_result,
    }
    state["reasoning_log"] = prev_log + ["TOOL: ran message_contexter"]
    return state

def pubmed_node(state: AgentState) -> AgentState:
    """
    Calls `run_pubmed_demo`, which:
      - looks at MessageState['suspected'] for disease/condition name
      - performs PubMed search
      - stores results back into MessageState['messages'].
    """
    msg_state: MessageState = state.get("message_state", {})  # type: ignore[assignment]
    try:
        updated_state = run_pubmed_demo(msg_state)
        
    except Exception as e:
        prev_log = state.get("reasoning_log", []) or []
        state["tool_output"] = {"tool": "pubmed_search", "error": str(e)}
        state["reasoning_log"] = prev_log + [f"TOOL ERROR: pubmed_search failed: {e}"]
        return state

    updated_state = _normalize_message_state(updated_state if isinstance(updated_state, dict) else {})
    prev_log = state.get("reasoning_log", []) or []
    state["message_state"] = updated_state
    state["tool_output"] = {
        "tool": "pubmed_search",
        "query": updated_state.get("pubmed_query", ""),
        "results_count": len(updated_state.get("pubmed_results", [])),
        "raw": updated_state.get("pubmed_results", []),
    }
    state["reasoning_log"] = prev_log + [f"TOOL: ran pubmed_search - found {len(updated_state.get('pubmed_results', []))} articles"]
    return state

def tavily_node(state: AgentState) -> AgentState:
    """
    Calls `medical_query_search` directly with user_question.
    Stores web search results in message_state for frontend display.
    """
    question = state.get("user_question", "")
    msg_state: MessageState = state.get("message_state", {})  # type: ignore[assignment]
    
    try:
        search_result = medical_query_search(question)
        
        # Store web search results in message_state
        msg_state["web_search_results"] = search_result.get("results", [])
        msg_state["web_search_query"] = search_result.get("query", question)
        state["message_state"] = msg_state
        
    except Exception as e:
        prev_log = state.get("reasoning_log", []) or []
        state["tool_output"] = {"tool": "medical_web_search", "error": str(e)}
        state["reasoning_log"] = prev_log + [f"TOOL ERROR: medical_web_search failed: {e}"]
        return state

    prev_log = state.get("reasoning_log", []) or []
    state["tool_output"] = {
        "tool": "medical_web_search",
        "raw": search_result,
        "results_count": len(search_result.get("results", [])),
    }
    state["reasoning_log"] = prev_log + [f"TOOL: ran medical_web_search via Tavily - found {len(search_result.get('results', []))} results"]
    return state

def route_after_router(state: AgentState) -> Literal["message_contexter_node", "pubmed_node", "tavily_node", "finalize"]:
    """
    Conditional edge after router_node:
    Decide which node to go to next based on `selected_tool`.
    """
    tool_name = state.get("selected_tool", "medical_web_search")
    if tool_name == "message_contexter":
        return "message_contexter_node"
    if tool_name == "pubmed_search":
        return "pubmed_node"
    if tool_name == "medical_web_search":
        return "tavily_node"
    return "finalize"

def finalize_node(state: AgentState) -> AgentState:
    """
    Uses the router reasoning + tool output to generate a final, user-facing answer.
    Also extracts sources from message_state for frontend display.
    """
    question = state.get("user_question", "")
    reasoning_log = state.get("reasoning_log", [])
    tool_output = state.get("tool_output")
    msg_state: MessageState = state.get("message_state", {})  # type: ignore[assignment]

    log_text = "\n".join(reasoning_log) if reasoning_log else "No explicit reasoning log."
    tool_text = json.dumps(tool_output, ensure_ascii=False, indent=2) if tool_output is not None else "No tool was called."

    system_msg = (
        "You are a careful clinical & medical assistant.\n"
        "- You MUST NOT give definitive diagnoses or prescriptions.\n"
        "- Use the provided tool output as context.\n"
        "- Be clear about uncertainty and advise consulting a qualified clinician.\n"
        "- Keep the answer crisp, focused and clinically sound."
    )

    user_msg = f"""
User question:
{question}

Router/tool reasoning log:
{log_text}

Structured tool output:
{tool_text}

Now, write a concise answer for the user:
- First, answer their question as well as you can from the context.
- Then, briefly mention (in plain language) how you used the tools.
- Finally, include a short disclaimer that this is not a substitute for professional medical advice.
"""

    try:
        resp = answer_llm.invoke(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
        )
    except Exception as e:
        prev_log = state.get("reasoning_log", []) or []
        state["final_answer"] = f"Error generating final answer: {e}"
        state["reasoning_log"] = prev_log + [f"FINALIZE ERROR: {e}"]
        return state

    final = resp.content if isinstance(resp.content, str) else json.dumps(resp.content, ensure_ascii=False)
    state["final_answer"] = final
    
    # Extract sources for frontend display
    sources = []
    
    # Add PubMed sources
    pubmed_results = msg_state.get("pubmed_results", [])
    for result in pubmed_results:
        sources.append({
            "type": "pubmed",
            "title": result.get("title", ""),
            "url": result.get("url", ""),
        })
    
    # Add web search sources
    web_results = msg_state.get("web_search_results", [])
    for result in web_results:
        sources.append({
            "type": "web",
            "title": result.get("title", ""),
            "url": result.get("url", ""),
        })
    
    state["sources"] = sources
    
    print(f"\n📚 SOURCES EXTRACTED: {len(sources)} total")
    for i, src in enumerate(sources, 1):
        print(f"   {i}. [{src['type'].upper()}] {src['url']}")
    
    return state

def build_health_agent_graph():
    """
    Builds a LangGraph StateGraph with:
    START -> router_node -> (tool node OR finalize) -> finalize -> END
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("preprocess", make_preprocess_node(build_health_rag_graph))
    workflow.add_node("router", router_node)
    workflow.add_node("message_contexter_node", message_contexter_node)
    workflow.add_node("pubmed_node", pubmed_node)
    workflow.add_node("tavily_node", tavily_node)
    workflow.add_node("finalize", finalize_node)

    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "router")
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        ["message_contexter_node", "pubmed_node", "tavily_node", "finalize"],
    )
    workflow.add_edge("message_contexter_node", "finalize")
    workflow.add_edge("pubmed_node", "finalize")
    workflow.add_edge("tavily_node", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()

if __name__ == "__main__":
    """
    Minimal CLI demo:

    - Asks for a user question
    - Initializes a bare MessageState (only original_query / suspected filled)
    - Runs the graph
    - Prints final answer and debug info
    """
    agent = build_health_agent_graph()
    user_q = input("what is the disease all about ").strip()
    base_message_state: MessageState = {
        "original_query": user_q,
        "suspected": user_q,
    }  # type: ignore[typeddict-item]

    init_state: AgentState = {
        "user_question": user_q,
        "message_state": base_message_state,
        "reasoning_log": [],
    }

    result = agent.invoke(init_state)

    print("\n=== FINAL ANSWER ===\n")
    print(result.get("final_answer", "[No final_answer in state]"))

    print("\n=== DEBUG: ROUTER / TOOL LOG ===")
    for line in result.get("reasoning_log", []):
        print("-", line)

    print("\n=== DEBUG: SELECTED TOOL ===")
    print(result.get("selected_tool"))

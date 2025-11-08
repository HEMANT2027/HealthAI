from graph_health import health_rag_graph_with_memory, MessageState
import uuid

# ============================================================
# 🩺 HealthAI Interactive CLI (With Conversation Memory)
# ============================================================

print("\n💬 HealthAI Interactive Chat (With Conversation Memory)")
print("=" * 60)
thread_id = str(uuid.uuid4())
print(f"\n🔗 Thread ID: {thread_id}")
print("(Use this thread_id in FastAPI to continue this conversation)\n")

import json

def extract_healthai_response(result, debug=False):
    """
    Extract the final meaningful text response from a HealthAI LangGraph result.
    Handles dicts, JSON-like strings, AIMessage lists, and plain text.
    Always returns clean natural-language text.
    """

    if debug:
        print("\n[DEBUG] Type of result:", type(result))
        try:
            print("[DEBUG] Raw Result Preview:", json.dumps(result, indent=2, default=str))
        except Exception:
            print("[DEBUG] Raw Result (non-serializable):", result)

    # Case 1: Graph returned a dict
    if isinstance(result, dict):
        # Priority fields
        for key in ["fused_report", "medgemma_report", "llm_report"]:
            val = result.get(key)
            if val:
                # Handle LLM message lists
                if isinstance(val, list) and len(val) > 0:
                    last_msg = val[-1]
                    if hasattr(last_msg, "content"):
                        return last_msg.content.strip()
                    elif isinstance(last_msg, dict):
                        return last_msg.get("content", "").strip()
                if isinstance(val, str):
                    # Remove accidental JSON wrappers
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, dict):
                            return (
                                parsed.get("text")
                                or parsed.get("response")
                                or parsed.get("answer")
                                or str(parsed)
                            ).strip()
                    except json.JSONDecodeError:
                        pass
                    return val.strip()

        # fallback for dict with no known key
        return json.dumps(result, indent=2)

    # Case 2: AIMessage or BaseMessage
    if hasattr(result, "content"):
        return result.content.strip()

    # Case 3: Plain string or stringified JSON
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return (
                    parsed.get("text")
                    or parsed.get("response")
                    or parsed.get("answer")
                    or str(parsed)
                ).strip()
        except json.JSONDecodeError:
            pass
        return result.strip()

    # Default fallback
    return str(result)

# ============================================================
# 🧩 Utility: Extract Final AI Response
# ============================================================
def extract_healthai_response(result, debug=False):
    """
    Extract the final meaningful text response from a HealthAI LangGraph result.
    Handles dicts, AIMessage lists, and fallback strings.
    """

    if debug:
        print("\n[DEBUG] Type of result:", type(result))
        if isinstance(result, dict):
            print("[DEBUG] Keys available:", list(result.keys()))

    # Case 1: Graph returned a dict
    if isinstance(result, dict):
        # ✅ Priority order
        if result.get("fused_report"):
            return result["fused_report"].strip()

        if result.get("medgemma_report"):
            return result["medgemma_report"].strip()

        if result.get("llm_report"):
            llm_report = result["llm_report"]
            if isinstance(llm_report, list) and len(llm_report) > 0:
                last_msg = llm_report[-1]
                if hasattr(last_msg, "content"):
                    return last_msg.content.strip()
                elif isinstance(last_msg, dict):
                    return last_msg.get("content", "").strip()

        if result.get("ocr_result"):
            return f"[OCR Extract]\n{result['ocr_result'][:400]}..."  # fallback

        return str(result)

    # Case 2: AIMessage or BaseMessage
    elif hasattr(result, "content"):
        return result.content.strip()

    # Case 3: Plain string
    elif isinstance(result, str):
        return result.strip()

    # Default fallback
    return str(result)


# ============================================================
# 💬 Chat Loop
# ============================================================
while True:
    query = input("🧑‍⚕️ You: ").strip()

    if query.lower() in ["exit", "quit", "q"]:
        print("👋 Ending chat. Stay healthy!")
        break

    if not query:
        continue

    # Initialize state for this query
    state = MessageState(
        original_query=query,
        rewritten_query="",
        messages=[],
        image_path="",     # Files handled by FastAPI elsewhere
        pdf_path="",
        ocr_result="",
        ner_result=[],
        pathology_report=[],
        medsam_report="",
        medgemma_report="",
        fused_report="",
        llm_report=[],
    )

    print("\n🔄 Processing...")

    try:
        result = health_rag_graph_with_memory.invoke(
            state,
            config={"configurable": {"thread_id": thread_id}}
        )

        # ✅ Extract clean response
        response = extract_healthai_response(result, debug=False)

        # ✅ Handle no response
        if not response or response.strip() == "":
            print("\n⚠️ No response generated. Please try again.\n")
            continue

        # ✅ Display the final answer only
        print(f"\n🤖 HealthAI: {response}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please try again.\n")
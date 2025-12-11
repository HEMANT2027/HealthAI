from fastapi import APIRouter, HTTPException, Body, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import re
import json
from datetime import datetime
import asyncio
import os
import traceback
from dotenv import load_dotenv
load_dotenv()
 
from .Agent import build_health_agent_graph
from endpoints.auth import authMiddleware
from .types import MessageState

router = APIRouter(prefix="/chat", tags=["Chat"])
from pymongo import MongoClient
mongo_client = MongoClient(os.getenv('MONGODB_KEY'))
db = mongo_client['medicotourism']
reports_collection = db['ocr_medsam_reports']

# ============================================================
# Helper Functions
# ============================================================
def build_base_message_state(original_query: str, pseudonym_id: str, user_email: str = None, 
                            image_path: str = "", pdf_path: str = "") -> dict:
    """
    Construct the minimal MessageState expected by the health agent.
    Compatible with both new agent and legacy graph architectures.
    """

    return {
        "original_query": original_query,
        "rewritten_query": "",
        "messages": [],
        "pseudonym_id": pseudonym_id,
        "user_email": user_email,
        "step": 0,
        "image_regions": [],
        "image_path": image_path or "",
        "pdf_path": pdf_path or "",
        "ocr_result": "",
        "ner_result": [],
        "pathology_report": [],
        "medgemma_report": "",
        # "fused_report": "",
        "llm_report": [],
        "analyze_medications": "",
        "suggest_tests": "",
        "suspected": [],
        "symptoms": [],
        "medicines": [],
    }


def extract_healthai_response(result, debug=False):
    """
    Extract the final meaningful text response from a HealthAI result.
    Supports both new agent architecture (with final_answer) and legacy graph.
    """
    if debug:
        print("\n[DEBUG] Type of result:", type(result))
        try:
            print("[DEBUG] Raw Result Preview:", json.dumps(result, indent=2, default=str))
        except Exception:
            print("[DEBUG] Raw Result (non-serializable):", result)

    if isinstance(result, dict):
        # NEW AGENT: Check for final_answer first (new architecture)
        if "final_answer" in result and result["final_answer"]:
            return result["final_answer"].strip()
        
        # LEGACY: Check for standard keys
        for key in ["medgemma_report", "llm_report"]:
            val = result.get(key)
            if val:
                if isinstance(val, list) and len(val) > 0:
                    last_msg = val[-1]
                    if hasattr(last_msg, "content"):
                        return last_msg.content.strip()
                    elif isinstance(last_msg, dict):
                        return last_msg.get("content", "").strip()
                if isinstance(val, str):
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
        return json.dumps(result, indent=2)

    if hasattr(result, "content"):
        return result.content.strip()

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

    return str(result)


def _clean_text(text: str) -> str:
    """Sanitize and normalize model output for clean, human-readable responses."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^[\s]*[\*\-•]+\s+", "- ", text, flags=re.M)
    text = text.replace("•", "-")
    text = re.sub(r"^\s*>+\s*", "", text, flags=re.M)
    text = re.sub(r"^[=~\-\*_]{2,}\s*$", "", text, flags=re.M)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = "".join(ch for ch in text if (ch == "\n" or ch.isprintable()))
    text = text.strip()
    return text


# ============================================================
# Regular Chat Endpoint (Non-streaming)
# ============================================================
# @router.post("/query")
# async def chat_query(
#     payload: dict = Body(...),
#     current_user: dict = Depends(authMiddleware)
# ):
#     """
#     Handle chat messages and return a clean AI response.
#     payload: { query: str, pseudonym_id: str, thread_id?: str }
#     """
#     try:
#         query = payload.get("query")
#         pseudonym_id = payload.get("pseudonym_id")
#         thread_id = payload.get("thread_id")

#         if not query or not pseudonym_id:
#             raise HTTPException(status_code=400, detail="Missing query or pseudonym_id")

#         if not thread_id:
#             thread_id = str(uuid.uuid4())

#         state = MessageState(
#             original_query=query,
#             rewritten_query="",
#             messages=[],
#             pseudonym_id=pseudonym_id,
#             user_email=current_user.get("email"),
#             step=0,
#             image_regions=[],
#             image_path="",     
#             pdf_path="",
#             ocr_result="",
#             ner_result=[],
#             medicines=[],
#             pathology_report=[],
#             medgemma_report="",
#             fused_report="",
#             llm_report=[],
#             suggest_tests="",
#             analyze_medications="",
#             suspected: [],
#             symptoms: [],
#         )

#         result = health_rag_graph_with_memory.invoke(
#             state,
#             config={"configurable": {"thread_id": thread_id}}
#         )

#         response = extract_healthai_response(result, debug=False)
#         clean_response = _clean_text(response)

#         return {
#             "response": clean_response
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# AGUI Event Types
# ============================================================
class EventType:
    RUN_STARTED = "run_started"
    TEXT_MESSAGE_STARTED = "text_message_started"
    TEXT_MESSAGE_CHUNK = "text_message_chunk"
    TEXT_MESSAGE_FINISHED = "text_message_finished"
    RUN_FINISHED = "run_finished"
    ERROR = "error"


class RunAgentInput(BaseModel):
    """Input schema for AGUI agent execution"""
    query: str
    pseudonym_id: str
    thread_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None


class EventEncoder:
    """Encodes events for streaming based on Accept header"""
    
    def __init__(self, accept: Optional[str] = None):
        self.use_sse = accept and "text/event-stream" in accept
        self.content_type = "text/event-stream" if self.use_sse else "application/x-ndjson"
    
    def encode(self, event: Dict[str, Any]) -> str:
        """Encode event as SSE or JSON-lines"""
        json_str = json.dumps(event, ensure_ascii=False)
        
        if self.use_sse:
            return f"data: {json_str}\n\n"
        else:
            return f"{json_str}\n"
    
    def get_content_type(self) -> str:
        return self.content_type


# ============================================================
# AGUI Streaming Endpoint
# ============================================================
@router.post("/agent")
async def agent_endpoint(
    input_data: RunAgentInput,
    request: Request,
    current_user: dict = Depends(authMiddleware)
):
    """
    AGUI-compatible streaming endpoint for HealthAI chatbot.
    """
    print("\n" + "="*80)
    print("🚀 CHATBOT REQUEST RECEIVED")
    print("="*80)
    print(f"📝 Query: {input_data.query}")
    print(f"👤 Patient ID: {input_data.pseudonym_id}")
    print(f"🔑 User: {current_user.get('email')}")
    print("="*80 + "\n")
    
    encoder = EventEncoder(accept=request.headers.get("accept"))
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    async def event_generator():
        try:
            print(f"🎬 Starting AGUI stream - Run ID: {run_id}, Thread ID: {thread_id}")
            
            yield encoder.encode({
                "type": EventType.RUN_STARTED,
                "runId": run_id,
                "threadId": thread_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            yield encoder.encode({
                "type": EventType.TEXT_MESSAGE_STARTED,
                "messageId": message_id,
                "role": "assistant",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            print("📦 Creating MessageState...")
            msg_state = build_base_message_state(
                original_query=input_data.query,
                pseudonym_id=input_data.pseudonym_id,
                user_email=current_user.get("email"),
                image_path="",
                pdf_path=""
            )
            
            # Fetch patient data from MongoDB to populate message_state
            print("🔍 Fetching patient data from MongoDB...")
            try:
                from pymongo import MongoClient
                mongo_client = MongoClient(os.getenv('MONGODB_KEY'))
                db = mongo_client['medicotourism']
                reports_collection = db['ocr_medsam_reports']
                
                # Get cached report
                report = reports_collection.find_one(
                    {"pseudonym_id": input_data.pseudonym_id},
                    sort=[("created_at", -1)]
                )
                
                if report:
                    print("✅ Found cached patient report in MongoDB")
                    msg_state["ocr_result"] = report.get("prescription_ocr", "")
                    msg_state["pathology_report"] = [report.get("pathology_ocr", "")] if report.get("pathology_ocr") else []
                    msg_state["medgemma_report"] = report.get("medgemma_analysis", "")
                    msg_state["medicines"] = report.get("extracted_medicines", [])
                    msg_state["suggested_medicines"] = report.get("suggested_medicines",[])
                    # msg_state["fused_report"] = report.get("medgemma_analysis", "")
                    msg_state["suspected"] = report.get("suspected", [])
                    msg_state["symptoms"] = report.get("symptoms", [])
                else:
                    print("⚠️  No cached report found")
                    
            except Exception as e:
                print(f"⚠️  MongoDB fetch failed: {e}")

            print("✅ MessageState created and populated successfully")
            # Build the new agent graph
            agent = build_health_agent_graph()
            try:
                # Prepare initial state for new agent
                init_state = {
                    "user_question": input_data.query,
                    "message_state": msg_state,
                    "reasoning_log": [],
                }
                # Invoke the agent
                try:
                    if hasattr(agent, "invoke") and callable(agent.invoke):
                        result = agent.invoke(init_state)
                    elif callable(agent):
                        result = agent(init_state)
                    else:
                        raise RuntimeError("Agent is not callable")
                    
                    print("✅ New Agent workflow completed")
                    print(f"   Selected tool: {result.get('selected_tool', 'N/A')}")
                    print(f"   Reasoning steps: {len(result.get('reasoning_log', []))}")
                    
                except Exception as e:
                    print("❌ Exception while invoking agent graph:")
                    traceback.print_exc()
                
                final_answer = result.get("final_answer") if isinstance(result, dict) else None
                print("\n=== DEBUG INFO ===")
                print("Selected tool:", result.get("selected_tool"))
                print("Reasoning Log:")
                for line in result.get("reasoning_log", []):
                    print("-", line)

                msg_snapshot = result.get("message_state", {})
                if isinstance(msg_snapshot, dict):
                    print("\nMessageState snapshot keys and brief values:")
                    keys_to_show = ["suspected", "symptoms", "ocr_result", "medgemma_report"]
                    for k in keys_to_show:
                        v = msg_snapshot.get(k, None)
                        if isinstance(v, (str, list)):
                            summary = (v[:400] + "...") if isinstance(v, str) and len(v) > 400 else v
                        else:
                            summary = str(type(v))
                        print(f" - {k}: {summary}")
                print("\n--- Run complete ---\n")
            except KeyboardInterrupt:
                print("\nInterrupted. Exiting.")

            print("\n📤 Extracting response from result...")
            response_text = extract_healthai_response(result, debug=False)
            print(f"📝 Raw response length: {len(response_text)} chars")
            
            print("🧹 Cleaning response text...")
            clean_response = _clean_text(response_text)
            print(f"✅ Clean response length: {len(clean_response)} chars")
            print(f"📄 Response preview: {clean_response[:100]}...")
            
            # Extract sources from tool_output
            sources = []
            
            # Method 1: Check if sources already in result (from Agent)
            if isinstance(result, dict) and "sources" in result:
                sources = result.get("sources", [])
                print(f"📚 Found {len(sources)} sources from Agent")
            
            # Method 2: Parse from tool_output
            if not sources and isinstance(result, dict):
                tool_output = result.get('tool_output')
                print(f"🔧 Tool output type: {type(tool_output)}")
                
                if(tool_output.get("tool") == "pubmed_search"):
                    raw_results = tool_output.get("raw", [])
                    print(f"📚 Parsing {len(raw_results)} PubMed results")
                    for item in raw_results:
                        sources.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                        })
                elif (tool_output.get("tool") == "medical_web_search"):
                    raw = tool_output.get("raw", [])
                    raw_results = raw.get("results", [])
                    print(f"📚 Parsing {len(raw_results)} PubMed results")
                    for item in raw_results:
                        sources.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                        })
                else:
                    sources = []

            print(f"✅ TOTAL SOURCES: {len(sources)}")

            print(f"\n📡 Streaming response in chunks...")
            chunk_size = 15
            chunk_count = 0
            for i in range(0, len(clean_response), chunk_size):
                chunk = clean_response[i:i + chunk_size]
                chunk_count += 1
                yield encoder.encode({
                    "type": EventType.TEXT_MESSAGE_CHUNK,
                    "messageId": message_id,
                    "delta": chunk
                })
                await asyncio.sleep(0.05)
            print(f"✅ Streamed {chunk_count} chunks")
            
            yield encoder.encode({
                "type": EventType.TEXT_MESSAGE_FINISHED,
                "messageId": message_id,
                "content": clean_response,
                "sources": sources,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Save chat history to MongoDB (append to existing conversation)
            try:
                print("\n💾 Saving chat history to MongoDB...")
                chat_history_collection = db['chat_history']
                
                # Create the conversation entry
                conversation_entry = {
                    "query": input_data.query,
                    "response": clean_response,
                    "sources": sources,
                    "message_id": message_id,
                    "timestamp": datetime.utcnow()
                }
                
                # Find existing conversation or create new one
                conversation_key = {
                    "pseudonym_id": input_data.pseudonym_id,
                    "doctor_email": current_user.get("email")
                }
                
                existing_conversation = chat_history_collection.find_one(conversation_key)
                
                if existing_conversation:
                    # Append to existing conversation
                    result_update = chat_history_collection.update_one(
                        conversation_key,
                        {
                            "$push": {"conversations": conversation_entry},
                            "$set": {"last_updated": datetime.utcnow()}
                        }
                    )
                    print(f"✅ Chat appended to existing conversation")
                    print(f"   - Total messages in conversation: {len(existing_conversation.get('conversations', [])) + 1}")
                else:
                    # Create new conversation document
                    new_conversation = {
                        "pseudonym_id": input_data.pseudonym_id,
                        "doctor_email": current_user.get("email"),
                        "thread_id": thread_id,
                        "conversations": [conversation_entry],
                        "created_at": datetime.utcnow(),
                        "last_updated": datetime.utcnow()
                    }
                    result_insert = chat_history_collection.insert_one(new_conversation)
                    print(f"✅ New conversation created with ID: {result_insert.inserted_id}")
                
                print(f"   - Query: {input_data.query[:50]}...")
                print(f"   - Response length: {len(clean_response)} chars")
                print(f"   - Sources: {len(sources)}")
                
            except Exception as e:
                print(f"⚠️  Failed to save chat history: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail the request if saving fails
            
            yield encoder.encode({
                "type": EventType.RUN_FINISHED,
                "runId": run_id,
                "threadId": thread_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            print("\n" + "="*80)
            print("✅ CHATBOT REQUEST COMPLETED SUCCESSFULLY")
            print("="*80 + "\n")
            
        except Exception as e:
            print("\n" + "="*80)
            print("❌ CHATBOT REQUEST FAILED")
            print("="*80)
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print("Traceback:")
            traceback.print_exc()
            print("="*80 + "\n")
            
            yield encoder.encode({
                "type": EventType.ERROR,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/medicines/{pseudonym_id}")
async def get_patient_medicines(
    pseudonym_id: str,
    current_user: dict = Depends(authMiddleware)
):
    """
    Fetch extracted and suggested medicines for a patient from MongoDB.
    Returns medicines from the most recent report.
    """
    try:
        from pymongo import MongoClient
        import os
        
        # Connect to MongoDB
        mongo_client = MongoClient(os.getenv('MONGODB_KEY'))
        db = mongo_client['medicotourism']
        reports_collection = db['ocr_medsam_reports']
        
        # Find the most recent report for this patient
        report = reports_collection.find_one(
            {"pseudonym_id": pseudonym_id},
            sort=[("created_at", -1)]  # Get most recent
        )
        
        if not report:
            return {
                "success": True,
                "extracted": [],
                "suggested": [],
                "combined": [],
                "message": "No report found for this patient"
            }
        
        extracted = report.get("extracted_medicines", [])
        suggested = report.get("suggested_medicines", [])
        
        # For backward compatibility, also check old "medicines" field
        if not extracted and not suggested:
            old_medicines = report.get("medicines", [])
            extracted = old_medicines
        
        # Combined list for legacy support
        combined = list(dict.fromkeys(extracted + suggested))
        
        return {
            "success": True,
            "extracted": extracted,
            "suggested": suggested,
            "combined": combined,
            "report_id": str(report.get("_id", "")),
            "created_at": report.get("created_at")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch medicines: {str(e)}")

@router.get("/health")
async def agent_health():
    """Check if chat agent is operational"""
    return {
        "status": "healthy",
        "agent": "HealthAI",
        "protocol": "AGUI",
        "version": "1.0.0"
    }

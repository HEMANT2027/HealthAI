from fastapi import APIRouter, HTTPException, Body, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import re
import json
from datetime import datetime
import asyncio

from endpoints.auth import authMiddleware
from .graph_health import health_rag_graph_with_memory, MessageState

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================================
# Helper Functions
# ============================================================
def extract_healthai_response(result, debug=False):
    """
    Extract the final meaningful text response from a HealthAI LangGraph result.
    """
    if debug:
        print("\n[DEBUG] Type of result:", type(result))
        try:
            print("[DEBUG] Raw Result Preview:", json.dumps(result, indent=2, default=str))
        except Exception:
            print("[DEBUG] Raw Result (non-serializable):", result)

    if isinstance(result, dict):
        for key in ["fused_report", "medgemma_report", "llm_report"]:
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
@router.post("/query")
async def chat_query(
    payload: dict = Body(...),
    current_user: dict = Depends(authMiddleware)
):
    """
    Handle chat messages and return a clean AI response.
    payload: { query: str, pseudonym_id: str, thread_id?: str }
    """
    try:
        query = payload.get("query")
        pseudonym_id = payload.get("pseudonym_id")
        thread_id = payload.get("thread_id")

        if not query or not pseudonym_id:
            raise HTTPException(status_code=400, detail="Missing query or pseudonym_id")

        if not thread_id:
            thread_id = str(uuid.uuid4())

        state = MessageState(
            original_query=query,
            rewritten_query="",
            messages=[],
            pseudonym_id=pseudonym_id,
            user_email=current_user.get("email"),
            step=0,
            image_regions=[],
            image_path="",
            pdf_path="",
            ocr_result="",
            ner_result=[],
            pathology_report=[],
            medsam_report="",
            medgemma_report="",
            fused_report="",
            llm_report=[]
        )

        result = health_rag_graph_with_memory.invoke(
            state,
            config={"configurable": {"thread_id": thread_id}}
        )

        response = extract_healthai_response(result, debug=False)
        clean_response = _clean_text(response)

        return {
            "response": clean_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    encoder = EventEncoder(accept=request.headers.get("accept"))
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    async def event_generator():
        try:
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
            
            state = MessageState(
                original_query=input_data.query,
                rewritten_query="",
                messages=[],
                pseudonym_id=input_data.pseudonym_id,
                user_email=current_user.get("email"),
                step=0,
                image_regions=[],
                image_path="",
                pdf_path="",
                ocr_result="",
                ner_result=[],
                pathology_report=[],
                medsam_report="",
                medgemma_report="",
                fused_report="",
                llm_report=[]
            )
            
            result = health_rag_graph_with_memory.invoke(
                state,
                config={"configurable": {"thread_id": thread_id}}
            )
            
            response_text = extract_healthai_response(result, debug=False)
            clean_response = _clean_text(response_text)
            
            chunk_size = 15
            for i in range(0, len(clean_response), chunk_size):
                chunk = clean_response[i:i + chunk_size]
                yield encoder.encode({
                    "type": EventType.TEXT_MESSAGE_CHUNK,
                    "messageId": message_id,
                    "delta": chunk
                })
                await asyncio.sleep(0.05)
            
            yield encoder.encode({
                "type": EventType.TEXT_MESSAGE_FINISHED,
                "messageId": message_id,
                "content": clean_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            yield encoder.encode({
                "type": EventType.RUN_FINISHED,
                "runId": run_id,
                "threadId": thread_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
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


@router.get("/health")
async def agent_health():
    """Check if chat agent is operational"""
    return {
        "status": "healthy",
        "agent": "HealthAI",
        "protocol": "AGUI",
        "version": "1.0.0"
    }

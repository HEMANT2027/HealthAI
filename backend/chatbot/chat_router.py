from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Optional
from endpoints.auth import authMiddleware
from chatbot.graph_health import health_rag_graph_with_memory, MessageState
import uuid

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/query")
async def chat_query(
    payload: dict = Body(...),
    current_user: dict = Depends(authMiddleware)
):
    """
    Handle chat messages and return AI responses.
    
    Payload:
        query: str - The user's question
        pseudonym_id: str - Patient ID
        thread_id: Optional[str] - Existing conversation thread ID
    """
    try:
        query = payload.get("query")
        pseudonym_id = payload.get("pseudonym_id")
        thread_id = payload.get("thread_id")

        if not query or not pseudonym_id:
            raise HTTPException(status_code=400, detail="Missing query or pseudonym_id")

        # Create or use existing thread_id
        if not thread_id:
            thread_id = str(uuid.uuid4())

        # Initialize state
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
            medgemma_report="",
            fused_report="",
            llm_report=[]
        )

        # Process through RAG graph
        response = None
        result = health_rag_graph_with_memory.invoke(
            state,
            config={'configurable': {'thread_id': thread_id}}
        )
        response  = result.content
        print(response)
        return {
            "response": response,
            "thread_id": thread_id
        }

    except HTTPException:
        raise Exception 
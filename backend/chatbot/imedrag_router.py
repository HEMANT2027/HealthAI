from fastapi import APIRouter, HTTPException, Body, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
import uuid
import os
import asyncio
from datetime import datetime
from pathlib import Path
import shutil
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser

from endpoints.auth import authMiddleware

load_dotenv()

router = APIRouter(prefix="/imedrag", tags=["iMedRAG"])

# ============================================================
# iMedRAG Core Classes (merged from iMedRag.py)
# ============================================================

def extract_text_from_file(file_path: str) -> str:
    """Extract text from supported file formats (.txt, .pdf)."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = file_path.suffix.lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    if ext == ".pdf":
        try:
            import PyPDF2
            text = ""
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                if len(pdf_reader.pages) == 0:
                    raise ValueError("PDF file has no pages")
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
            if not text.strip():
                raise ValueError("No extractable text found in PDF (maybe scanned).")
            return text
        except ImportError:
            raise ImportError("PyPDF2 required for PDF files. Install with: pip install PyPDF2")
        except Exception as exc:
            raise ValueError(f"Error reading PDF file: {exc}") from exc

    raise ValueError(f"Unsupported file format: {ext}. Only .txt and .pdf files are supported.")


def process_files(file_paths: List[str], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Process multiple files and split them into overlapping chunks."""
    all_chunks: List[str] = []
    for file_path in file_paths:
        text = extract_text_from_file(file_path)
        if not text.strip():
            continue
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                all_chunks.append(chunk.strip())
            start = end - chunk_overlap
    return all_chunks


class SingleKeyProvider:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.api_key: Optional[str] = None
        self.llm: Optional[ChatGoogleGenerativeAI] = None

    def load_from_env(self):
        key = os.getenv("GEMINI_API_KEY")
        if not key or not key.strip():
            raise ValueError("GEMINI_API_KEY not found. Please set it in your environment or .env file.")
        self.api_key = key.strip()

    def initialize_llm(self):
        if not self.api_key:
            self.load_from_env()
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.0,
        )

    def get_llm(self) -> ChatGoogleGenerativeAI:
        if self.llm is None:
            self.initialize_llm()
        return self.llm


class iMedRAG:
    def __init__(self, documents: List[str], key_provider: SingleKeyProvider, domain: str = "general"):
        if not documents:
            raise ValueError("No documents provided. Please provide at least one document or file.")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = FAISS.from_texts(documents, self.embeddings)
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        self.key_provider = key_provider
        self.domain = domain

    def _retrieve(self, query: str) -> str:
        docs = self.retriever.invoke(query)
        return "\n\n".join([d.page_content for d in docs])

    def _generate_follow_up_queries(self, original_q: str, history: List[Tuple[str, str]], n: int = 4) -> List[str]:
        history_text = (
            "CURRENT FINDINGS:\n" + "\n".join([f"- Q: {q}\n  A: {a[:200]}..." for q, a in history])
            if history else "CURRENT FINDINGS: None (Initial State)"
        )
        domain_context = {
            "medical": "You are an expert medical diagnostic engine.",
            "legal": "You are an expert legal research assistant.",
            "technical": "You are an expert technical documentation specialist.",
            "general": "You are an expert research assistant.",
        }
        domain_role = domain_context.get(self.domain, domain_context["general"])
        prompt = PromptTemplate(
            template="""
            {domain_role}
            ORIGINAL QUESTION: {original_q}

            {history_text}

            TASK: What are the next {n} specific search queries needed to fully answer this question?
            OUTPUT: A comma-separated list of questions only. Be specific and focused.
            """,
            input_variables=["domain_role", "original_q", "history_text", "n"],
        )
        llm = self.key_provider.get_llm()
        chain = prompt | llm | CommaSeparatedListOutputParser()
        result = chain.invoke(
            {"domain_role": domain_role, "original_q": original_q, "history_text": history_text, "n": n}
        )
        return [str(q).strip() for q in result if str(q).strip()]

    def _rag_answer(self, query: str) -> str:
        context = self._retrieve(query)
        prompt = PromptTemplate(
            template="""
            Answer this query using ONLY the provided context. If the context doesn't contain enough information, say so clearly.

            CONTEXT:
            {context}

            QUERY: {query}

            ANSWER:
            """,
            input_variables=["query", "context"],
        )
        llm = self.key_provider.get_llm()
        chain = prompt | llm
        result = chain.invoke({"query": query, "context": context})
        return result.content if hasattr(result, "content") else str(result)

    def run(self, question: str, iterations: int = 2, max_queries: int = 4) -> str:
        iterations = max(1, min(iterations, 5))
        max_queries = max(1, min(max_queries, 8))
        history: List[Tuple[str, str]] = []
        for _ in range(iterations):
            qs = self._generate_follow_up_queries(question, history, n=max_queries)
            qs = qs[:max_queries]
            for q in qs:
                ans = self._rag_answer(q)
                history.append((q, ans))
        history_str = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in history])
        domain_context = {
            "medical": "Synthesize a comprehensive medical answer.",
            "legal": "Synthesize a comprehensive legal analysis.",
            "technical": "Synthesize a comprehensive technical explanation.",
            "general": "Synthesize a comprehensive answer.",
        }
        synthesis_instruction = domain_context.get(self.domain, domain_context["general"])
        final_prompt = PromptTemplate(
            template="""
            {synthesis_instruction}

            ORIGINAL QUESTION: {question}

            RESEARCH FINDINGS:
            {history_str}

            Provide a clear, comprehensive answer that synthesizes all the research findings.
            If any information is missing, clearly state what is missing.
            """,
            input_variables=["synthesis_instruction", "question", "history_str"],
        )
        llm = self.key_provider.get_llm()
        final_chain = final_prompt | llm
        result = final_chain.invoke(
            {"synthesis_instruction": synthesis_instruction, "question": question, "history_str": history_str}
        )
        return result.content if hasattr(result, "content") else str(result)


def create_rag_system(
    file_paths: Optional[List[str]] = None,
    documents: Optional[List[str]] = None,
    domain: str = "general",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> iMedRAG:
    key_provider = SingleKeyProvider()
    key_provider.load_from_env()
    key_provider.initialize_llm()
    all_documents: List[str] = []
    if file_paths:
        file_chunks = process_files(file_paths, chunk_size, chunk_overlap)
        all_documents.extend(file_chunks)
    if documents:
        all_documents.extend(documents)
    if not all_documents:
        raise ValueError("No documents or files provided! Please provide either file_paths or documents.")
    return iMedRAG(documents=all_documents, key_provider=key_provider, domain=domain)


# Store active RAG sessions in memory (in production, use Redis or similar)
rag_sessions: Dict[str, iMedRAG] = {}

# Upload directory
UPLOAD_DIR = Path("uploads/imedrag")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


class EventEncoder:
    """Encodes events for streaming based on Accept header"""
    
    def __init__(self, accept: Optional[str] = None):
        self.use_sse = accept and "text/event-stream" in accept
        self.content_type = "text/event-stream" if self.use_sse else "application/x-ndjson"
    
    def encode(self, event: Dict[str, Any]) -> str:
        """Encode event as SSE or JSON-lines"""
        import json
        json_str = json.dumps(event, ensure_ascii=False)
        
        if self.use_sse:
            return f"data: {json_str}\n\n"
        else:
            return f"{json_str}\n"
    
    def get_content_type(self) -> str:
        return self.content_type


# ============================================================
# Request Models
# ============================================================
class InitializeRAGRequest(BaseModel):
    session_id: Optional[str] = None
    domain: str = "medical"
    chunk_size: int = 1000
    chunk_overlap: int = 200


class QueryRAGRequest(BaseModel):
    session_id: str
    query: str
    iterations: int = 2
    max_queries: int = 4


# ============================================================
# File Upload Endpoint
# ============================================================
@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    domain: str = Form("medical"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    current_user: dict = Depends(authMiddleware)
):
    """
    Upload files and initialize RAG system.
    Returns session_id for subsequent queries.
    """
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create session directory
        session_dir = UPLOAD_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded files
        file_paths = []
        for file in files:
            # Validate file type
            if not file.filename.endswith(('.txt', '.pdf')):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}. Only .txt and .pdf files are supported."
                )
            
            # Save file
            file_path = session_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(str(file_path))
        
        print(f"\n{'='*60}")
        print(f"📁 FILES UPLOADED - Session: {session_id}")
        print(f"{'='*60}")
        print(f"📄 Files: {len(file_paths)}")
        for fp in file_paths:
            print(f"   - {Path(fp).name}")
        print(f"🏥 Domain: {domain}")
        print(f"{'='*60}\n")
        
        # Initialize RAG system
        rag_system = create_rag_system(
            file_paths=file_paths,
            domain=domain,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Store in session
        rag_sessions[session_id] = rag_system
        
        return {
            "success": True,
            "session_id": session_id,
            "files_uploaded": len(file_paths),
            "file_names": [Path(fp).name for fp in file_paths],
            "domain": domain,
            "message": "RAG system initialized successfully"
        }
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Streaming Query Endpoint (AGUI Compatible)
# ============================================================
@router.post("/query")
async def query_rag(
    request: QueryRAGRequest,
    current_user: dict = Depends(authMiddleware)
):
    """
    Query the RAG system with streaming response (AGUI compatible).
    """
    from fastapi import Request as FastAPIRequest
    
    # Get accept header for encoding
    encoder = EventEncoder(accept="text/event-stream")
    
    run_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    async def event_generator():
        try:
            print(f"\n{'='*60}")
            print(f"🔍 iMedRAG QUERY - Session: {request.session_id}")
            print(f"{'='*60}")
            print(f"❓ Query: {request.query}")
            print(f"🔄 Iterations: {request.iterations}")
            print(f"📊 Max queries: {request.max_queries}")
            print(f"{'='*60}\n")
            
            # Check if session exists
            if request.session_id not in rag_sessions:
                yield encoder.encode({
                    "type": EventType.ERROR,
                    "error": "Session not found. Please upload files first.",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return
            
            rag_system = rag_sessions[request.session_id]
            
            # Send run started event
            yield encoder.encode({
                "type": EventType.RUN_STARTED,
                "runId": run_id,
                "sessionId": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send message started event
            yield encoder.encode({
                "type": EventType.TEXT_MESSAGE_STARTED,
                "messageId": message_id,
                "role": "assistant",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Run RAG system (this is synchronous, so we'll run it in executor)
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Run the RAG query in a thread pool to avoid blocking
            answer = await loop.run_in_executor(
                None,
                rag_system.run,
                request.query,
                request.iterations,
                request.max_queries
            )
            
            print(f"✅ Answer generated: {len(answer)} chars")
            
            # Stream the answer in chunks
            chunk_size = 20
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield encoder.encode({
                    "type": EventType.TEXT_MESSAGE_CHUNK,
                    "messageId": message_id,
                    "delta": chunk
                })
                await asyncio.sleep(0.03)  # Smooth streaming
            
            # Send message finished event
            yield encoder.encode({
                "type": EventType.TEXT_MESSAGE_FINISHED,
                "messageId": message_id,
                "content": answer,
                "sources": [],  # iMedRAG doesn't expose sources directly
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Send run finished event
            yield encoder.encode({
                "type": EventType.RUN_FINISHED,
                "runId": run_id,
                "sessionId": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            print(f"{'='*60}")
            print(f"✅ iMedRAG QUERY COMPLETED")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"❌ Query error: {e}")
            import traceback
            traceback.print_exc()
            
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


# ============================================================
# Session Management Endpoints
# ============================================================
@router.get("/sessions")
async def list_sessions(current_user: dict = Depends(authMiddleware)):
    """List all active RAG sessions."""
    return {
        "success": True,
        "sessions": list(rag_sessions.keys()),
        "count": len(rag_sessions)
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(authMiddleware)
):
    """Delete a RAG session and its files."""
    try:
        # Remove from memory
        if session_id in rag_sessions:
            del rag_sessions[session_id]
        
        # Delete files
        session_dir = UPLOAD_DIR / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
        
        return {
            "success": True,
            "message": f"Session {session_id} deleted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Check if iMedRAG service is operational."""
    return {
        "status": "healthy",
        "service": "iMedRAG",
        "active_sessions": len(rag_sessions)
    }

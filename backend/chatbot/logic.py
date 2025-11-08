from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv
from .graph_health import MessageState
import hashlib, json
from langchain_chroma import Chroma
load_dotenv()


model = ChatOpenAI(temperature=0.3)

embeddings = OpenAIEmbeddings()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=900,    
    chunk_overlap=120, 
    add_start_index=True,
)

def _hash_text(s: str) -> str:
    """Hash helper to dedupe near-identical context blocks."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _stringify_docs(docs) -> str:
    """Make sure fused_report (dict/list/str) becomes a readable string for embedding."""
    if isinstance(docs, (dict, list)):
        
        return json.dumps(docs, ensure_ascii=False, separators=(", ", ": "))
    if isinstance(docs, str):
        return docs
    return str(docs)


def context_retrieve(state: MessageState) -> MessageState:
    """
    LangGraph node: Retrieves context and generates query-specific responses.
    """
    print("\n================ RAG Retrieval Stage ================")

    # Get conversation history
    conversation_history = state.get("messages", [])
    history_pairs = []
    for msg in conversation_history[-6:]:
        role = "Doctor" if isinstance(msg, HumanMessage) else "AI"
        content = getattr(msg, "content", "")
        if content:
            history_pairs.append(f"{role}: {content}")
    history_text = "\n".join(history_pairs)

    # Get fused medical data
    fused = state.get("fused_report", "")
    fused_text = _stringify_docs(fused).strip()

    if not fused_text and not history_text:
        print("⚠️ No context available")
        state["llm_report"].append(
            AIMessage(content="I don't have medical data yet. Please upload files or ask a question.")
        )
        return state

    # Prepare context blocks
    context_blocks = []
    if history_text:
        context_blocks.append("Previous Conversation:\n" + history_text)
    if fused_text:
        context_blocks.append("Medical Data:\n" + fused_text)
    full_context = "\n\n".join(context_blocks).strip()

    # Split into chunks
    splits = text_splitter.create_documents([full_context])
    seen_hashes = set()
    unique_docs = []
    for d in splits:
        h = _hash_text(d.page_content)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_docs.append(d)

    # ✅ FIX 1: Use InMemoryVectorStore instead of persistent Chroma
    vector_store = InMemoryVectorStore(embedding=embeddings)
    if unique_docs:
        vector_store.add_documents(unique_docs)

    # Get query
    rewritten = state.get("rewritten_query", "") or ""
    original = state.get("original_query", "") or ""
    query = rewritten.strip() if rewritten.strip() else original.strip()
    
    if not query:
        query = "Provide clinical insights"

    # Retrieve relevant context
    retrieved = []
    if unique_docs:
        retrieved = vector_store.similarity_search(query=query, k=3)  # ✅ FIX 2: Reduced k from 5 to 3
    
    context_text = "\n".join([d.page_content for d in retrieved]) if retrieved else full_context

    # ✅ FIX 3: More directive prompt
    prompt = PromptTemplate(
        template="""
You are HealthAI, a clinical assistant for doctors. 

**CRITICAL: Answer ONLY the doctor's current question. Do not provide summaries unless asked.**

Conversation History:
{history}

Patient Medical Context:
{context}

Doctor's Question:
{query}

**Instructions:**
- If asked a YES/NO question (e.g., "can patient smoke"), answer directly first, then briefly explain why.
- If asked for recommendations (e.g., "suggest medicines"), provide specific actionable items.
- If asked to explain in N words, strictly follow the word limit.
- If asked about a disease, name it clearly first, then elaborate.
- Do NOT repeat previous summaries unless the question asks for a summary.
- Be concise and direct.

Answer:
""",
        input_variables=["history", "context", "query"],
    )

    formatted = prompt.format(
        context=context_text,
        query=query,
        history=history_text
    )

    # Generate response
    response = model.invoke(formatted)

    # Append to conversation
    state["messages"].append(HumanMessage(content=state.get("original_query", "")))
    state["messages"].append(response)
    state["llm_report"].append(response)

    print("✅ RAG retrieval complete.")
    return state
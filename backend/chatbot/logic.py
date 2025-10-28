from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv
from .graph_health import MessageState
import json
 
load_dotenv()

# Initialize embeddings and model
embeddings = OpenAIEmbeddings()

model = ChatAnthropic(
    model_name="claude-3-5-sonnet-20241022",
    max_tokens_to_sample=4096,
    timeout=120,
    stop=None,
)

# Initialize vector store and text splitter
vector_store = InMemoryVectorStore(embedding=embeddings)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
    add_start_index=True,
)


def context_retrieve(state: MessageState) -> MessageState:
    """
    LangGraph node:
    Performs retrieval-augmented reasoning over the fused report context.
    Maintains conversation history for contextual responses.
    """
    print("\n================ RAG Retrieval Stage ================")
    
    # Step 1: Get conversation history for context
    conversation_history = state.get("messages", [])
    history_text = "\n".join([
        f"{'Doctor' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}"
        for msg in conversation_history[-5:]  # Last 5 messages for context
    ])
    
    # Step 2: Prepare docs from fused report
    docs = state.get("fused_report", "")
    
    # If no fused report but we have conversation history, use that
    if not docs and not history_text:
        print("⚠️ No context available – providing general response.")
        state["llm_report"].append(
            AIMessage(content="I don't have enough medical data to provide a specific analysis. Please upload prescription images or pathology reports, or ask a general medical question.")
        )
        return state
    
    # Convert dict or list to text
    if isinstance(docs, (dict, list)):
        docs = json.dumps(docs, indent=2)
    elif not isinstance(docs, str):
        docs = str(docs)
    
    # Step 3: Combine fused report with conversation history
    full_context = f"Previous Conversation:\n{history_text}\n\nMedical Data:\n{docs}" if docs else history_text
    
    # Step 4: Embed and store
    if docs:  
        splits = text_splitter.create_documents([full_context])
        vector_store.add_documents(splits)
        
       
        retrieved = vector_store.similarity_search(
            query=state.get("rewritten_query", ""), k=5
        )
        context = "\n".join([d.page_content for d in retrieved])
    else:
        context = history_text
    
    
    prompt = PromptTemplate(
        template="""
        You are a helpful AI Medical expert assisting doctors.
        You maintain context across the conversation and provide relevant medical insights.
        
        If medical data (OCR, pathology, etc.) is provided, analyze it thoroughly.
        If a question is unrelated to the medical context, politely inform the doctor.
        If continuing a previous conversation, maintain continuity.
        
        Conversation History:
        {history}
        
        Medical Context:
        {context}
        
        Doctor's Current Query: {query}
        
        Provide a clear, structured medical response addressing the doctor's query.
        Maintain professional medical terminology while being clear.""",
        input_variables=["query", "context", "history"],
    )

    formatted = prompt.format(
        context=context,
        query=state.get("rewritten_query", ""),
        history=history_text
    )
    response = model.invoke(formatted)
    
    # Add current query and response to messages for history
    state["messages"].append(HumanMessage(content=state.get("original_query", "")))
    state["messages"].append(response)
    
    state["llm_report"].append(response)
    print("✅ RAG retrieval and reasoning complete.")
    return state
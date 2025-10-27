from graph_health import health_rag_graph_with_memory, MessageState
import uuid

print("\n💬 HealthAI Interactive Chat (With Conversation Memory)")
print("=" * 60)
# print("Features:")
# print("  ✅ Conversation memory across queries")
# print("  ✅ End-to-end RAG processing")
# print("  ✅ Persistent conversation thread")
# print("\nNote: Files (images/PDFs) should be uploaded via FastAPI")
# print("      This CLI is for text-based medical queries with memory")
# print("=" * 60)
 
thread_id = str(uuid.uuid4())
print(f"\n🔗 Thread ID: {thread_id}")
print("(Use this thread_id in FastAPI to continue this conversation)\n")

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
        image_path="",  # Files come from FastAPI
        pdf_path="",    # Files come from FastAPI
        ocr_result="",
        ner_result=[],
        pathology_report=[],
        medgemma_report="",
        fused_report="",   
        llm_report=[],
    )

    print("\n🔄 Processing...")
    
    try:
        response_received = False
        for result, meta_data in health_rag_graph_with_memory.stream(
            state, 
            config={'configurable': {'thread_id': thread_id}},
            stream_mode="messages"
        ):
            if result.content:
                response = result.content
                print(f"\n🤖 HealthAI: {response}\n",end=" ",flush=True)
                response_received = True
        
        if not response_received:
            print("\n⚠️ No response generated. Please try again.\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please try again.\n")
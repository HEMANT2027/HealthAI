import React, { useState, useEffect, useRef } from "react";

/**
 * iMedRAG Chatbot Component
 * Upload documents and ask questions with streaming responses
 */
function IMedRagChat() {
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  
  const [sessionId, setSessionId] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    { 
      role: "assistant", 
      content: "Hello! I'm your document analysis assistant. Click the + button to upload PDF or TXT files, then ask me questions about them.",
      id: "welcome",
      sources: []
    }
  ]);
  const [input, setInput] = useState("");
  const [streamingMessage, setStreamingMessage] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  // Handle file selection and upload
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    const validFiles = files.filter(f => 
      f.name.endsWith('.pdf') || f.name.endsWith('.txt')
    );
    
    if (validFiles.length === 0) {
      alert("Please select PDF or TXT files");
      return;
    }
    
    if (validFiles.length !== files.length) {
      alert("Only PDF and TXT files are supported. Invalid files were filtered out.");
    }
    
    // Automatically upload after selection
    await handleUpload(validFiles);
  };

  // Upload files and initialize RAG
  const handleUpload = async (files) => {
    if (!files || files.length === 0) {
      return;
    }

    try {
      setUploading(true);
      
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      formData.append('domain', 'medical'); // Always medical domain
      
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/imedrag/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      
      setSessionId(data.session_id);
      setUploadedFiles(prev => [...prev, ...data.file_names]);
      
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `✅ Successfully uploaded ${data.files_uploaded} file(s): ${data.file_names.join(', ')}. You can now ask questions about these documents!`,
        id: Date.now().toString(),
        sources: []
      }]);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
    } catch (err) {
      console.error("Upload error:", err);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `❌ Failed to upload files: ${err.message}. Please try again.`,
        id: Date.now().toString(),
        sources: []
      }]);
    } finally {
      setUploading(false);
    }
  };

  // Parse AGUI streaming events
  const parseAGUIEvent = (line) => {
    try {
      if (line.startsWith("data: ")) {
        return JSON.parse(line.slice(6));
      }
      return JSON.parse(line);
    } catch (e) {
      return null;
    }
  };

  // Handle streaming query
  const handleQuery = async () => {
    if (!input.trim()) return;
    if (!sessionId) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠️ Please upload documents first by clicking the + button.",
        id: Date.now().toString(),
        sources: []
      }]);
      return;
    }

    try {
      setLoading(true);
      setIsThinking(true);
      setStreamingMessage("");
      
      // Add user message
      const userMessage = { role: "user", content: input, id: Date.now().toString(), sources: [] };
      setMessages(prev => [...prev, userMessage]);
      const currentInput = input;
      setInput("");

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/imedrag/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: currentInput,
          iterations: 2,
          max_queries: 4
        })
      });

      if (!response.ok) throw new Error('Query failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentMessageId = null;
      let accumulatedContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;

          const event = parseAGUIEvent(line);
          if (!event) continue;

          switch (event.type) {
            case "run_started":
              console.log("📡 run_started event received");
              setIsThinking(true);
              break;

            case "text_message_started":
              console.log("📝 text_message_started event received - stopping thinking animation");
              currentMessageId = event.messageId;
              accumulatedContent = "";
              setIsThinking(false);
              break;

            case "text_message_chunk":
              if (event.delta) {
                accumulatedContent += event.delta;
                setStreamingMessage(accumulatedContent);
              }
              break;

            case "text_message_finished":
              const assistantMessage = {
                role: "assistant",
                content: event.content || accumulatedContent,
                id: event.messageId,
                sources: []
              };
              setMessages(prev => [...prev, assistantMessage]);
              setStreamingMessage("");
              break;

            case "error":
              console.error("Error:", event.error);
              setIsThinking(false);
              setMessages(prev => [...prev, {
                role: "assistant",
                content: `❌ Error: ${event.error}`,
                id: Date.now().toString(),
                sources: []
              }]);
              break;
          }
        }
      }
    } catch (err) {
      console.error("Query error:", err);
      setIsThinking(false);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        id: Date.now().toString(),
        sources: []
      }]);
    } finally {
      setLoading(false);
      setIsThinking(false);
      setStreamingMessage("");
    }
  };

  // Trigger file input click
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-100 via-white to-blue-200 p-4">
      <div className="w-full max-w-[1400px] mx-auto">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Chat area - Full Width with Better Font */}
        <div className="bg-white rounded-2xl shadow-lg p-6 h-[90vh] flex flex-col" style={{fontFamily: "'Inter', 'Segoe UI', 'Roboto', sans-serif"}}>
          {/* Header with session info */}
          {sessionId && uploadedFiles.length > 0 && (
            <div className="mb-4 pb-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-700">📚 Active Documents:</span>
                  <span className="text-xs text-gray-500">{uploadedFiles.join(', ')}</span>
                </div>
                <button
                  onClick={handleUploadClick}
                  className="px-3 py-1 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  + Add More
                </button>
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto mb-4 space-y-5 px-2">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`px-5 py-3 rounded-2xl max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-md"
                      : "bg-gray-50 text-gray-800 border border-gray-200 shadow-sm"
                  }`}
                >
                  <div className={`text-sm font-semibold mb-2 ${msg.role === "user" ? "text-blue-100" : "text-gray-600"}`}>
                    {msg.role === "user" ? "You" : "AI Assistant"}
                  </div>
                  <div className="whitespace-pre-wrap text-base leading-relaxed">{msg.content}</div>
                </div>
              </div>
            ))}
            
            {/* Thinking animation */}
            {(isThinking || loading) && !streamingMessage && (
              <div className="flex justify-start">
                <div className="px-5 py-3 rounded-2xl bg-gray-50 text-gray-800 border border-gray-200 shadow-sm">
                  <div className="text-sm font-semibold mb-2 text-gray-600">AI Assistant</div>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Streaming message */}
            {streamingMessage && (
              <div className="flex justify-start">
                <div className="px-5 py-3 rounded-2xl max-w-[85%] bg-gray-50 text-gray-800 border border-gray-200 shadow-sm">
                  <div className="text-sm font-semibold mb-2 text-gray-600">AI Assistant</div>
                  <div className="whitespace-pre-wrap text-base leading-relaxed">{streamingMessage}</div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></span>
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input area - Sleek Pill Shape */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3 px-6 py-3 rounded-full bg-white border-2 border-gray-200 shadow-lg hover:shadow-xl focus-within:border-blue-400 focus-within:shadow-blue-100 transition-all">
              {/* Upload button */}
              <button
                onClick={handleUploadClick}
                disabled={uploading}
                className={`flex-shrink-0 p-2 rounded-full transition-all ${
                  uploading
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-blue-500 text-white hover:bg-blue-600 hover:scale-110 active:scale-95"
                }`}
                title="Upload documents"
              >
                {uploading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                )}
              </button>

              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleQuery();
                  }
                }}
                placeholder="Ask questions about your documents..."
                disabled={loading}
                rows={1}
                className="flex-1 bg-transparent border-0 outline-none resize-none text-gray-800 placeholder:text-gray-400 focus:ring-0 disabled:opacity-50 text-base py-2"
                style={{
                  fontFamily: "'Inter', 'Segoe UI', 'Roboto', sans-serif",
                  maxHeight: '120px',
                  minHeight: '24px'
                }}
                onInput={(e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                }}
              />

              {/* Send Button */}
              <button
                onClick={handleQuery}
                disabled={loading || !input.trim()}
                className={`p-3 rounded-full transition-all shadow-md flex items-center justify-center ${
                  loading || !input.trim()
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-blue-500 to-teal-500 text-white hover:brightness-110 hover:scale-110 active:scale-95"
                }`}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 12h13M12 5l6.5 6.5L12 18"
                  />
                </svg>
              </button>
            </div>
            
            {/* Warning text below input */}
            <div className="text-center">
              <span className="text-xs text-gray-500">AI can make mistakes, double check it.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default IMedRagChat;

import { useLocation } from "react-router-dom";
import { useState, useEffect, useRef } from "react";

/**
 * AGUI-powered Chatbot Component
 * Uses streaming protocol for real-time AI responses
 */
function ChatbotAGUI() { 
  const location = useLocation();
  const pathParts = location.pathname.split("/");
  const pseudonym_id = pathParts[pathParts.length - 1] || location.state?.pseudonym_id;
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);
  
  const [loading, setLoading] = useState(false);
  const [intakeFiles, setIntakeFiles] = useState([]);
  const [messages, setMessages] = useState([
    { 
      role: "assistant", 
      content: "Hello! I'm your medical AI assistant. I can help analyze patient records and answer medical questions.",
      id: "welcome"
    }
  ]);
  const [input, setInput] = useState("");
  const [streamingMessage, setStreamingMessage] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [threadId, setThreadId] = useState(null);
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Fetch intake form files
  useEffect(() => {
    const fetchIntakeFiles = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/intake/form/${pseudonym_id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) throw new Error('Failed to fetch intake form');

        const data = await response.json();
        if (data.success && data.form.documents) {
          setIntakeFiles(data.form.documents);
        }
      } catch (err) {
        console.error("Failed to fetch intake files:", err);
      }
    };

    fetchIntakeFiles();
  }, [pseudonym_id]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  /**
   * Parse AGUI streaming events (SSE or JSON-lines)
   */
  const parseAGUIEvent = (line) => {
    try {
      // Handle SSE format: "data: {...}"
      if (line.startsWith("data: ")) {
        return JSON.parse(line.slice(6));
      }
      // Handle JSON-lines format
      return JSON.parse(line);
    } catch (e) {
      return null;
    }
  };

  /**
   * Handle streaming response from AGUI endpoint
   */
  const handleAGUIStream = async (query) => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setIsThinking(true);
      setStreamingMessage("");
      
      // Add user message
      const userMessage = { role: "user", content: query, id: Date.now().toString() };
      setMessages(prev => [...prev, userMessage]);
      setInput("");

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/chat/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream', // Request SSE format
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query,
          pseudonym_id,
          thread_id: threadId
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) throw new Error('AGUI stream failed');

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
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          const event = parseAGUIEvent(line);
          if (!event) continue;

          switch (event.type) {
            case "run_started":
              // Store thread_id for conversation continuity
              if (event.threadId) {
                setThreadId(event.threadId);
                localStorage.setItem(`agui_thread_${pseudonym_id}`, event.threadId);
              }
              setIsThinking(true);
              break;

            case "text_message_started":
              currentMessageId = event.messageId;
              accumulatedContent = "";
              setIsThinking(false); // Stop thinking animation when text starts
              break;

            case "text_message_chunk":
              if (event.delta) {
                accumulatedContent += event.delta;
                setStreamingMessage(accumulatedContent);
              }
              break;

            case "text_message_finished":
              // Add complete assistant message
              const assistantMessage = {
                role: "assistant",
                content: event.content || accumulatedContent,
                id: event.messageId
              };
              setMessages(prev => [...prev, assistantMessage]);
              setStreamingMessage("");
              break;

            case "error":
              console.error("AGUI Error:", event.error);
              setIsThinking(false);
              setMessages(prev => [...prev, {
                role: "assistant",
                content: "Sorry, I encountered an error. Please try again.",
                id: Date.now().toString()
              }]);
              break;
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log("Stream cancelled");
        setIsThinking(false);
      } else {
        console.error("AGUI stream error:", err);
        setIsThinking(false);
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          id: Date.now().toString()
        }]);
      }
    } finally {
      setLoading(false);
      setIsThinking(false);
      setStreamingMessage("");
      abortControllerRef.current = null;
    }
  };

  const handleSend = () => {
    handleAGUIStream(input);
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // File type helpers
  const getFileIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'prescription': return '📄';
      case 'pathology': return '🔬';
      case 'scan': return '🩻';
      default: return '📎';
    }
  };

  const getTypeColor = (type) => {
    switch (type?.toLowerCase()) {
      case 'prescription': return 'bg-blue-100';
      case 'pathology': return 'bg-purple-100';
      case 'scan': return 'bg-green-100';
      default: return 'bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-100 via-white to-blue-200 p-6">
      <div className="max-w-6xl mx-auto grid grid-cols-3 gap-6">
        {/* Files sidebar */}
        <div className="col-span-1 bg-white rounded-2xl shadow-lg p-6 h-[85vh] overflow-y-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Patient Files</h2>

          {intakeFiles.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No files available
            </div>
          ) : (
            <div className="space-y-4">
              {intakeFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="group border border-gray-200 hover:border-blue-300 rounded-xl p-4 transition-all hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-lg ${getTypeColor(file.type)}`}>
                      {getFileIcon(file.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 truncate">
                        {file.fileName}
                      </h3>
                      <p className="text-sm text-gray-500 capitalize">
                        {file.type || 'Document'}
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(file.uploadedAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  {file.url && (
                    <div className="mt-3 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                      <a
                        href={file.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
                      >
                        Open File ↗
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Chat area with AGUI streaming */}
        <div className="col-span-2 bg-white rounded-2xl shadow-lg p-6 h-[85vh] flex flex-col">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`px-4 py-2 rounded-2xl max-w-[80%] ${
                    msg.role === "user"
                      ? "bg-blue-500 text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  <div className="text-sm font-medium mb-1">
                    {msg.role === "user" ? "You" : "AI Assistant"}
                  </div>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
              </div>
            ))}
            
            {/* Thinking animation */}
            {isThinking && !streamingMessage && (
              <div className="flex justify-start">
                <div className="px-4 py-2 rounded-2xl bg-gray-100 text-gray-800">
                  <div className="text-sm font-medium mb-1">AI Assistant</div>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Streaming message */}
            {streamingMessage && (
              <div className="flex justify-start">
                <div className="px-4 py-2 rounded-2xl max-w-[80%] bg-gray-100 text-gray-800">
                  <div className="text-sm font-medium mb-1">AI Assistant</div>
                  <div className="whitespace-pre-wrap">{streamingMessage}</div>
                  <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                    <div className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></span>
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></span>
                    </div>
                    <span>Streaming...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="flex items-end gap-3 p-3 rounded-2xl bg-white/80 backdrop-blur-sm border border-gray-200 shadow-sm">
            <div className="flex-1 flex flex-col bg-gray-50 rounded-2xl px-4 py-2 border border-gray-200 focus-within:border-blue-500/60 focus-within:ring-2 focus-within:ring-blue-500/30 transition-all">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask your medical question..."
                disabled={loading}
                className="w-full bg-transparent border-0 outline-none resize-none text-gray-800 placeholder:text-gray-400 min-h-[60px] max-h-[180px] focus:ring-0 disabled:opacity-50"
              />
              <div className="flex justify-between items-center mt-1 text-xs text-gray-500">
                <span className="ml-40">⚠️ AI can make mistakes, double check it.</span>
                {loading && (
                  <button
                    onClick={handleCancel}
                    className="text-red-500 hover:text-red-700 transition-colors"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className={`p-3 rounded-xl transition-all mb-5 shadow-md flex items-center justify-center ${
                loading || !input.trim()
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-blue-500 to-teal-500 text-white hover:brightness-110 hover:scale-105 active:scale-95"
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 12h13M12 5l6.5 6.5L12 18"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatbotAGUI;
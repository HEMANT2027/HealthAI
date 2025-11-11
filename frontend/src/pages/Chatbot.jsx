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

  const [expandedSection, setExpandedSection] = useState('documents');

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-100 via-white to-blue-200 p-4">
      <div className="w-[96%] max-w-[1800px] mx-auto grid grid-cols-12 gap-6">
        {/* Sidebar - Larger */}
        <div className="col-span-3 bg-white rounded-2xl shadow-lg p-5 h-[90vh] overflow-y-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-5">Patient Information</h2>

          {/* Documents Section */}
          <div className="mb-4">
            <button
              onClick={() => toggleSection('documents')}
              className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-cyan-50 hover:from-blue-100 hover:to-cyan-100 rounded-xl transition-all border border-blue-100"
            >
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="font-semibold text-gray-900 text-base">Documents</span>
              </div>
              <svg 
                className={`w-6 h-6 text-gray-600 transition-transform ${expandedSection === 'documents' ? 'rotate-180' : ''}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {expandedSection === 'documents' && (
              <div className="mt-3 space-y-3 pl-2">
                {intakeFiles.length === 0 ? (
                  <div className="text-center py-6 text-gray-500 text-sm">
                    No files available
                  </div>
                ) : (
                  intakeFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="group border border-gray-200 hover:border-blue-300 rounded-xl p-4 transition-all hover:shadow-md"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-3 rounded-lg ${getTypeColor(file.type)} text-xl`}>
                          {getFileIcon(file.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-900 text-sm truncate">
                            {file.fileName}
                          </h3>
                          <p className="text-sm text-gray-500 capitalize mt-1">
                            {file.type || 'Document'}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(file.uploadedAt).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      {file.url && (
                        <div className="mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                          <a
                            href={file.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-blue-600 hover:text-blue-700 hover:underline font-medium"
                          >
                            Open File ↗
                          </a>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Medications Section */}
          <div className="mb-4">
            <button
              onClick={() => toggleSection('medications')}
              className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 rounded-xl transition-all border border-purple-100"
            >
              <div className="flex items-center gap-3">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                <span className="font-semibold text-gray-900 text-base">Medications Suggested</span>
              </div>
              <svg 
                className={`w-6 h-6 text-gray-600 transition-transform ${expandedSection === 'medications' ? 'rotate-180' : ''}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {expandedSection === 'medications' && (
              <div className="mt-3 space-y-3 pl-2">
                <div className="border border-purple-200 rounded-xl p-4 bg-purple-50/50 hover:bg-purple-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💊</span>
                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm">Aspirin</h4>
                      <p className="text-sm text-gray-600 mt-1">100mg - Once daily</p>
                      <p className="text-sm text-gray-500 mt-2">For blood thinning</p>
                    </div>
                  </div>
                </div>
                <div className="border border-purple-200 rounded-xl p-4 bg-purple-50/50 hover:bg-purple-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💊</span>
                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm">Metformin</h4>
                      <p className="text-sm text-gray-600 mt-1">500mg - Twice daily</p>
                      <p className="text-sm text-gray-500 mt-2">Diabetes management</p>
                    </div>
                  </div>
                </div>
                <div className="border border-purple-200 rounded-xl p-4 bg-purple-50/50 hover:bg-purple-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💊</span>
                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm">Lisinopril</h4>
                      <p className="text-sm text-gray-600 mt-1">10mg - Once daily</p>
                      <p className="text-sm text-gray-500 mt-2">Blood pressure control</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Chat area - Much Wider with Better Font */}
        <div className="col-span-9 bg-white rounded-2xl shadow-lg p-6 h-[90vh] flex flex-col" style={{fontFamily: "'Inter', 'Segoe UI', 'Roboto', sans-serif"}}>
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
            {isThinking && !streamingMessage && (
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
                    <span>Streaming...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input area - Sleek Pill Shape */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3 px-6 py-3 rounded-full bg-white border-2 border-gray-200 shadow-lg hover:shadow-xl focus-within:border-blue-400 focus-within:shadow-blue-100 transition-all">
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
              
              {loading && (
                <button
                  onClick={handleCancel}
                  className="text-red-500 hover:text-red-600 transition-colors font-medium text-sm px-3 py-1 rounded-full hover:bg-red-50"
                >
                  Cancel
                </button>
              )}

              {/* Send Button */}
              <button
                onClick={handleSend}
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

export default ChatbotAGUI;
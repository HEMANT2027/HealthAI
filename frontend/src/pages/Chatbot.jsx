import { useLocation, useParams } from "react-router-dom";
import { useState, useEffect, useRef } from "react";

function Chatbot() {
  const location = useLocation();
  const pathParts = location.pathname.split("/");
  const pseudonym_id = pathParts[pathParts.length - 1] || location.state?.pseudonym_id;
  const messagesEndRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [intakeFiles, setIntakeFiles] = useState([]);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello! I'm your medical AI assistant. I can help analyze patient records and answer medical questions." }
  ]);
  const [input, setInput] = useState("");
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Fetch intake form files
  useEffect(() => {
    const fetchIntakeFiles = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/intake/form/${pseudonym_id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch intake form');
        }

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
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    try {
      setLoading(true);
      setMessages(prev => [...prev, { role: "user", content: input }]);
      setInput("");

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/chat/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          query: input,
          pseudonym_id,
          thread_id: localStorage.getItem(`chat_thread_${pseudonym_id}`) || undefined
        })
      });

      if (!response.ok) throw new Error('Chat query failed');
      const data = await response.json();

      // Store thread_id for conversation continuity
      if (data.thread_id) {
        localStorage.setItem(`chat_thread_${pseudonym_id}`, data.thread_id);
      }

      setMessages(prev => [...prev, { role: "assistant", content: data.response }]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again."
      }]);
    } finally {
      setLoading(false);
    }
  };

  // File type icons mapping
  const getFileIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'prescription':
        return '📄';
      case 'pathology':
        return '🔬';
      case 'scan':
        return '🩻';
      default:
        return '📎';
    }
  };

  // File type colors mapping
  const getTypeColor = (type) => {
    switch (type?.toLowerCase()) {
      case 'prescription':
        return 'bg-blue-100';
      case 'pathology':
        return 'bg-purple-100';
      case 'scan':
        return 'bg-green-100';
      default:
        return 'bg-gray-100';
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

        {/* Chat area - keeping existing chat implementation */}
        <div className="col-span-2 bg-white rounded-2xl shadow-lg p-6 h-[85vh] flex flex-col">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
              >
                <div
                  className={`px-4 py-2 rounded-2xl max-w-[80%] ${msg.role === "user"
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
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="flex items-end gap-3 p-3 rounded-2xl bg-white/80 backdrop-blur-sm border border-gray-200 shadow-sm">
            {/* Text Input Area */}
            <div className="flex-1 flex flex-col bg-gray-50 rounded-2xl px-4 py-2 border border-gray-200 focus-within:border-vibrant-blue/60 focus-within:ring-2 focus-within:ring-vibrant-blue/30 transition-all">
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
                className="w-full bg-transparent border-0 outline-none resize-none text-gray-800 placeholder:text-gray-400 min-h-[60px] max-h-[180px] focus:ring-0"
              />
              <div className="flex justify-between items-center mt-1 text-xs text-gray-500">
                <span className="ml-40">⚠️ AI can make mistakes, double check it.</span>
                {loading && <span className="animate-pulse text-vibrant-blue">Processing...</span>}
              </div>
            </div>

            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className={`p-3 rounded-xl transition-all mb-5 shadow-md flex items-center justify-center ${loading || !input.trim()
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-vibrant-blue to-teal-500 text-white hover:brightness-110 hover:scale-105 active:scale-95"
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

export default Chatbot;
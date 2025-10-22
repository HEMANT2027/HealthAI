import { useLocation } from "react-router-dom";
import { useState } from "react";

function Chatbot() {
  const { state } = useLocation();
  const { ocrText, modelOutput, finalNotes } = state || {};
  const [messages, setMessages] = useState([
    { from: "bot", text: "Hello! How can I help you today?" },
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { from: "user", text: input }]);
    setInput("");
    // Dummy bot reply
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { from: "bot", text: "That’s a great question! Let’s explore that." },
      ]);
    }, 800);
  };

  const commonQuestions = [
    "What does the diagnosis mean?",
    "Are there any treatment options?",
    "What should I do next?",
    "Can I get a second opinion?",
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-100 via-white to-blue-200 flex flex-col items-center p-6">
      <div className="bg-white rounded-2xl shadow-lg p-6 w-full max-w-3xl flex flex-col">
        <h1 className="text-3xl font-bold text-gray-800 mb-3">AI Chatbot 🤖</h1>
        <p className="text-gray-500 mb-4">
          Chat with our assistant for help understanding your report.
        </p>

        {/* Common questions */}
        <div className="flex flex-wrap gap-2 mb-4">
          {commonQuestions.map((q) => (
            <button
              key={q}
              onClick={() => setInput(q)}
              className="px-3 py-1 text-sm border border-gray-300 rounded-full hover:bg-blue-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Chat window */}
        <div className="flex-1 overflow-y-auto border border-gray-200 rounded-lg p-4 bg-gray-50 mb-4 space-y-3">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.from === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`px-3 py-2 rounded-xl max-w-xs ${
                  msg.from === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-800"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask something..."
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-vibrant-blue"
          />
          <button
            onClick={handleSend}
            className="px-4 py-2 bg-gradient-to-r from-vibrant-blue to-teal-500 text-white rounded-lg hover:brightness-110"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export {Chatbot}
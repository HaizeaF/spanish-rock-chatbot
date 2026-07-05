import { useState, useEffect, useRef } from 'react'
import { Send, Trash2 } from "lucide-react";
import './App.css'

function App() {
  const [userInput, setUserInput] = useState('');
  const [chatLog, setChatLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const chatWindowRef = useRef(null)

  useEffect(() => {
    const storedChatLog = localStorage.getItem('chatLog');
    if (storedChatLog) {
      setChatLog(JSON.parse(storedChatLog));
    }
  }, []);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [chatLog, loading]);

  const handleClearChat = () => {
    setChatLog([]);
    localStorage.removeItem('chatLog');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    console.log("[Chat] Submit pressed");

    if (!userInput.trim()) {
      console.log("[Chat] Empty input, ignoring request");
      return;
    }

    const userMessage = { type: "user", text: userInput };
    const newChatLog = [...chatLog, userMessage];

    setChatLog(newChatLog);
    setUserInput("");
    setLoading(true);

    try {
      console.log("[Chat] Sending request to backend...");

      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: userInput,
          history: chatLog
            .filter(m => m.type !== "error")
            .map(m => ({
              role: m.type === "user" ? "user" : "assistant",
              content: m.text,
            })),
        }),
      });

      console.log("[Chat] Response received:", response);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      console.log("[Chat] Parsing response...");

      const data = await response.json();

      console.log("[Chat] Response body:", data);

      const agentMessage = {
        type: "agent",
        text: data.agent_response,
      };

      const finalChatLog = [...newChatLog, agentMessage];

      setChatLog(finalChatLog);

      localStorage.setItem("chatLog", JSON.stringify(finalChatLog));

      console.log("[Chat] Conversation updated");
    } catch (error) {
      console.error("[Chat] Request failed:", error);

      const errorMessage = {
        type: "error",
        text: "Lo siento, algo no ha ido bien. Inténtalo de nuevo más tarde.",
      };

      setChatLog(prev => [...prev, errorMessage]);
    } finally {
      console.log("[Chat] Loading finished");
      setLoading(false);
    }
  };

  return (
    <div className="App">
    <div className="header">
      <div className="header-title">
        <h1>Asistente de Rock Español</h1>
        <button type="button" className="clear-button" onClick={handleClearChat} disabled={chatLog.length === 0}>
          <Trash2 size={20}/>
        </button>
      </div>
    </div>

      <div className="chat-window" ref={chatWindowRef}>
        {chatLog.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
                {message.text}
            </div>
        ))}
        {loading && <div className="message agent">Cargando...</div>}
      </div>
      <form onSubmit={handleSubmit} className="chat-form">
        <input type="text" value={userInput} onChange={(e) => setUserInput(e.target.value)} placeholder="Escribe tu mensaje..." disabled={loading} />
        <button type="submit" disabled={loading}>
            <Send size={20} />
        </button>
      </form>
    </div>
  );
}

export default App;
import { useState, useEffect, useRef } from 'react'
import { Send, Trash2 } from 'lucide-react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL
const STORAGE_KEY = 'chatLog'

function App() {
  
  const [userInput, setUserInput] = useState('')
  const [chatLog, setChatLog] = useState([])
  const [loading, setLoading] = useState(false)
  const chatWindowRef = useRef(null)

  /** Restore the persisted chat log from local storage on mount. */
  useEffect(() => {
    const storedChatLog = localStorage.getItem(STORAGE_KEY)
    if (storedChatLog) {
      setChatLog(JSON.parse(storedChatLog))
    }
  }, [])

  /** Keep the chat window scrolled to the latest message. */
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight
    }
  }, [chatLog, loading])

  /** Clear the conversation from state and local storage. */
  const handleClearChat = () => {
    setChatLog([])
    localStorage.removeItem(STORAGE_KEY)
  }

  /** Send the current input to the backend and append the response to the chat log. */
  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!userInput.trim()) {
      return
    }

    const userMessage = { type: 'user', text: userInput }
    const newChatLog = [...chatLog, userMessage]
    setChatLog(newChatLog)
    setUserInput('')
    setLoading(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userInput,
          history: chatLog
            .filter((m) => m.type !== 'error')
            .map((m) => ({
              role: m.type === 'user' ? 'user' : 'assistant',
              content: m.text,
            })),
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      const agentMessage = { type: 'agent', text: data.agent_response }
      const finalChatLog = [...newChatLog, agentMessage]

      setChatLog(finalChatLog)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(finalChatLog))
    } catch (error) {
      const errorMessage = {
        type: 'error',
        text: 'Lo siento, algo no ha ido bien. Inténtalo de nuevo más tarde.',
      }
      setChatLog((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="App">
      <div className="header">
        <div className="header-title">
          <h1>Asistente de Rock Español</h1>
          <button
            type="button"
            className="clear-button"
            onClick={handleClearChat}
            disabled={chatLog.length === 0}
          >
            <Trash2 size={20} />
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
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder="Escribe tu mensaje..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          <Send size={20} />
        </button>
      </form>

      <p className="disclaimer">
        Este asistente utiliza inteligencia artificial y puede cometer errores.
        Verifica la información antes de utilizarla.
      </p>
    </div>
  )
}

export default App
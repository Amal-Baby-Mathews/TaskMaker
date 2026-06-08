import React, { useEffect, useRef, useState } from 'react'
import type { ChatMessage as ChatMessageType } from '@/api/chat'
import { ChatMessage } from './ChatMessage'
import { Send, Trash2, ShieldAlert } from 'lucide-react'

interface ChatPanelProps {
  messages: ChatMessageType[]
  isStreaming: boolean
  error: string | null
  onSendMessage: (text: string) => void
  onClearHistory: () => void
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  isStreaming,
  error,
  onSendMessage,
  onClearHistory
}) => {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Scroll to bottom whenever messages list updates
  useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return
    onSendMessage(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
  }

  // Filter messages to hide system log inputs if they are empty
  const visibleMessages = messages.filter(
    m => !(m.role === 'ai' && m.content.startsWith('[System') && m.content.length < 10)
  )

  return (
    <div className="flex flex-col h-full bg-[#161616] border border-[#2a2a2a] rounded-xl overflow-hidden shadow-lg flex-1">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a2a] bg-[#1a1a1a]">
        <div>
          <h2 className="text-lg font-bold text-white font-heading">Chat Assistant</h2>
          <p className="text-xs text-zinc-500 font-sans mt-0.5">Interact with the multi-agent system in real-time.</p>
        </div>
        <button
          onClick={onClearHistory}
          disabled={messages.length === 0 || isStreaming}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold text-rose-400 hover:text-white hover:bg-rose-500/10 border border-rose-500/20 disabled:opacity-40 disabled:pointer-events-none transition-all duration-200 font-heading"
          title="Clear Conversation History"
        >
          <Trash2 className="w-4 h-4" />
          <span>Clear History</span>
        </button>
      </div>

      {/* Message List Area */}
      <div className="flex-1 overflow-y-auto p-6 bg-[#121212] flex flex-col">
        {visibleMessages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto my-auto">
            <div className="w-12 h-12 rounded-xl bg-[#9D4EDD]/10 border border-[#9D4EDD]/20 flex items-center justify-center text-[#9D4EDD] mb-4">
              <Send className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-200 font-heading mb-1.5">No messages yet</h3>
            <p className="text-sm text-zinc-500 leading-relaxed font-sans">
              Ask TaskMaker AI to schedule plans, create recurring tasks, query reminders, or configure instructions.
            </p>
          </div>
        ) : (
          <div className="flex flex-col">
            {visibleMessages.map((msg, index) => (
              <ChatMessage key={index} message={msg} />
            ))}
          </div>
        )}

        {/* Streaming/Typing indicator */}
        {isStreaming && (
          <div className="flex gap-3 my-4 mr-auto items-start max-w-3xl w-full">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#9D4EDD]/10 border border-[#9D4EDD]/30 text-[#9D4EDD] flex-shrink-0 animate-pulse">
              ●
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-zinc-500 font-heading tracking-wider uppercase mb-1">
                TaskMaker AI
              </span>
              <div className="bg-[#1e1e1e] border border-[#2e2e2e] px-4 py-3 rounded-2xl rounded-tl-none flex items-center gap-1.5 text-zinc-500 text-sm">
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="flex items-center gap-3 p-4 bg-rose-500/10 border border-rose-500/25 rounded-xl text-rose-400 text-sm my-4 max-w-2xl mx-auto">
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            <span className="font-sans leading-normal">{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input box */}
      <form onSubmit={handleSend} className="p-4 border-t border-[#2a2a2a] bg-[#1a1a1a]">
        <div className="flex gap-2 items-end max-w-4xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message here..."
            disabled={isStreaming}
            rows={1}
            className="flex-1 bg-[#121212] text-white placeholder-zinc-500 text-sm rounded-xl px-4 py-3 border border-[#2a2a2a] focus:outline-none focus:border-[#9D4EDD] focus:ring-1 focus:ring-[#9D4EDD] resize-none overflow-hidden max-h-32 min-h-[46px] transition-all disabled:opacity-60 disabled:pointer-events-none"
            style={{ height: 'auto' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="w-11 h-11 bg-[#9D4EDD] hover:bg-[#8B3DCD] disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-xl flex items-center justify-center shadow-lg shadow-[#9D4EDD]/10 hover:shadow-[#9D4EDD]/20 transition-all duration-200 flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}

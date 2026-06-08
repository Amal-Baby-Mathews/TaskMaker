import React, { useEffect } from 'react'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { AgentTopologyMap } from '@/components/topology/AgentTopologyMap'
import { useChatStream, fetchChatHistory, clearChatHistory } from '@/api/chat'

export const ChatPage: React.FC = () => {
  const {
    messages,
    setMessages,
    activeNode,
    isStreaming,
    error,
    startStream
  } = useChatStream() as any

  // Load chat history on mount
  useEffect(() => {
    let active = true
    const loadHistory = async () => {
      try {
        const history = await fetchChatHistory()
        if (active) {
          setMessages(history)
        }
      } catch (err) {
        console.error('Failed to load chat history:', err)
      }
    }
    loadHistory()
    return () => {
      active = false
    }
  }, [setMessages])

  const handleSendMessage = async (text: string) => {
    // Current history is whatever messages we have now
    await startStream(text, messages)
  }

  const handleClearHistory = async () => {
    if (window.confirm('Are you sure you want to clear your chat history?')) {
      try {
        await clearChatHistory()
        setMessages([])
      } catch (err) {
        console.error('Failed to clear chat history:', err)
      }
    }
  }

  return (
    <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0 h-full">
      {/* Left Chat Column */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          error={error}
          onSendMessage={handleSendMessage}
          onClearHistory={handleClearHistory}
        />
      </div>

      {/* Right Topology Column */}
      <div className="w-full lg:w-96 flex-shrink-0 flex flex-col gap-6">
        <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl p-4 shadow-lg">
          <h3 className="text-sm font-bold text-white font-heading mb-1">Execution Topology</h3>
          <p className="text-xs text-zinc-500 font-sans leading-normal">
            Visualize multi-agent coordination. The active agent node glows purple in real-time as tasks are delegated.
          </p>
        </div>
        <AgentTopologyMap activeNode={activeNode} />
      </div>
    </div>
  )
}
export default ChatPage

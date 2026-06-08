import { useState, useCallback, useRef } from 'react'

export interface ChatMessage {
  role: 'human' | 'ai' | 'system'
  content: string
}

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history')
  if (!res.ok) {
    throw new Error('Failed to fetch chat history')
  }
  const data = await res.json()
  return data.messages || []
}

export async function clearChatHistory(): Promise<boolean> {
  const res = await fetch('/api/chat/history', {
    method: 'DELETE'
  })
  if (!res.ok) {
    throw new Error('Failed to clear chat history')
  }
  const data = await res.json()
  return !!data.ok
}

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [activeNode, setActiveNode] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null)

  const stopStreaming = useCallback(() => {
    if (readerRef.current) {
      readerRef.current.cancel()
      readerRef.current = null
    }
    setIsStreaming(false)
    setActiveNode(null)
  }, [])

  const startStream = useCallback(async (userPrompt: string, currentHistory: ChatMessage[]) => {
    setIsStreaming(true)
    setError(null)
    setActiveNode(null)

    // Optimistically add the human message to the view
    const updatedHistory: ChatMessage[] = [
      ...currentHistory,
      { role: 'human', content: userPrompt }
    ]
    setMessages(updatedHistory)

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userPrompt,
          history: currentHistory
        })
      })

      if (!response.body) {
        throw new Error('No response body from backend')
      }

      const reader = response.body.getReader()
      readerRef.current = reader
      const decoder = new TextDecoder()

      let buffer = ''
      let assistantReply = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        
        // Save the last partial line back to buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          const cleanLine = line.trim()
          if (!cleanLine.startsWith('data: ')) continue

          const jsonStr = cleanLine.slice(6)
          try {
            const data = JSON.parse(jsonStr)

            if (data.event === 'node_active') {
              setActiveNode(data.node)
            } else if (data.event === 'node_idle') {
              setActiveNode(null)
            } else if (data.event === 'message') {
              assistantReply = data.content
              setMessages([...updatedHistory, { role: 'ai', content: assistantReply }])
            } else if (data.event === 'error') {
              setError(data.detail)
            } else if (data.event === 'done') {
              setActiveNode(null)
            }
          } catch (err) {
            console.error('Failed to parse SSE line:', jsonStr, err)
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Stream processing failed')
      }
    } finally {
      setIsStreaming(false)
      setActiveNode(null)
      readerRef.current = null
    }
  }, [])

  return {
    messages,
    setMessages,
    activeNode,
    isStreaming,
    error,
    startStream,
    stopStreaming
  }
}

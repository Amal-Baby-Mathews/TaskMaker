import React from 'react'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from '@/api/chat'
import { User, Sparkles } from 'lucide-react'

interface ChatMessageProps {
  message: ChatMessageType
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isHuman = message.role === 'human'

  // If AI response represents an internal DB system log, hide it or style it differently
  if (message.role === 'ai' && message.content.startsWith('[System')) {
    return (
      <div className="flex justify-center my-2">
        <div className="text-[11px] text-zinc-500 bg-zinc-900/40 border border-zinc-800/60 rounded px-2.5 py-1 font-mono max-w-[90%] whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={cn(
      "flex gap-3 my-4 max-w-3xl w-full items-start",
      isHuman ? "ml-auto flex-row-reverse" : "mr-auto"
    )}>
      {/* Icon/Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border",
        isHuman 
          ? "bg-[#252525] border-[#3a3a3a] text-zinc-300" 
          : "bg-[#9D4EDD]/10 border-[#9D4EDD]/30 text-[#9D4EDD]"
      )}>
        {isHuman ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      {/* Bubble Container */}
      <div className="flex flex-col max-w-[85%]">
        {/* Author Label */}
        <span className={cn(
          "text-[10px] text-zinc-500 font-heading tracking-wider uppercase mb-1 px-1",
          isHuman ? "text-right" : "text-left"
        )}>
          {isHuman ? 'User' : 'TaskMaker AI'}
        </span>

        {/* Bubble */}
        <div className={cn(
          "px-4 py-3 rounded-2xl text-[14px] leading-relaxed shadow-sm font-sans break-words whitespace-pre-wrap",
          isHuman
            ? "bg-[#9D4EDD] text-white rounded-tr-none"
            : "bg-[#1e1e1e] text-zinc-100 border border-[#2e2e2e] rounded-tl-none"
        )}>
          {message.content}
        </div>
      </div>
    </div>
  )
}

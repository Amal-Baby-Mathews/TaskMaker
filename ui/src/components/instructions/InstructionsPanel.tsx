import React, { useState } from 'react'
import type { Rule } from '@/api/rules'
import { BookOpen, Plus, Trash2, Info } from 'lucide-react'

interface InstructionsPanelProps {
  rules: Rule[]
  onAddRule: (payload: { rule_id?: string; content: string }) => Promise<void>
  onDeleteRule: (ruleId: string) => Promise<void>
}

export const InstructionsPanel: React.FC<InstructionsPanelProps> = ({
  rules,
  onAddRule,
  onDeleteRule
}) => {
  const [ruleId, setRuleId] = useState('')
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) {
      setError('Instruction content cannot be empty')
      return
    }

    setIsSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      await onAddRule({
        rule_id: ruleId.trim() || undefined,
        content: content.trim()
      })
      setRuleId('')
      setContent('')
      setSuccess('Instruction added successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to add instruction')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (ruleId: string) => {
    if (window.confirm(`Delete instruction with ID "${ruleId}"?`)) {
      setError(null)
      try {
        await onDeleteRule(ruleId)
      } catch (err: any) {
        setError(err.message || 'Failed to delete instruction')
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#9D4EDD]/10 border border-[#9D4EDD]/20 flex items-center justify-center text-[#9D4EDD]">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white font-heading">Operational Instructions & Preferences</h1>
          <p className="text-xs text-zinc-500 font-sans mt-0.5">Define operational rules guiding system planning and agent behaviors.</p>
        </div>
      </div>

      {/* Form Container */}
      <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl p-6 shadow-lg">
        <h2 className="text-base font-bold text-white font-heading mb-4">Add New Operational Instruction</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-xs font-sans">
              {error}
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-sans">
              {success}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-1 flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-400 font-heading">Rule ID</label>
              <input
                type="text"
                value={ruleId}
                onChange={(e) => setRuleId(e.target.value)}
                placeholder="e.g. rule_001 (optional)"
                className="bg-[#111] border border-[#2a2a2a] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#9D4EDD] focus:ring-1 focus:ring-[#9D4EDD] transition-all"
              />
            </div>
            
            <div className="md:col-span-3 flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-400 font-heading">Rule Content</label>
              <input
                type="text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="e.g. Always schedule meetings in the afternoon"
                className="bg-[#111] border border-[#2a2a2a] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#9D4EDD] focus:ring-1 focus:ring-[#9D4EDD] transition-all"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSubmitting || !content.trim()}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-[#9D4EDD] hover:bg-[#8B3DCD] disabled:opacity-40 text-white rounded-lg text-xs font-semibold shadow-lg shadow-[#9D4EDD]/15 transition-all font-heading"
            >
              <Plus className="w-4 h-4" />
              <span>{isSubmitting ? 'Adding...' : 'Add Instruction'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Rules list */}
      <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl p-6 shadow-lg">
        <h2 className="text-base font-bold text-white font-heading mb-4">Active System Rules</h2>

        {rules.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-zinc-800 rounded-xl flex flex-col items-center justify-center">
            <Info className="w-5 h-5 text-zinc-600 mb-2" />
            <p className="text-sm text-zinc-500 font-sans">No active operational instructions found.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {rules.map((rule) => (
              <div
                key={rule.rule_id}
                className="bg-[#111111]/80 border border-[#2a2a2a] hover:border-zinc-800 rounded-xl p-4 flex justify-between items-center gap-4 transition-all"
              >
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] font-mono bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded text-zinc-400 font-semibold inline-block mb-1.5">
                    {rule.rule_id}
                  </span>
                  <p className="text-sm text-zinc-300 font-sans leading-relaxed">
                    {rule.content}
                  </p>
                </div>
                
                <button
                  onClick={() => handleDelete(rule.rule_id)}
                  className="p-2 hover:bg-rose-500/10 rounded-lg text-rose-500 hover:text-rose-400 transition-colors flex-shrink-0"
                  title="Delete Rule"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

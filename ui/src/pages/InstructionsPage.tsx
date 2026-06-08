import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRules, addRule, deleteRule } from '@/api/rules'
import type { Rule } from '@/api/rules'
import { InstructionsPanel } from '@/components/instructions/InstructionsPanel'
import { ShieldAlert } from 'lucide-react'

export const InstructionsPage: React.FC = () => {
  const queryClient = useQueryClient()

  // Fetch all operational rules
  const { data: rules = [], isLoading, error } = useQuery<Rule[]>({
    queryKey: ['rules'],
    queryFn: fetchRules
  })

  // Mutation to add rule
  const addMutation = useMutation({
    mutationFn: (payload: { rule_id?: string; content: string }) => addRule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    }
  })

  // Mutation to delete rule
  const deleteMutation = useMutation({
    mutationFn: (ruleId: string) => deleteRule(ruleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    }
  })

  const handleAddRule = async (payload: { rule_id?: string; content: string }) => {
    await addMutation.mutateAsync(payload)
  }

  const handleDeleteRule = async (ruleId: string) => {
    await deleteMutation.mutateAsync(ruleId)
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 bg-[#9D4EDD] rounded-full animate-ping"></span>
          <span className="text-zinc-400 font-heading text-sm font-semibold tracking-wide">Loading instructions...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto">
        <div className="w-12 h-12 bg-rose-500/10 border border-rose-500/20 text-rose-500 rounded-xl flex items-center justify-center mb-4">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-zinc-200 font-heading mb-1.5">Failed to load instructions</h3>
        <p className="text-sm text-zinc-500 leading-relaxed font-sans mb-4">
          {error instanceof Error ? error.message : 'Could not communicate with the rules database.'}
        </p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['rules'] })}
          className="px-4 py-2 bg-[#9D4EDD] text-white text-xs font-semibold rounded-lg hover:bg-[#8B3DCD] transition-all font-heading"
        >
          Retry Connection
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1">
      <InstructionsPanel
        rules={rules}
        onAddRule={handleAddRule}
        onDeleteRule={handleDeleteRule}
      />
    </div>
  )
}
export default InstructionsPage

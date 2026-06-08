import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTasks, updateTask } from '@/api/tasks'
import type { Task } from '@/api/tasks'
import { ChevronLeft, ChevronRight, CalendarDays, CheckSquare, Square, ShieldAlert, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Subtask {
  id: string
  title: string
  completed: boolean
}

export const DailyPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedDateStr, setSelectedDateStr] = useState<string>(() => {
    const today = new Date()
    return today.toISOString().split('T')[0] // YYYY-MM-DD
  })

  // Fetch all plans
  const { data: tasks = [], isLoading, error } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: fetchTasks
  })

  // Mutation to update task/subtask state
  const updateMutation = useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Partial<Task> }) => 
      updateTask(taskId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    }
  })

  // Date navigation helpers
  const handlePrevDay = () => {
    const d = new Date(selectedDateStr)
    d.setDate(d.getDate() - 1)
    setSelectedDateStr(d.toISOString().split('T')[0])
  }

  const handleNextDay = () => {
    const d = new Date(selectedDateStr)
    d.setDate(d.getDate() + 1)
    setSelectedDateStr(d.toISOString().split('T')[0])
  }

  const handleSetToday = () => {
    const today = new Date()
    setSelectedDateStr(today.toISOString().split('T')[0])
  }

  // Filter tasks that match the selected date (matching YYYY-MM-DD)
  const dailyTasks = useMemo(() => {
    return tasks.filter(task => {
      if (!task.due_time) return false
      const datePart = task.due_time.split('T')[0].split(' ')[0]
      return datePart === selectedDateStr
    })
  }, [tasks, selectedDateStr])

  // Parse a task's subtasks from the metadata string field
  const parseSubtasks = (task: Task): Subtask[] => {
    if (!task.subtasks) return []
    try {
      return JSON.parse(task.subtasks)
    } catch {
      return []
    }
  }

  // Toggle a subtask checkbox and push back to server
  const handleToggleSubtask = async (task: Task, subtaskId: string) => {
    const subtasks = parseSubtasks(task)
    const updatedSubtasks = subtasks.map(sub => {
      if (sub.id === subtaskId) {
        return { ...sub, completed: !sub.completed }
      }
      return sub
    })

    // Determine if all subtasks are now completed
    const allCompleted = updatedSubtasks.length > 0 && updatedSubtasks.every(s => s.completed)
    const newStatus = allCompleted ? 'completed' : 'in_progress'

    await updateMutation.mutateAsync({
      taskId: task.plan_id,
      payload: {
        subtasks: JSON.stringify(updatedSubtasks),
        status: newStatus
      }
    })
  }

  // Mock / Decompose a task for testing purposes
  const handleMockDecomposition = async (task: Task) => {
    const mockList: Subtask[] = [
      { id: '1', title: 'Review operational instructions and parameters', completed: false },
      { id: '2', title: 'Retrieve relevant calendar schedules and logs', completed: false },
      { id: '3', title: 'Verify plan dependencies and check conflicts', completed: false },
      { id: '4', title: 'Format output guidelines and commit updates', completed: false }
    ]

    await updateMutation.mutateAsync({
      taskId: task.plan_id,
      payload: {
        subtasks: JSON.stringify(mockList),
        status: 'in_progress'
      }
    })
  }

  // Formatted date string for display (e.g. Monday, June 8, 2026)
  const formattedDate = useMemo(() => {
    const d = new Date(selectedDateStr)
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }, [selectedDateStr])

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 bg-[#9D4EDD] rounded-full animate-ping"></span>
          <span className="text-zinc-400 font-heading text-sm font-semibold tracking-wide">Loading daily agenda...</span>
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
        <h3 className="text-base font-bold text-zinc-200 font-heading mb-1.5">Failed to load agenda</h3>
        <p className="text-sm text-zinc-500 leading-relaxed font-sans mb-4">
          {error instanceof Error ? error.message : 'Could not query ChromaDB plans.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6 flex-1 flex flex-col h-full min-h-0">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#9D4EDD]/10 border border-[#9D4EDD]/20 flex items-center justify-center text-[#9D4EDD]">
            <CalendarDays className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white font-heading">Daily Agenda Planner</h1>
            <p className="text-xs text-zinc-500 font-sans mt-0.5">Focus on daily plans, decompose tasks, and tick subtasks.</p>
          </div>
        </div>

        {/* Date Selector Navigation */}
        <div className="flex items-center gap-2 bg-[#161616] border border-[#2a2a2a] p-1.5 rounded-xl">
          <button
            onClick={handlePrevDay}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={handleSetToday}
            className="px-3 py-1 hover:bg-zinc-800 text-zinc-300 rounded-lg text-xs font-semibold font-heading transition-colors"
          >
            Today
          </button>
          <span className="text-xs font-mono text-zinc-400 px-2 select-none">{selectedDateStr}</span>
          <button
            onClick={handleNextDay}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Date Header Display */}
      <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl px-6 py-4 flex justify-between items-center shadow-md flex-shrink-0">
        <span className="text-sm font-bold text-zinc-200 font-heading">{formattedDate}</span>
        <span className="text-[11px] text-[#9D4EDD] font-semibold bg-[#9D4EDD]/10 border border-[#9D4EDD]/25 px-2.5 py-1 rounded-md uppercase tracking-wider">
          {dailyTasks.length} {dailyTasks.length === 1 ? 'Task' : 'Tasks'} Scheduled
        </span>
      </div>

      {/* Daily Tasks List */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-4">
        {dailyTasks.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-zinc-800 rounded-2xl max-w-lg mx-auto my-8">
            <CalendarDays className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-zinc-400 font-heading mb-1">No tasks for this day</h3>
            <p className="text-xs text-zinc-600 font-sans max-w-xs mx-auto leading-relaxed">
              Use the Chat page to prompt the agent to schedule tasks, or look at the Calendar tab for other dates.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 max-w-4xl">
            {dailyTasks.map(task => {
              const subtasks = parseSubtasks(task)
              const hasSubtasks = subtasks.length > 0
              const isCompleted = task.status === 'completed'
              const isInProgress = task.status === 'in_progress'

              // Calculate progress percentage
              const progressPercentage = hasSubtasks
                ? Math.round((subtasks.filter(s => s.completed).length / subtasks.length) * 100)
                : 0

              return (
                <div
                  key={task.plan_id}
                  className={cn(
                    "bg-[#161616] border rounded-2xl p-6 transition-all shadow-md relative overflow-hidden",
                    isCompleted
                      ? "border-emerald-500/20 bg-[#161616]/90 shadow-emerald-500/5"
                      : "border-[#2a2a2a]"
                  )}
                >
                  {/* Status Indicator Glow */}
                  <div className={cn(
                    "absolute top-0 left-0 w-1.5 h-full",
                    isCompleted
                      ? "bg-emerald-500"
                      : isInProgress
                        ? "bg-blue-500"
                        : "bg-[#9D4EDD]"
                  )} />

                  {/* Header Row */}
                  <div className="flex justify-between items-start gap-4 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider",
                          isCompleted
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : isInProgress
                              ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                              : "bg-[#9D4EDD]/10 text-[#a85cfc] border border-[#9D4EDD]/20"
                        )}>
                          {task.status.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-zinc-500 font-mono">({task.plan_id})</span>
                      </div>
                      <h3 className={cn(
                        "text-base font-bold font-heading",
                        isCompleted ? "text-zinc-400 line-through" : "text-white"
                      )}>
                        {task.title}
                      </h3>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-zinc-500 font-sans leading-relaxed mb-4">
                    {task.description || 'No description provided.'}
                  </p>

                  {/* Subtask Section */}
                  <div className="border-t border-[#2a2a2a]/60 pt-4 space-y-3">
                    <div className="flex items-center justify-between text-xs mb-2.5">
                      <span className="font-semibold text-zinc-400 font-heading">Subtasks checklist</span>
                      {hasSubtasks && (
                        <span className="font-mono text-zinc-500 font-bold">
                          {progressPercentage}% ({subtasks.filter(s => s.completed).length}/{subtasks.length})
                        </span>
                      )}
                    </div>

                    {!hasSubtasks ? (
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[#111] border border-[#2a2a2a]/55 rounded-xl p-3">
                        <span className="text-[11px] text-zinc-500 font-sans">
                          No subtasks defined. Ask the Planner subagent to decompose this task.
                        </span>
                        <button
                          onClick={() => handleMockDecomposition(task)}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#9D4EDD]/10 hover:bg-[#9D4EDD] border border-[#9D4EDD]/25 hover:border-transparent text-white hover:text-white rounded-lg text-[10px] font-semibold font-heading transition-all"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Mock Decomposition</span>
                        </button>
                      </div>
                    ) : (
                      <>
                        {/* Progress Bar */}
                        <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden mb-3">
                          <div
                            className={cn(
                              "h-full transition-all duration-300",
                              isCompleted ? "bg-emerald-500" : "bg-[#9D4EDD]"
                            )}
                            style={{ width: `${progressPercentage}%` }}
                          />
                        </div>

                        {/* Checklist Items */}
                        <div className="space-y-2">
                          {subtasks.map(sub => (
                            <div
                              key={sub.id}
                              onClick={() => handleToggleSubtask(task, sub.id)}
                              className={cn(
                                "flex items-start gap-2.5 p-2.5 rounded-xl border border-transparent hover:bg-zinc-900/60 hover:border-zinc-800/80 cursor-pointer select-none transition-all duration-150",
                                sub.completed ? "opacity-75" : ""
                              )}
                            >
                              <div className="flex-shrink-0 mt-0.5 text-zinc-500">
                                {sub.completed ? (
                                  <CheckSquare className="w-4 h-4 text-emerald-500" />
                                ) : (
                                  <Square className="w-4 h-4 text-zinc-600 hover:text-zinc-400" />
                                )}
                              </div>
                              <span className={cn(
                                "text-xs font-sans leading-normal",
                                sub.completed ? "text-zinc-500 line-through" : "text-zinc-300"
                              )}>
                                {sub.title}
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
export default DailyPage

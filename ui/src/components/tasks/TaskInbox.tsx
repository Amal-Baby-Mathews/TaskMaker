import React, { useMemo } from 'react'
import type { Task } from '@/api/tasks'
import { useAppStore } from '@/store/useAppStore'
import { Inbox, Trash2, Edit3 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TaskInboxProps {
  tasks: Task[]
  onSelectTask: (task: Task) => void
  onUpdateStatus: (taskId: string, status: string) => Promise<void>
  onDeleteTask: (taskId: string) => Promise<void>
}

export const TaskInbox: React.FC<TaskInboxProps> = ({
  tasks,
  onSelectTask,
  onUpdateStatus,
  onDeleteTask
}) => {
  const { calYear, calMonth } = useAppStore()

  // Parse helper to see if a date fits in the active month
  const isOutsideActiveMonth = (dueTime: string): boolean => {
    if (!dueTime) return true
    try {
      const datePart = dueTime.split('T')[0].split(' ')[0]
      const parts = datePart.split('-')
      if (parts.length === 3) {
        const year = parseInt(parts[0])
        const month = parseInt(parts[1])
        return year !== calYear || month !== calMonth
      }
      return true
    } catch {
      return true
    }
  }

  // Filter unscheduled or out of range tasks
  const inboxTasks = useMemo(() => {
    return tasks.filter(task => {
      if (!task.due_time) return true
      return isOutsideActiveMonth(task.due_time)
    })
  }, [tasks, calYear, calMonth])

  const handleDelete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation()
    if (window.confirm('Delete this task?')) {
      await onDeleteTask(taskId)
    }
  }

  return (
    <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl p-6 shadow-lg mt-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
          <Inbox className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-white font-heading">Inbox & Out-of-Range Tasks</h2>
          <p className="text-xs text-zinc-500 font-sans mt-0.5">Tasks scheduled outside this month or with no set due time.</p>
        </div>
      </div>

      {inboxTasks.length === 0 ? (
        <div className="text-center py-8 border border-dashed border-zinc-800 rounded-xl">
          <p className="text-sm text-zinc-500 font-sans">No tasks in the inbox.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {inboxTasks.map((task) => {
            const isCompleted = task.status === 'completed'
            const isInProgress = task.status === 'in_progress'

            return (
              <div
                key={task.plan_id}
                onClick={() => onSelectTask(task)}
                className="bg-[#111111]/80 hover:bg-[#1a1a1a]/80 border border-[#2a2a2a] rounded-xl p-4 flex justify-between items-start gap-4 cursor-pointer hover:border-zinc-700 transition-all"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className={cn(
                      "text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider",
                      isCompleted
                        ? "bg-emerald-500/10 text-emerald-400"
                        : isInProgress
                          ? "bg-blue-500/10 text-blue-400"
                          : "bg-amber-500/10 text-amber-400"
                    )}>
                      {task.status.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">({task.plan_id})</span>
                  </div>
                  <h3 className="text-sm font-bold text-zinc-200 font-heading mb-1 truncate">
                    {task.title}
                  </h3>
                  <p className="text-xs text-zinc-500 font-sans line-clamp-2 leading-relaxed">
                    {task.description || 'No description provided.'}
                  </p>
                  {task.due_time && (
                    <div className="mt-2 text-[10px] text-zinc-500 font-mono">
                      Due: {task.due_time}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
                  <select
                    value={task.status}
                    onChange={(e) => onUpdateStatus(task.plan_id, e.target.value)}
                    className="bg-[#181818] border border-[#2e2e2e] text-zinc-300 rounded px-2 py-1 text-xs focus:outline-none focus:border-[#9D4EDD] cursor-pointer"
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>

                  <button
                    onClick={() => onSelectTask(task)}
                    className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-200 transition-colors"
                    title="Edit Task"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>

                  <button
                    onClick={(e) => handleDelete(e, task.plan_id)}
                    className="p-1.5 hover:bg-rose-500/10 rounded text-rose-500 hover:text-rose-400 transition-colors"
                    title="Delete Task"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

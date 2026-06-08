import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTasks, updateTask, deleteTask } from '@/api/tasks'
import type { Task } from '@/api/tasks'
import { CalendarView } from '@/components/calendar/CalendarView'
import { TaskInbox } from '@/components/tasks/TaskInbox'
import { TaskEditDialog } from '@/components/tasks/TaskEditDialog'
import { ShieldAlert } from 'lucide-react'

export const CalendarPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Fetch all tasks
  const { data: tasks = [], isLoading, error } = useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: fetchTasks
  })

  // Mutation to update task
  const updateMutation = useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Partial<Task> }) => 
      updateTask(taskId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    }
  })

  // Mutation to delete task
  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    }
  })

  const handleSelectTask = (task: Task) => {
    setSelectedTask(task)
    setIsDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setSelectedTask(null)
    setIsDialogOpen(false)
  }

  const handleSaveTask = async (taskId: string, payload: { title: string; description: string; status: string }) => {
    await updateMutation.mutateAsync({ taskId, payload })
  }

  const handleDeleteTask = async (taskId: string) => {
    await deleteMutation.mutateAsync(taskId)
  }

  const handleUpdateStatus = async (taskId: string, status: string) => {
    await updateMutation.mutateAsync({ taskId, payload: { status } })
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 bg-[#9D4EDD] rounded-full animate-ping"></span>
          <span className="text-zinc-400 font-heading text-sm font-semibold tracking-wide">Loading tasks board...</span>
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
        <h3 className="text-base font-bold text-zinc-200 font-heading mb-1.5">Failed to load tasks</h3>
        <p className="text-sm text-zinc-500 leading-relaxed font-sans mb-4">
          {error instanceof Error ? error.message : 'Could not communicate with the backend database.'}
        </p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['tasks'] })}
          className="px-4 py-2 bg-[#9D4EDD] text-white text-xs font-semibold rounded-lg hover:bg-[#8B3DCD] transition-all font-heading"
        >
          Retry Connection
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 h-full">
      {/* Calendar Grid View */}
      <CalendarView tasks={tasks} onSelectTask={handleSelectTask} />

      {/* Task Inbox & Out of range List */}
      <TaskInbox
        tasks={tasks}
        onSelectTask={handleSelectTask}
        onUpdateStatus={handleUpdateStatus}
        onDeleteTask={handleDeleteTask}
      />

      {/* Inline Modal Task Editor */}
      <TaskEditDialog
        task={selectedTask}
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
        onSave={handleSaveTask}
        onDelete={handleDeleteTask}
      />
    </div>
  )
}
export default CalendarPage

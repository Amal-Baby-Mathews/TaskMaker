import React, { useState, useEffect } from 'react'
import type { Task } from '@/api/tasks'
import { X, Save, Trash2 } from 'lucide-react'

interface TaskEditDialogProps {
  task: Task | null
  isOpen: boolean
  onClose: () => void
  onSave: (taskId: string, payload: { title: string; description: string; status: string }) => Promise<void>
  onDelete: (taskId: string) => Promise<void>
}

export const TaskEditDialog: React.FC<TaskEditDialogProps> = ({
  task,
  isOpen,
  onClose,
  onSave,
  onDelete
}) => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('pending')
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (task) {
      setTitle(task.title || '')
      setDescription(task.description || '')
      setStatus(task.status || 'pending')
      setError(null)
    }
  }, [task, isOpen])

  if (!isOpen || !task) return null

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      setError('Title cannot be empty')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      await onSave(task.plan_id, {
        title: title.trim(),
        description: description.trim(),
        status
      })
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to update plan')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete this task?`)) {
      return
    }
    setIsDeleting(true)
    setError(null)
    try {
      await onDelete(task.plan_id)
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to delete plan')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] w-full max-w-lg rounded-2xl overflow-hidden shadow-2xl relative z-10 scale-100 transition-all duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a2a2a] bg-[#1e1e1e]">
          <div className="flex flex-col">
            <h3 className="text-base font-bold text-white font-heading">Edit Task details</h3>
            <span className="text-[10px] text-zinc-500 font-mono mt-0.5">ID: {task.plan_id}</span>
          </div>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg text-xs font-sans">
              {error}
            </div>
          )}

          {/* Title */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-zinc-400 font-heading">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Weekly Sync Meeting"
              className="bg-[#121212] border border-[#2a2a2a] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#9D4EDD] focus:ring-1 focus:ring-[#9D4EDD] transition-all"
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-zinc-400 font-heading">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide a detailed description..."
              rows={3}
              className="bg-[#121212] border border-[#2a2a2a] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#9D4EDD] focus:ring-1 focus:ring-[#9D4EDD] transition-all resize-none"
            />
          </div>

          {/* Status */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-zinc-400 font-heading">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="bg-[#121212] border border-[#2a2a2a] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#9D4EDD] transition-all"
            >
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          {/* Due Time Display (Readonly) */}
          {task.due_time && (
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-zinc-500 font-heading">Due Time</label>
              <span className="text-xs text-zinc-400 font-mono bg-[#121212] px-3 py-2 rounded-lg border border-[#2a2a2a]/40">
                {task.due_time}
              </span>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-[#2a2a2a] mt-6">
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="flex items-center gap-1.5 px-4 py-2 border border-rose-500/20 text-rose-400 hover:text-white hover:bg-rose-500 rounded-lg text-xs font-semibold transition-all disabled:opacity-40 font-heading"
            >
              <Trash2 className="w-4 h-4" />
              <span>{isDeleting ? 'Deleting...' : 'Delete'}</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSaving || isDeleting}
                className="px-4 py-2 border border-[#333] hover:bg-zinc-800 text-zinc-300 rounded-lg text-xs font-semibold transition-all disabled:opacity-40 font-heading"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving || isDeleting}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#9D4EDD] hover:bg-[#8B3DCD] text-white rounded-lg text-xs font-semibold shadow-lg shadow-[#9D4EDD]/15 transition-all disabled:opacity-40 font-heading"
              >
                <Save className="w-4 h-4" />
                <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

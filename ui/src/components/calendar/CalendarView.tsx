import React, { useMemo } from 'react'
import type { Task } from '@/api/tasks'
import { useAppStore } from '@/store/useAppStore'
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CalendarViewProps {
  tasks: Task[]
  onSelectTask: (task: Task) => void
}

export const CalendarView: React.FC<CalendarViewProps> = ({ tasks, onSelectTask }) => {
  const { calYear, calMonth, prevMonth, nextMonth, setToday } = useAppStore()

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ]

  // Parse task due_time to Date. Standardized helper to parse YYYY-MM-DD
  const parseTaskDateStr = (dueTime: string): string | null => {
    if (!dueTime) return null
    try {
      // due_time typically starts with YYYY-MM-DD (ISO/JSON format)
      const datePart = dueTime.split('T')[0].split(' ')[0]
      if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
        return datePart
      }
      return null
    } catch {
      return null
    }
  }

  // Generate matrix grid of days in the month
  const gridCells = useMemo(() => {
    // 0-indexed month for Date API
    const date = new Date(calYear, calMonth - 1, 1)
    
    // Day of the week of first day (0 = Sunday, 1 = Monday, etc.)
    // We want Mon = 0, Tue = 1, ..., Sun = 6
    let startDayOfWeek = date.getDay() - 1
    if (startDayOfWeek < 0) startDayOfWeek = 6 // shift Sunday to 6

    // Total days in month
    const totalDays = new Date(calYear, calMonth, 0).getDate()

    const cells = []
    
    // Empty padding slots for days of previous month
    for (let i = 0; i < startDayOfWeek; i++) {
      cells.push({ day: 0, dateKey: '' })
    }

    // Days of the month
    for (let day = 1; day <= totalDays; day++) {
      const monthStr = String(calMonth).padStart(2, '0')
      const dayStr = String(day).padStart(2, '0')
      cells.push({
        day,
        dateKey: `${calYear}-${monthStr}-${dayStr}`
      })
    }

    return cells
  }, [calYear, calMonth])

  // Group tasks by parsed date key for efficient lookup
  const tasksByDate = useMemo(() => {
    const map: Record<string, Task[]> = {}
    tasks.forEach(task => {
      const dateKey = parseTaskDateStr(task.due_time)
      if (dateKey) {
        if (!map[dateKey]) map[dateKey] = []
        map[dateKey].push(task)
      }
    })
    return map
  }, [tasks])

  const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

  return (
    <div className="bg-[#161616] border border-[#2a2a2a] rounded-xl p-6 shadow-lg">
      {/* Calendar Header with Navigation */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-6 pb-6 border-b border-[#2a2a2a]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#9D4EDD]/10 border border-[#9D4EDD]/20 flex items-center justify-center text-[#9D4EDD]">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white font-heading">
              {monthNames[calMonth - 1]} {calYear}
            </h2>
            <p className="text-xs text-zinc-500 font-sans mt-0.5">Manage tasks in a monthly grid view.</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 border border-[#2a2a2a] transition-all"
            title="Previous Month"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={setToday}
            className="px-4 py-2 hover:bg-zinc-800 border border-[#2a2a2a] text-zinc-300 rounded-lg text-xs font-semibold font-heading transition-all"
          >
            Today
          </button>
          <button
            onClick={nextMonth}
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 border border-[#2a2a2a] transition-all"
            title="Next Month"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Weekday Labels Grid */}
      <div className="grid grid-cols-7 gap-1.5 mb-2">
        {weekdays.map((w, idx) => (
          <div 
            key={idx} 
            className="text-center py-2 text-xs font-bold text-zinc-500 uppercase tracking-wider border-b border-[#2a2a2a]"
          >
            {w}
          </div>
        ))}
      </div>

      {/* Monthly Grid Days */}
      <div className="grid grid-cols-7 gap-1.5 auto-rows-[110px]">
        {gridCells.map((cell, idx) => {
          const dayTasks = cell.dateKey ? (tasksByDate[cell.dateKey] || []) : []
          
          return (
            <div
              key={idx}
              className={cn(
                "border border-[#2a2a2a]/60 rounded-xl p-2.5 flex flex-col justify-between overflow-hidden transition-all duration-150",
                cell.day === 0 
                  ? "bg-[#111]/30 border-transparent opacity-20 pointer-events-none" 
                  : "bg-[#111111]/60 hover:bg-[#1a1a1a]/60 hover:border-[#3a3a3a]"
              )}
            >
              {cell.day !== 0 && (
                <>
                  {/* Day Number */}
                  <div className="text-xs font-extrabold text-[#9D4EDD] mb-1 font-heading">
                    {cell.day}
                  </div>

                  {/* Task list list (scrollable if many chips exist) */}
                  <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                    {dayTasks.map(task => {
                      const isCompleted = task.status === 'completed'
                      const isInProgress = task.status === 'in_progress'

                      return (
                        <div
                          key={task.plan_id}
                          onClick={(e) => {
                            e.stopPropagation()
                            onSelectTask(task)
                          }}
                          className={cn(
                            "text-[10px] px-2 py-1 rounded font-medium truncate cursor-pointer transition-colors hover:brightness-110 select-none",
                            isCompleted
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : isInProgress
                                ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                                : "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                          )}
                          title={`[${task.status.toUpperCase()}] ${task.title}`}
                        >
                          {task.title}
                        </div>
                      )}
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

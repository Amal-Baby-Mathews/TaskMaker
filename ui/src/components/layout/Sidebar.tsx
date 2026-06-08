import React from 'react'
import { NavLink } from 'react-router-dom'
import { MessageSquare, CalendarDays, BookOpen, ChevronLeft, ChevronRight, Zap, CheckSquare } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/lib/utils'

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useAppStore()

  const navItems = [
    {
      label: 'Chat Assistant',
      path: '/chat',
      icon: MessageSquare
    },
    {
      label: 'Daily Agenda',
      path: '/daily',
      icon: CheckSquare
    },
    {
      label: 'Tasks Board',
      path: '/calendar',
      icon: CalendarDays
    },
    {
      label: 'Instructions',
      path: '/instructions',
      icon: BookOpen
    }
  ]

  return (
    <aside
      className={cn(
        "h-screen bg-[#161616] border-r border-[#2a2a2a] flex flex-col justify-between transition-all duration-300 ease-in-out relative z-10",
        sidebarCollapsed ? "w-16" : "w-60"
      )}
    >
      {/* Top Header */}
      <div>
        <div className={cn(
          "flex items-center gap-3 p-4 border-b border-[#2a2a2a] overflow-hidden whitespace-nowrap",
          sidebarCollapsed ? "justify-center" : "justify-start"
        )}>
          <div className="w-8 h-8 rounded-lg bg-[#9D4EDD] flex items-center justify-center flex-shrink-0 shadow-lg shadow-[#9D4EDD]/20">
            <Zap className="w-4 h-4 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="flex flex-col">
              <span className="font-semibold text-white tracking-wide text-sm font-heading">TaskMaker AI</span>
              <span className="text-[10px] text-zinc-500 font-sans uppercase tracking-wider">v2.0 Secretary</span>
            </div>
          )}
        </div>

        {/* Nav Links */}
        <nav className="flex flex-col gap-1 p-2 mt-4">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative",
                  isActive
                    ? "bg-[#9D4EDD] text-white shadow-md shadow-[#9D4EDD]/20"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
                )
              }
            >
              {() => (
                <>
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && (
                    <span className="font-heading transition-opacity duration-300">
                      {item.label}
                    </span>
                  )}
                  {sidebarCollapsed && (
                    <div className="absolute left-16 bg-[#1e1e1e] border border-[#333] text-white text-xs rounded-md px-2.5 py-1.5 opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap z-50 shadow-xl">
                      {item.label}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Collapse Button at the bottom */}
      <div className="p-3 border-t border-[#2a2a2a] flex justify-center">
        <button
          onClick={toggleSidebar}
          className="w-full py-2 hover:bg-zinc-900 rounded-lg text-zinc-400 hover:text-zinc-200 flex items-center justify-center transition-colors duration-200"
          title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <div className="flex items-center gap-2">
              <ChevronLeft className="w-5 h-5" />
              <span className="text-xs font-heading">Collapse Menu</span>
            </div>
          )}
        </button>
      </div>
    </aside>
  )
}

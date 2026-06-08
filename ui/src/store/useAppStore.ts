import { create } from 'zustand'

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  calYear: number
  calMonth: number
  prevMonth: () => void
  nextMonth: () => void
  setToday: () => void
}

export const useAppStore = create<AppState>((set) => {
  // Load sidebar state from localStorage if present
  const savedSidebar = localStorage.getItem('sidebar_collapsed')
  const initialSidebar = savedSidebar ? JSON.parse(savedSidebar) : false

  const today = new Date()

  return {
    sidebarCollapsed: initialSidebar,
    toggleSidebar: () => set((state) => {
      const newVal = !state.sidebarCollapsed
      localStorage.setItem('sidebar_collapsed', JSON.stringify(newVal))
      return { sidebarCollapsed: newVal }
    }),
    calYear: today.getFullYear(),
    calMonth: today.getMonth() + 1, // 1-indexed (Jan = 1)
    prevMonth: () => set((state) => {
      let nextMonth = state.calMonth - 1
      let nextYear = state.calYear
      if (nextMonth < 1) {
        nextMonth = 12
        nextYear -= 1
      }
      return { calMonth: nextMonth, calYear: nextYear }
    }),
    nextMonth: () => set((state) => {
      let nextMonth = state.calMonth + 1
      let nextYear = state.calYear
      if (nextMonth > 12) {
        nextMonth = 1
        nextYear += 1
      }
      return { calMonth: nextMonth, calYear: nextYear }
    }),
    setToday: () => set({
      calYear: today.getFullYear(),
      calMonth: today.getMonth() + 1
    })
  }
})

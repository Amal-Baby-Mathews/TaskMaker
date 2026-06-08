import React from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export const AppShell: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#111111] text-zinc-100 font-sans">
      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Content Pane */}
      <main className="flex-1 h-full overflow-y-auto flex flex-col relative bg-[#111111]">
        <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full h-full min-h-0">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

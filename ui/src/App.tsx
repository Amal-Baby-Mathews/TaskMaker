import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { ChatPage } from '@/pages/ChatPage'
import { CalendarPage } from '@/pages/CalendarPage'
import { DailyPage } from '@/pages/DailyPage'
import { InstructionsPage } from '@/pages/InstructionsPage'

// Create TanStack Query client for API cache management
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000 // 30 seconds cache TTL
    }
  }
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Main App Layout wrapper */}
          <Route path="/" element={<AppShell />}>
            {/* Redirect root path to chat assistant */}
            <Route index element={<Navigate to="/chat" replace />} />
            
            {/* Nav Pages */}
            <Route path="chat" element={<ChatPage />} />
            <Route path="daily" element={<DailyPage />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="instructions" element={<InstructionsPage />} />

            {/* Catch-all route redirects back to chat */}
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App

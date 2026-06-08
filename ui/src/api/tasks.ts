export interface Task {
  plan_id: string
  title: string
  description: string
  due_time: string
  status: string
  subtasks?: string
}

export async function fetchTasks(): Promise<Task[]> {
  const res = await fetch('/api/tasks')
  if (!res.ok) {
    throw new Error('Failed to fetch tasks')
  }
  const data = await res.json()
  return data.plans || []
}

export async function updateTask(
  planId: string,
  payload: { title?: string; description?: string; due_time?: string; status?: string; subtasks?: string }
): Promise<boolean> {
  const res = await fetch(`/api/tasks/${planId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    throw new Error('Failed to update task')
  }
  const data = await res.json()
  return !!data.ok
}

export async function deleteTask(planId: string): Promise<boolean> {
  const res = await fetch(`/api/tasks/${planId}`, {
    method: 'DELETE'
  })
  if (!res.ok) {
    throw new Error('Failed to delete task')
  }
  const data = await res.json()
  return !!data.ok
}

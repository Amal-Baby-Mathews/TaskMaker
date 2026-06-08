export interface Rule {
  rule_id: string
  content: string
}

export async function fetchRules(): Promise<Rule[]> {
  const res = await fetch('/api/rules')
  if (!res.ok) {
    throw new Error('Failed to fetch rules')
  }
  const data = await res.json()
  return data.rules || []
}

export async function addRule(payload: { rule_id?: string; content: string }): Promise<string> {
  const res = await fetch('/api/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    throw new Error(errData.detail || 'Failed to add rule')
  }
  const data = await res.json()
  return data.rule_id
}

export async function deleteRule(ruleId: string): Promise<boolean> {
  const res = await fetch(`/api/rules/${ruleId}`, {
    method: 'DELETE'
  })
  if (!res.ok) {
    throw new Error('Failed to delete rule')
  }
  const data = await res.json()
  return !!data.ok
}

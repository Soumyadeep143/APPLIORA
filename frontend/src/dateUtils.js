// Shared deadline-urgency classification — used by the job feed (App.jsx)
// and the landing page's trending strip (Landing.jsx) so "how urgent is
// this deadline" reads identically in both places instead of drifting.
export function deadlineInfo(deadline) {
  if (!deadline) return null
  const date = new Date(deadline)
  if (Number.isNaN(date.getTime())) return { label: `Apply by ${deadline}`, tone: 'ok' }
  const msLeft = date.getTime() - Date.now()
  const daysLeft = Math.ceil(msLeft / 86400000)
  const pretty = date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  if (daysLeft < 0) return { label: `Closed ${pretty}`, tone: 'expired', daysLeft }
  if (daysLeft <= 7) return { label: `Apply by ${pretty} · ${daysLeft}d left`, tone: 'soon', daysLeft }
  return { label: `Apply by ${pretty}`, tone: 'ok', daysLeft }
}

// API base: empty in dev (vite proxy handles it); set VITE_API_URL in
// production to the deployed backend origin, e.g. https://appliora.onrender.com
const API_BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail) && body.detail[0]?.msg)
        detail = body.detail[0].msg
    } catch {
      /* keep default message */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return null
  return response.json()
}

export const extractJob = (url) =>
  request('/api/extract', { method: 'POST', body: JSON.stringify({ url }) })

export const listJobs = (search = '') =>
  request(`/api/jobs${search ? `?search=${encodeURIComponent(search)}` : ''}`)

export const createJob = (job) =>
  request('/api/jobs', { method: 'POST', body: JSON.stringify(job) })

export const deleteJob = (id) =>
  request(`/api/jobs/${id}`, { method: 'DELETE' })

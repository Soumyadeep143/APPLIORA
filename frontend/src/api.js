// API base: empty in dev (vite proxy handles it); set VITE_API_URL in
// production to the deployed backend origin, e.g. https://devcareer.onrender.com
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

export const extractJob = (payload) =>
  request('/api/extract', { method: 'POST', body: JSON.stringify(payload) })

export const register = (username, name, email, password, referralCode = '') =>
  request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, name, email, password, referral_code: referralCode }),
  })

export const login = (username, password) =>
  request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })

export const listJobs = (search = '') =>
  request(`/api/jobs${search ? `?search=${encodeURIComponent(search)}` : ''}`)

export const getStats = () => request('/api/stats')

export const createJob = (job) =>
  request('/api/jobs', { method: 'POST', body: JSON.stringify(job) })

export const deleteJob = (id, adminUserId) =>
  request(`/api/jobs/${id}?admin_user_id=${adminUserId}`, { method: 'DELETE' })

export const updateJob = (id, job, adminUserId) =>
  request(`/api/jobs/${id}?admin_user_id=${adminUserId}`, {
    method: 'PATCH',
    body: JSON.stringify(job),
  })

export const toggleReaction = (jobId, userId, emoji) =>
  request(`/api/jobs/${jobId}/reactions`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, emoji }),
  })

export const listComments = (jobId) => request(`/api/jobs/${jobId}/comments`)

export const postComment = (jobId, userId, body) =>
  request(`/api/jobs/${jobId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, body }),
  })

export const deleteComment = (jobId, commentId, userId) =>
  request(`/api/jobs/${jobId}/comments/${commentId}?user_id=${userId}`, { method: 'DELETE' })

export const updateNotificationSettings = (userId, email, optIn) =>
  request(`/api/users/${userId}/notifications`, {
    method: 'PATCH',
    body: JSON.stringify({ email, opt_in: optIn }),
  })

export const updateProfileDetails = (
  userId,
  { linkedinUrl, githubUrl, xUrl, bio, skills, targetRole }
) =>
  request(`/api/users/${userId}/profile`, {
    method: 'PATCH',
    body: JSON.stringify({
      linkedin_url: linkedinUrl,
      github_url: githubUrl,
      x_url: xUrl,
      bio,
      skills,
      target_role: targetRole,
    }),
  })

export const getUserProfile = (userId) => request(`/api/users/${userId}`)

export const getLeaderboard = () => request('/api/leaderboard')

export const listAdminUsers = (adminUserId) =>
  request(`/api/admin/users?admin_user_id=${adminUserId}`)

export const setUserAdmin = (userId, superadminUserId, isAdmin) =>
  request(`/api/admin/users/${userId}/admin?superadmin_user_id=${superadminUserId}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_admin: isAdmin }),
  })

export const removeUser = (userId, superadminUserId) =>
  request(`/api/superadmin/users/${userId}?superadmin_user_id=${superadminUserId}`, {
    method: 'DELETE',
  })

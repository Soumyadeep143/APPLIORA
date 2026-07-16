import { useEffect, useState } from 'react'
import { listAdminUsers, removeUser, setUserAdmin } from './api'
import './SuperAdminPage.css'

// A tier above the Task 6.2 Admin page (PRD.md Task 6.9): superadmins can
// still promote/demote admins (same as any admin can), and additionally
// remove a user account entirely — not just moderate jobs. There's
// currently exactly one bootstrap path to becoming a superadmin
// (SUPERADMIN_NAMES env var, or a direct DB flip) — no UI here promotes
// someone else to superadmin, since that wasn't asked for and is a bigger
// trust decision than the other actions on this page.
export default function SuperAdminPage({ superadminUserId }) {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listAdminUsers(superadminUserId)
      .then(setUsers)
      .catch((err) => setError(err.message))
  }, [superadminUserId])

  async function handleToggleAdmin(target) {
    setError('')
    try {
      const updated = await setUserAdmin(target.id, superadminUserId, !target.is_admin)
      setUsers((current) => current.map((u) => (u.id === target.id ? updated : u)))
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleRemoveUser(target) {
    if (!window.confirm(`Remove ${target.name} (@${target.username}) entirely? This can't be undone.`))
      return
    setError('')
    try {
      await removeUser(target.id, superadminUserId)
      setUsers((current) => current.filter((u) => u.id !== target.id))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="superadmin-page">
      <div className="superadmin-page-card">
        <h1>👑 Super Admin</h1>
        <p className="superadmin-page-subtitle">
          Promote or demote admins, or remove an account entirely. Removing someone
          keeps the jobs they shared (the board is shared content) but deletes their
          own reactions and comments.
        </p>

        {error && <p className="auth-error">{error}</p>}

        {users === null ? (
          <p className="muted">Loading…</p>
        ) : (
          <div className="superadmin-table-wrap">
            <table className="superadmin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th aria-hidden="true"></th>
                  <th aria-hidden="true"></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>@{u.username}</td>
                    <td>{u.email || <span className="muted">—</span>}</td>
                    <td>
                      {u.is_superadmin ? (
                        <span className="admin-badge superadmin">Super admin</span>
                      ) : u.is_admin ? (
                        <span className="admin-badge">Admin</span>
                      ) : (
                        <span className="muted">Member</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ghost small"
                        disabled={u.id === superadminUserId || u.is_superadmin}
                        title={
                          u.is_superadmin ? 'Super admins keep admin access permanently' : undefined
                        }
                        onClick={() => handleToggleAdmin(u)}
                      >
                        {u.is_admin ? 'Remove admin' : 'Make admin'}
                      </button>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ghost small danger"
                        disabled={u.id === superadminUserId}
                        title={u.id === superadminUserId ? "You can't remove your own account" : undefined}
                        onClick={() => handleRemoveUser(u)}
                      >
                        Remove user
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

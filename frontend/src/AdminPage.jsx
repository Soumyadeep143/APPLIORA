import { useEffect, useState } from 'react'
import { listAdminUsers, setUserAdmin } from './api'
import './AdminPage.css'

// A dedicated page (PRD.md Task 6.5), not the header popover it started as
// — every admin can promote or demote any other user (including another
// admin) to admin; there's no separate "superadmin" tier, any admin can
// make any other user an admin. Enforced server-side on every call here
// (main.py's _require_admin, 403 for a non-admin) — App.jsx's caller
// already checks user.is_admin before rendering this page at all, but that
// client-side check is UX only, not the real gate.
export default function AdminPage({ adminUserId }) {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listAdminUsers(adminUserId)
      .then(setUsers)
      .catch((err) => setError(err.message))
  }, [adminUserId])

  async function handleToggleAdmin(target) {
    setError('')
    try {
      const updated = await setUserAdmin(target.id, adminUserId, !target.is_admin)
      setUsers((current) => current.map((u) => (u.id === target.id ? updated : u)))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="admin-page">
      <div className="admin-page-card">
        <h1>Admin — manage users</h1>
        <p className="admin-page-subtitle">
          Promote a friend to admin so they can help moderate the board and delete jobs
          that shouldn't be there — any admin can promote or demote any other user.
        </p>

        {error && <p className="auth-error">{error}</p>}

        {users === null ? (
          <p className="muted">Loading…</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Rank points</th>
                  <th>Role</th>
                  <th aria-hidden="true"></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>{u.email || <span className="muted">—</span>}</td>
                    <td>{u.rank_points}</td>
                    <td>
                      {u.is_admin ? (
                        <span className="admin-badge">Admin</span>
                      ) : (
                        <span className="muted">Member</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ghost small"
                        disabled={u.id === adminUserId}
                        title={u.id === adminUserId ? "You can't change your own role" : undefined}
                        onClick={() => handleToggleAdmin(u)}
                      >
                        {u.is_admin ? 'Remove admin' : 'Make admin'}
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

import { useEffect, useState } from 'react'
import { listAdminUsers } from './api'
import './AdminPage.css'

// A dedicated page (PRD.md Task 6.5) — read-only user directory for
// regular admins. Promoting/demoting admins moved to superadmin-only
// (PRD.md Task 6.10, see SuperAdminPage.jsx) — a regular admin's actual
// moderation powers are job-level (add/modify/delete a job, from
// BrowseJobsPage's JobCard), not account-level.
export default function AdminPage({ adminUserId }) {
  const [users, setUsers] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listAdminUsers(adminUserId)
      .then(setUsers)
      .catch((err) => setError(err.message))
  }, [adminUserId])

  return (
    <div className="admin-page">
      <div className="admin-page-card">
        <h1>Admin — all users</h1>
        <p className="admin-page-subtitle">
          You can add, edit and delete jobs from the board. Promoting someone to admin
          is a super admin action — ask one if a friend needs admin access.
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
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>{u.email || <span className="muted">—</span>}</td>
                    <td>{u.rank_points}</td>
                    <td>
                      {u.is_superadmin ? (
                        <span className="admin-badge superadmin">Super admin</span>
                      ) : u.is_admin ? (
                        <span className="admin-badge">Admin</span>
                      ) : (
                        <span className="muted">Member</span>
                      )}
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

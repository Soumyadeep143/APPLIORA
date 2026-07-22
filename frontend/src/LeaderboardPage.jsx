import { useEffect, useState } from 'react'
import { getLeaderboard } from './api'
import './LeaderboardPage.css'

const MEDALS = ['🥇', '🥈', '🥉']

// A dedicated page (PRD.md Task 6.10) — was previously a popover inside
// App.jsx's own header (RankPanel), which disappeared along with the rest
// of that header. Gated behind login like Browse Jobs / Add Job / Profile
// (App.jsx's redirect effect) — ranking is tied to signed-in accounts, so
// there's no useful anonymous view of it.
export default function LeaderboardPage({ user, onViewProfile }) {
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getLeaderboard()
      .then(setBoard)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-card">
        <h1>🏆 Leaderboard</h1>
        <p className="leaderboard-subtitle">
          Ranked by jobs shared and friends who joined with your referral code.
        </p>

        {error && <p className="auth-error">{error}</p>}

        {board === null ? (
          <p className="muted">Loading…</p>
        ) : board.length === 0 ? (
          <p className="muted">No one's on the board yet — share a job to take the top spot.</p>
        ) : (
          <ol className="leaderboard-list">
            {board.map((row, index) => (
              <li key={row.id} className={row.id === user?.id ? 'me' : ''}>
                <span className="leaderboard-rank">{MEDALS[index] || `#${index + 1}`}</span>
                <button
                  type="button"
                  className="leaderboard-name"
                  onClick={() => onViewProfile(row.id)}
                >
                  {row.name}
                  {row.id === user?.id && <span className="leaderboard-you">you</span>}
                </button>
                <span className="leaderboard-points">{row.rank_points} pts</span>
              </li>
            ))}
          </ol>
        )}

        {user && (
          <p className="leaderboard-cta">
            Your referral code is <code>{user.referral_code}</code> — share it, or paste a job
            link on <strong>Add Job</strong>, to climb the board.
          </p>
        )}
      </div>
    </div>
  )
}

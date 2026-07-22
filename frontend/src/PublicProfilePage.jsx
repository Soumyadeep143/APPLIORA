import { useEffect, useState } from 'react'
import { getUserProfile } from './api'
import { GitHubIcon, LinkedInIcon, XIcon } from './Icons'
import './ProfilePage.css'

// Read-only counterpart to ProfilePage.jsx (PRD.md Task 6.13) — opened by
// clicking a Leaderboard row or a job's "Shared by" name. No edit forms,
// no email, no logout: just what that account has chosen to show.
export default function PublicProfilePage({ userId }) {
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setProfile(null)
    setError('')
    getUserProfile(userId)
      .then(setProfile)
      .catch((err) => setError(err.message))
  }, [userId])

  if (error) {
    return (
      <div className="profile-page">
        <p className="auth-error">{error}</p>
      </div>
    )
  }
  if (!profile) {
    return (
      <div className="profile-page">
        <p className="muted">Loading…</p>
      </div>
    )
  }

  const socialLinks = [
    { Icon: LinkedInIcon, url: profile.linkedin_url, label: 'LinkedIn' },
    { Icon: GitHubIcon, url: profile.github_url, label: 'GitHub' },
    { Icon: XIcon, url: profile.x_url, label: 'X' },
  ].filter((link) => link.url.trim())

  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-avatar" aria-hidden="true">
          {profile.name.trim().charAt(0).toUpperCase()}
        </div>
        <h1>{profile.name}</h1>
        <p className="profile-username">@{profile.username}</p>
        {profile.is_admin && <span className="admin-badge">Admin</span>}

        {profile.target_role && <p className="profile-target-role">{profile.target_role}</p>}
        {profile.bio && <p className="profile-bio">{profile.bio}</p>}
        {profile.skills && (
          <div className="profile-skills">
            {profile.skills
              .split(',')
              .map((skill) => skill.trim())
              .filter(Boolean)
              .map((skill) => (
                <span key={skill} className="skill-chip">
                  {skill}
                </span>
              ))}
          </div>
        )}

        <dl className="profile-fields">
          <div>
            <dt>Rank points</dt>
            <dd>{profile.rank_points}</dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{profile.created_at}</dd>
          </div>
        </dl>

        {socialLinks.length > 0 && (
          <div className="social-links-view">
            {socialLinks.map(({ Icon, url, label }) => (
              <a
                key={label}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="social-icon-link"
                title={`Open ${label} profile`}
              >
                <Icon size={20} />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

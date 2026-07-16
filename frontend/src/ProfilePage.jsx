import './ProfilePage.css'

export default function ProfilePage({ user }) {
  return (
    <div className="profile-page">
      <div className="profile-card">
        <div className="profile-avatar" aria-hidden="true">
          {user.name.trim().charAt(0).toUpperCase()}
        </div>
        <h1>{user.name}</h1>
        <p className="profile-username">@{user.username}</p>
        {user.is_admin && <span className="admin-badge">Admin</span>}

        <dl className="profile-fields">
          <div>
            <dt>Email</dt>
            <dd>{user.email || <span className="muted">Not set</span>}</dd>
          </div>
          <div>
            <dt>Rank points</dt>
            <dd>{user.rank_points}</dd>
          </div>
          <div>
            <dt>Referral code</dt>
            <dd>
              <code>{user.referral_code}</code>
            </dd>
          </div>
          <div>
            <dt>Daily reminder emails</dt>
            <dd>{user.reminders_opt_in ? 'On' : 'Off'}</dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{user.created_at}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
